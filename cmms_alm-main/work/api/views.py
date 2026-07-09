# work/api/views.py

from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from cmms_instanta.permissions import RoleBasedPermissionMixin
from work.models import WorkRequest, WorkOrder, Comment, PaymentItem, PaymentRequisition, PPM, WorkOrderCompletion, Invoice
from .serializers import (WorkRequestSerializer, WorkOrderSerializer, CommentSerializer,
                          PaymentItemSerializer, PaymentRequisitionSerializer,
                          PPMSerializer, WorkOrderCompletionSerializer, InvoiceSerializer)

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from accounts.models import Personnel, Vendor
from accounts.api.serializers import PersonnelSerializer, VendorSerializer

from facility.models import Facility, Building
from facility.api.serializers import BuildingSerializer
from asset_inventory.models import Asset
from asset_inventory.api.serializers import AssetSerializer

User = get_user_model()

REJECTED_STATUSES = {'Rejected – Vendor Changed', 'Reviewer Rejected', 'Approver Rejected'}


class WorkRequestViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    serializer_class = WorkRequestSerializer
    feature = 'work_request'
    lookup_field = 'slug'
    lookup_value_regex = r'(?:work|procument)[a-z0-9\-]*'

    def _base_queryset(self):
        return WorkRequest.objects.select_related(
            'requester', 'approver', 'category', 'subcategory',
            'facility', 'asset', 'department', 'vendor', 'po_vendor',
        ).prefetch_related('reviewers', 'request_to', 'resources')

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'roles', '').strip().upper()
        qs = self._base_queryset()
        if role in ['SUPER ADMIN', 'ADMIN', 'FINANCE']:
            return qs.order_by('-id')
        if role == 'PROCUREMENT AND STORE':
            return qs.filter(request_to=user).order_by('-id')
        if role == 'APPROVER':
            return qs.filter(approver=user).order_by('-id')
        if role == 'REVIEWER':
            return qs.filter(reviewers=user).order_by('-id')
        return qs.filter(owner=user).order_by('-id')

    def perform_create(self, serializer):
        allowed_roles = ['REQUESTER', 'ADMIN', 'SUPER ADMIN']
        if self.request.user.roles not in allowed_roles:
            raise PermissionDenied("Only REQUESTER, ADMIN, or SUPER ADMIN can create work requests.")

        # Enforce sequential route selection — all three must be provided
        data = self.request.data
        request_to = data.getlist('request_to') if hasattr(data, 'getlist') else data.get('request_to', [])
        reviewers = data.getlist('reviewers') if hasattr(data, 'getlist') else data.get('reviewers', [])
        approver = data.get('approver')

        if not request_to:
            raise drf_serializers.ValidationError({"request_to": "A Procurement & Store handler must be selected first."})
        if not reviewers:
            raise drf_serializers.ValidationError({"reviewers": "A Reviewer must be selected."})
        if not approver:
            raise drf_serializers.ValidationError({"approver": "An Approver must be selected."})

        serializer.save(
            owner=self.request.user,
            requester=self.request.user,
            approval_status='Pending Review',
            is_locked=True,
        )

    def perform_destroy(self, instance):
        if self.request.user.roles != 'SUPER ADMIN':
            raise PermissionDenied("Only SUPER ADMIN can delete work requests.")
        instance.delete()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_locked:
            return Response(
                {"error": "This request is locked. It must be rejected before it can be edited."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_locked:
            return Response(
                {"error": "This request is locked. It must be rejected before it can be edited."},
                status=status.HTTP_403_FORBIDDEN,
            )
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    # ── Step 2: Procurement & Store ───────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='cp-approve')
    def cp_approve(self, request, slug=None):
        """
        Procurement & Store approves the invoice, optionally selecting an alternative
        vendor, and generates a PO. Status → CP Approved.
        """
        if request.user.roles != 'PROCUREMENT AND STORE':
            return Response(
                {"error": "Only PROCUREMENT AND STORE users can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'Pending Review':
            return Response(
                {"error": f"Cannot act on a request with status '{instance.approval_status}'. Expected 'Pending Review'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        po_number = (request.data.get('po_number') or '').strip()
        if not po_number:
            return Response(
                {"error": "po_number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = ['approval_status', 'po_number', 'po_vendor']

        po_amount = request.data.get('po_amount')
        if po_amount is not None:
            try:
                from decimal import Decimal
                instance.po_amount = Decimal(str(po_amount))
                update_fields.append('po_amount')
            except Exception:
                return Response(
                    {"error": "po_amount must be a valid number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        po_vendor_id = request.data.get('po_vendor')
        if po_vendor_id:
            po_vendor = get_object_or_404(Vendor, pk=po_vendor_id)
            instance.po_vendor = po_vendor
        else:
            instance.po_vendor = instance.vendor

        po_document = request.FILES.get('po_document')
        if po_document:
            instance.po_document = po_document
            update_fields.append('po_document')

        instance.po_number = po_number
        instance.approval_status = 'CP Approved'
        instance.save(update_fields=update_fields)

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cp-reject')
    def cp_reject(self, request, slug=None):
        """
        Procurement & Store is not satisfied with the vendor. They select an alternative
        vendor, provide a mandatory reason, generate a PO against that vendor, and kick
        the request back to the Requester. Status → Rejected – Vendor Changed.
        """
        if request.user.roles != 'PROCUREMENT AND STORE':
            return Response(
                {"error": "Only PROCUREMENT AND STORE users can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'Pending Review':
            return Response(
                {"error": f"Cannot act on a request with status '{instance.approval_status}'. Expected 'Pending Review'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        po_vendor_id = request.data.get('po_vendor')
        cp_reason = (request.data.get('cp_reason') or '').strip()

        if not po_vendor_id:
            return Response(
                {"error": "po_vendor is required when rejecting due to a vendor issue."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not cp_reason:
            return Response(
                {"error": "cp_reason is required when rejecting due to a vendor issue."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        po_vendor = get_object_or_404(Vendor, pk=po_vendor_id)

        instance.po_vendor = po_vendor
        instance.po_number = instance.generate_po_number()
        instance.cp_reason = cp_reason
        instance.approval_status = 'Rejected – Vendor Changed'
        instance.is_locked = False
        instance.save(update_fields=['po_vendor', 'po_number', 'cp_reason', 'approval_status', 'is_locked'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Step 3: Reviewer ──────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='reviewer-approve')
    def reviewer_approve(self, request, slug=None):
        """
        Reviewer performs a three-way audit (original request, PO, invoice) and approves.
        Status → Reviewed.
        """
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'REVIEWER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only REVIEWER, ADMIN, or SUPER ADMIN can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'CP Approved':
            return Response(
                {"error": f"Cannot review a request with status '{instance.approval_status}'. Expected 'CP Approved'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.approval_status = 'Reviewed'
        instance.save(update_fields=['approval_status'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reviewer-reject')
    def reviewer_reject(self, request, slug=None):
        """
        Reviewer finds a mismatch and rejects with a mandatory reason.
        Status → Reviewer Rejected. Request unlocked for Requester correction.
        """
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'REVIEWER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only REVIEWER, ADMIN, or SUPER ADMIN can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'CP Approved':
            return Response(
                {"error": f"Cannot review a request with status '{instance.approval_status}'. Expected 'CP Approved'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reviewer_reason = (request.data.get('reviewer_reason') or '').strip()
        if not reviewer_reason:
            return Response(
                {"error": "reviewer_reason is required when rejecting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.reviewer_reason = reviewer_reason
        instance.approval_status = 'Reviewer Rejected'
        instance.is_locked = False
        instance.save(update_fields=['reviewer_reason', 'approval_status', 'is_locked'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Step 4: Final Approver ────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='final-approve')
    def final_approve(self, request, slug=None):
        """
        Approver reviews the full package and gives executive sign-off with a digital
        signature. The request is atomically committed to the ledger and permanently locked.
        Status → Fully Approved.
        """
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only APPROVER, ADMIN, or SUPER ADMIN can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'Reviewed':
            return Response(
                {"error": f"Cannot approve a request with status '{instance.approval_status}'. Expected 'Reviewed'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.fully_approved_at = timezone.now()
        instance.approval_status = 'Fully Approved'
        instance.is_locked = True
        instance.save(update_fields=['fully_approved_at', 'approval_status', 'is_locked'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='final-reject')
    def final_reject(self, request, slug=None):
        """
        Approver rejects with a mandatory reason. Request sent to remediation queue.
        Status → Approver Rejected. Request unlocked for Requester correction.
        """
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only APPROVER, ADMIN, or SUPER ADMIN can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'Reviewed':
            return Response(
                {"error": f"Cannot reject a request with status '{instance.approval_status}'. Expected 'Reviewed'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approver_reason = (request.data.get('approver_reason') or '').strip()
        if not approver_reason:
            return Response(
                {"error": "approver_reason is required when rejecting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.approver_reason = approver_reason
        instance.approval_status = 'Approver Rejected'
        instance.is_locked = False
        instance.save(update_fields=['approver_reason', 'approval_status', 'is_locked'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Resubmit (Requester) ──────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='resubmit')
    def resubmit(self, request, slug=None):
        """
        Requester corrects the request after any rejection and resubmits it.
        Resets the pipeline back to Step 2. Status → Pending Review.
        Call this after making corrections via the regular PATCH endpoint.
        """
        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.owner != request.user:
            return Response(
                {"error": "Only the original requester can resubmit this work request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if instance.approval_status not in REJECTED_STATUSES:
            return Response(
                {"error": f"Cannot resubmit a request with status '{instance.approval_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.approval_status = 'Pending Review'
        instance.is_locked = True
        instance.save(update_fields=['approval_status', 'is_locked'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Read-only helpers ─────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='approved-work-requests')
    def approved_work_requests(self, request):
        queryset = self._base_queryset().filter(
            approval_status='Fully Approved',
            derived_work_orders__isnull=True,
        ).order_by('-id')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='procurement-users')
    def procurement_users(self, request):
        users = User.objects.filter(roles='PROCUREMENT AND STORE')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reviewers')
    def reviewers_list(self, request):
        users = User.objects.filter(roles='REVIEWER')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='approvers')
    def approvers_list(self, request):
        users = User.objects.filter(roles='APPROVER')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='procurement-assigned')
    def procurement_assigned(self, request):
        if request.user.roles not in ('PROCUREMENT AND STORE', 'ADMIN', 'SUPER ADMIN'):
            return Response(
                {"error": "Only users with PROCUREMENT AND STORE role can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        work_requests = self._base_queryset().filter(request_to=request.user).order_by('-id')
        page = self.paginate_queryset(work_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(work_requests, many=True)
        return Response({"count": work_requests.count(), "results": serializer.data})

    @action(detail=False, methods=['get'], url_path='po-requisition')
    def po_requisition(self, request):
        if request.user.roles not in ('PROCUREMENT AND STORE', 'ADMIN', 'SUPER ADMIN'):
            return Response(
                {"error": "Only users with PROCUREMENT AND STORE role can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        procurement_users = User.objects.filter(roles='PROCUREMENT AND STORE')
        work_requests = self._base_queryset().filter(
            request_to__in=procurement_users
        ).distinct().order_by('-id')
        serializer = self.get_serializer(work_requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'patch'], url_path='update-requisition')
    def update_requisition(self, request, slug):
        if request.user.roles not in ('PROCUREMENT AND STORE', 'ADMIN', 'SUPER ADMIN'):
            return Response(
                {"error": "Only users with PROCUREMENT AND STORE role can update work requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        if request.user not in instance.request_to.all():
            return Response(
                {"error": "You can only update work requests assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='buildings-by-facility/(?P<facility_id>[^/.]+)')
    def buildings_by_facility(self, request, facility_id=None):
        try:
            facility = get_object_or_404(Facility, id=facility_id)
            buildings = Building.objects.filter(facility=facility).order_by('-id')
            serializer = BuildingSerializer(buildings, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Error retrieving buildings: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='assets-by-facility/(?P<facility_id>[^/.]+)')
    def assets_by_facility(self, request, facility_id=None):
        try:
            facility = get_object_or_404(Facility, id=facility_id)
            assets = Asset.objects.filter(facility=facility).order_by('-id')
            serializer = AssetSerializer(assets, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Error retrieving assets: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class WorkOrderViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all().order_by('-id')
    serializer_class = WorkOrderSerializer
    permission_classes = [IsAuthenticated]
    feature = "work_order"
    lookup_field = 'slug'

    def _base_queryset(self):
        return WorkOrder.objects.select_related(
            'requester', 'request_to', 'approver',
            'category', 'subcategory', 'facility', 'asset',
        ).prefetch_related('reviewers', 'resources')

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'roles', '').strip().upper()
        qs = self._base_queryset()
        if role in ['SUPER ADMIN', 'ADMIN', 'FINANCE']:
            return qs.order_by('-id')
        if role == 'REVIEWER':
            return qs.filter(reviewers=user).order_by('-id')
        if role == 'APPROVER':
            return qs.filter(approver=user).order_by('-id')
        return qs.filter(owner=user).order_by('-id')

    def create(self, request, *args, **kwargs):
        print("=== WorkOrder POST data ===", dict(request.data))
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("=== WorkOrder 400 validation errors ===", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, requester=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve-by-reviewer')
    def approve_by_reviewer(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        user = request.user
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'REVIEWER']
        is_assigned_reviewer = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in allowed_roles and not is_assigned_reviewer:
            return Response(
                {"error": "You are not authorised to review this work order."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.is_reviewed:
            return Response(
                {"error": "This work order has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_reviewed = True
        instance.approval_status = 'Reviewed'
        instance.save(update_fields=['is_reviewed', 'approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject-by-reviewer')
    def reject_by_reviewer(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        user = request.user
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'REVIEWER']
        is_assigned_reviewer = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in allowed_roles and not is_assigned_reviewer:
            return Response(
                {"error": "You are not authorised to reject this work order."},
                status=status.HTTP_403_FORBIDDEN,
            )
        reviewer_reason = (request.data.get('reviewer_reason') or '').strip()
        if not reviewer_reason:
            return Response(
                {"error": "reviewer_reason is required when rejecting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.reviewer_reason = reviewer_reason
        instance.approval_status = 'Reviewer Rejected'
        instance.is_reviewed = False
        instance.save(update_fields=['reviewer_reason', 'approval_status', 'is_reviewed'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='approve-by-approver')
    def approve_by_approver(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        user = request.user
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        is_assigned_approver = instance.approver_id == user.pk
        if user.roles not in allowed_roles and not is_assigned_approver:
            return Response(
                {"error": "You are not authorised to approve this work order."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not instance.is_reviewed:
            return Response(
                {"error": "Work order must be reviewed before it can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.is_approved:
            return Response(
                {"error": "This work order has already been approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_approved = True
        instance.approval_status = 'Approved'
        instance.save(update_fields=['is_approved', 'approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject-by-approver')
    def reject_by_approver(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        user = request.user
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        is_assigned_approver = instance.approver_id == user.pk
        if user.roles not in allowed_roles and not is_assigned_approver:
            return Response(
                {"error": "You are not authorised to reject this work order."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not instance.is_reviewed:
            return Response(
                {"error": "Work order must be reviewed before it can be rejected by approver."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        approver_reason = (request.data.get('approver_reason') or '').strip()
        if not approver_reason:
            return Response(
                {"error": "approver_reason is required when rejecting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.approver_reason = approver_reason
        instance.approval_status = 'Approver Rejected'
        instance.save(update_fields=['approver_reason', 'approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_order(self, request, slug=None):
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only ADMIN, SUPER ADMIN, or APPROVER can approve work orders."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(WorkOrder, slug=slug)
        instance.approval_status = 'Approved'
        instance.save(update_fields=['approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unlock-resubmission')
    def unlock_resubmission(self, request, slug=None):
        if request.user.roles not in ['ADMIN', 'SUPER ADMIN']:
            return Response(
                {"error": "Only ADMIN or SUPER ADMIN can unlock resubmission."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(WorkOrder, slug=slug)
        rejected_statuses = {'Reviewer Rejected', 'Approver Rejected'}
        if instance.approval_status not in rejected_statuses:
            return Response(
                {"error": "Resubmission can only be unlocked on a rejected work order."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.allow_resubmission:
            return Response(
                {"error": "Resubmission is already unlocked for this work order."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.allow_resubmission = True
        instance.save(update_fields=['allow_resubmission'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='approvers')
    def approvers(self, request):
        users = User.objects.filter(roles='APPROVER')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reviewers')
    def reviewers(self, request):
        users = User.objects.filter(roles='REVIEWER')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)


class PaymentRequisitionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = PaymentRequisition.objects.all().order_by('-id')
    serializer_class = PaymentRequisitionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        allowed_roles = ['REQUESTER', 'ADMIN', 'SUPER ADMIN']
        if self.request.user.roles not in allowed_roles:
            raise PermissionDenied("Only REQUESTER, ADMIN, or SUPER ADMIN can create payment requests.")
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, slug):
        instance = get_object_or_404(PaymentRequisition, slug=slug)
        user_role = request.user.roles
        amount = instance.amount if hasattr(instance, 'amount') else 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0

        if user_role == 'SUPER ADMIN':
            pass
        elif user_role == 'ADMIN' and amount > 1000000:
            pass
        elif user_role == 'APPROVER' and amount <= 1000000:
            pass
        else:
            return Response(
                {"error": "You do not have permission to approve this payment request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.approval_status = 'Approved'
        instance.save(update_fields=['approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='personnel-list')
    def personnel_list(self, request):
        personnel = Personnel.objects.all()
        serializer = PersonnelSerializer(personnel, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='vendor-list')
    def vendor_list(self, request):
        vendors = Vendor.objects.all()
        serializer = VendorSerializer(vendors, many=True)
        return Response(serializer.data)


class PaymentItemViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all().order_by('-id')
    serializer_class = PaymentItemSerializer
    feature = "requisition"


class CommentViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-id')
    serializer_class = CommentSerializer
    feature = "comment"


class PPMViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    serializer_class = PPMSerializer
    feature = "ppm_setting"

    def _base_queryset(self):
        return PPM.objects.select_related('owner', 'approver', 'facility')

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'roles', '').strip().upper()
        qs = self._base_queryset()
        if role in ['SUPER ADMIN', 'ADMIN']:
            return qs.order_by('-id')
        if role == 'APPROVER':
            return qs.filter(approver=user).order_by('-id')
        return qs.filter(owner=user).order_by('-id')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'], url_path='approved-ppms')
    def approved_ppms(self, request):
        queryset = PPM.objects.filter(approval_status='Approved').order_by('-id')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='approvers')
    def approvers(self, request):
        users = User.objects.filter(roles='APPROVER')
        data = [{"id": u.id, "name": u.name, "email": u.email} for u in users]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER', 'REVIEWER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only ADMIN, SUPER ADMIN, APPROVER, or REVIEWER can review PPMs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(PPM, pk=pk)
        if request.user.roles == 'APPROVER' and instance.approver_id != request.user.pk:
            return Response(
                {"error": "You can only review PPMs assigned to you as approver."},
                status=status.HTTP_403_FORBIDDEN,
            )
        review_action = request.data.get('review_action')
        if review_action not in ['approve', 'reject']:
            return Response(
                {"error": "review_action must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if review_action == 'approve':
            instance.approval_status = 'Approved'
            instance.rejection_reason = None
        else:
            instance.approval_status = 'Rejected'
            instance.rejection_reason = request.data.get('rejection_reason', '')
        instance.save(update_fields=['approval_status', 'rejection_reason'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER', 'REVIEWER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only ADMIN, SUPER ADMIN, APPROVER, or REVIEWER can reject PPMs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(PPM, pk=pk)
        if request.user.roles == 'APPROVER' and instance.approver_id != request.user.pk:
            return Response(
                {"error": "You can only reject PPMs assigned to you as approver."},
                status=status.HTTP_403_FORBIDDEN,
            )
        rejection_reason = request.data.get('rejection_reason', '')
        instance.approval_status = 'Rejected'
        instance.rejection_reason = rejection_reason
        instance.save(update_fields=['approval_status', 'rejection_reason'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


ACTIVE_WCC_STATUSES = {'Pending', 'Reviewed', 'Approved'}


class WorkOrderCompletionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = WorkOrderCompletion.objects.all().order_by('-id')
    serializer_class = WorkOrderCompletionSerializer
    permission_classes = [IsAuthenticated]
    feature = 'work_order'

    def _base_queryset(self):
        return WorkOrderCompletion.objects.select_related(
            'owner', 'approver', 'work_order',
        ).prefetch_related('reviewers', 'resources')

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'roles', '').strip().upper()
        qs = self._base_queryset()
        if role in ['SUPER ADMIN', 'ADMIN', 'FINANCE']:
            return qs.order_by('-id')
        if role == 'REVIEWER':
            return qs.filter(reviewers=user).order_by('-id')
        if role == 'APPROVER':
            return qs.filter(approver=user).order_by('-id')
        return qs.filter(owner=user).order_by('-id')

    def perform_create(self, serializer):
        work_order = serializer.validated_data.get('work_order')
        if work_order:
            conflict = WorkOrderCompletion.objects.filter(
                work_order=work_order,
                approval_status__in=ACTIVE_WCC_STATUSES,
            ).first()
            if conflict:
                from rest_framework.exceptions import ValidationError as DRFValidationError
                raise DRFValidationError(
                    f"A Work Completion Certificate already exists for this Work Order "
                    f"(WCC-{conflict.pk}, status: {conflict.approval_status}). "
                    "Resolve or reject the existing WCC before creating a new one."
                )
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'], url_path='available-work-orders')
    def available_work_orders(self, request):
        # Exclude Work Orders that already have an active (non-rejected) WCC
        blocked_wo_ids = WorkOrderCompletion.objects.filter(
            approval_status__in=ACTIVE_WCC_STATUSES
        ).values_list('work_order_id', flat=True)
        qs = WorkOrder.objects.filter(
            approval_status='Approved'
        ).exclude(id__in=blocked_wo_ids).order_by('-id')
        from .serializers import WorkOrderSerializer
        serializer = WorkOrderSerializer(qs, many=True, context={'request': request})
        return Response({
            'count': qs.count(),
            'results': serializer.data,
            'filters_applied': {'exclude_completed': True, 'work_order_types': []},
        })

    @action(detail=False, methods=['get'], url_path='raise-payment-work-orders')
    def raise_payment_work_orders(self, request):
        qs = WorkOrder.objects.filter(approval_status='Approved').order_by('-id')
        from .serializers import WorkOrderSerializer
        serializer = WorkOrderSerializer(qs, many=True, context={'request': request})
        return Response({
            'message': 'Approved work orders available for invoicing',
            'count': qs.count(),
            'results': serializer.data,
            'filters_applied': {
                'facility': None,
                'category': None,
                'priority': None,
                'status': None,
                'approval_status': 'Approved',
                'search': None,
                'user_filter': 'all',
                'work_order_type': 'all',
            },
        })

    @action(detail=False, methods=['get'], url_path='approved-for-invoicing')
    def approved_for_invoicing(self, request):
        qs = WorkOrderCompletion.objects.filter(approval_status='Approved').order_by('-id')
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'count': qs.count(),
            'next': None,
            'previous': None,
            'results': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='by-requester/(?P<requester_id>[^/.]+)')
    def by_requester(self, request, requester_id=None):
        qs = WorkOrderCompletion.objects.filter(owner_id=requester_id).order_by('-id')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'count': qs.count(),
            'next': None,
            'previous': None,
            'results': serializer.data,
        })

    @action(detail=True, methods=['post'], url_path='approve-by-reviewer')
    def approve_by_reviewer(self, request, pk=None):
        instance = get_object_or_404(WorkOrderCompletion, pk=pk)
        user = request.user
        is_assigned = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'REVIEWER'] and not is_assigned:
            return Response({'error': 'You are not authorised to review this completion.'}, status=status.HTTP_403_FORBIDDEN)
        if instance.is_reviewed:
            return Response({'error': 'Already reviewed.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.is_reviewed = True
        instance.approval_status = 'Reviewed'
        instance.save(update_fields=['is_reviewed', 'approval_status'])
        return Response({'message': 'Completion reviewed successfully.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='reject-by-reviewer')
    def reject_by_reviewer(self, request, pk=None):
        instance = get_object_or_404(WorkOrderCompletion, pk=pk)
        user = request.user
        is_assigned = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'REVIEWER'] and not is_assigned:
            return Response({'error': 'You are not authorised to reject this completion.'}, status=status.HTTP_403_FORBIDDEN)
        notes = (request.data.get('notes') or '').strip()
        if not notes:
            return Response({'error': 'notes is required when rejecting.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'Reviewer Rejected'
        instance.is_reviewed = False
        instance.reviewer_notes = notes
        instance.save(update_fields=['approval_status', 'is_reviewed', 'reviewer_notes'])
        return Response({'message': 'Completion rejected by reviewer.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='approve-by-approver')
    def approve_by_approver(self, request, pk=None):
        instance = get_object_or_404(WorkOrderCompletion, pk=pk)
        user = request.user
        is_assigned = instance.approver_id == user.pk
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'APPROVER'] and not is_assigned:
            return Response({'error': 'You are not authorised to approve this completion.'}, status=status.HTTP_403_FORBIDDEN)
        if not instance.is_reviewed:
            return Response({'error': 'Completion must be reviewed before it can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'Approved'
        instance.save(update_fields=['approval_status'])
        return Response({'message': 'Completion approved successfully.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='reject-by-approver')
    def reject_by_approver(self, request, pk=None):
        instance = get_object_or_404(WorkOrderCompletion, pk=pk)
        user = request.user
        is_assigned = instance.approver_id == user.pk
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'APPROVER'] and not is_assigned:
            return Response({'error': 'You are not authorised to reject this completion.'}, status=status.HTTP_403_FORBIDDEN)
        notes = (request.data.get('notes') or '').strip()
        if not notes:
            return Response({'error': 'notes is required when rejecting.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'Approver Rejected'
        instance.approver_notes = notes
        instance.save(update_fields=['approval_status', 'approver_notes'])
        return Response({'message': 'Completion rejected by approver.', 'data': self.get_serializer(instance).data})


class InvoiceViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    feature = 'work_order'

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'roles', '').strip().upper()
        if role in ['SUPER ADMIN', 'ADMIN', 'FINANCE']:
            return Invoice.objects.all().order_by('-id')
        if role == 'APPROVER':
            return Invoice.objects.filter(approver=user).order_by('-id')
        if role == 'REVIEWER':
            return Invoice.objects.filter(reviewers=user).order_by('-id')
        return Invoice.objects.filter(owner=user).order_by('-id')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, raised_by=self.request.user)

    def create(self, request, *args, **kwargs):
        import json
        raw = request.data.get('data')
        if raw:
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return Response({'error': 'Invalid JSON in data field.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            payload = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        # Gate: work_completion is mandatory
        wcc_id = payload.get('work_completion')
        if not wcc_id:
            return Response(
                {'error': 'An invoice must be linked to a Work Completion Certificate.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        wcc = get_object_or_404(WorkOrderCompletion, pk=wcc_id)
        if wcc.approval_status != 'Approved':
            return Response(
                {'error': f"Invoice can only be raised against an Approved WCC. Current status: '{wcc.approval_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Auto-populate work_order from the WCC so the link is always consistent
        if wcc.work_order_id:
            payload['work_order'] = wcc.work_order_id

        files = request.FILES.getlist('attachments')
        reviewers_ids = payload.pop('reviewers', [])
        items_data = payload.pop('items', [])

        serializer = self.get_serializer(data=payload)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.validated_data['attachments_files'] = files
        serializer.validated_data['reviewers'] = list(User.objects.filter(pk__in=reviewers_ids))
        serializer.validated_data['items_data'] = items_data

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        import json
        raw = request.data.get('data')
        if raw:
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return Response({'error': 'Invalid JSON in data field.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            payload = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        files = request.FILES.getlist('attachments')
        reviewers_ids = payload.pop('reviewers', None)
        items_data = payload.pop('items', None)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=payload, partial=kwargs.get('partial', False))
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.validated_data['attachments_files'] = files
        if reviewers_ids is not None:
            serializer.validated_data['reviewers'] = list(User.objects.filter(pk__in=reviewers_ids))
        if items_data is not None:
            serializer.validated_data['items_data'] = items_data

        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve-by-reviewer')
    def approve_by_reviewer(self, request, pk=None):
        instance = get_object_or_404(Invoice, pk=pk)
        user = request.user
        is_assigned = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'REVIEWER'] and not is_assigned:
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        if instance.is_reviewed:
            return Response({'error': 'Already reviewed.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.is_reviewed = True
        instance.approval_status = 'Reviewed'
        instance.save(update_fields=['is_reviewed', 'approval_status'])
        return Response({'message': 'Invoice reviewed.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='reject-by-reviewer')
    def reject_by_reviewer(self, request, pk=None):
        instance = get_object_or_404(Invoice, pk=pk)
        user = request.user
        is_assigned = instance.reviewers.filter(pk=user.pk).exists()
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'REVIEWER'] and not is_assigned:
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        notes = (request.data.get('notes') or '').strip()
        if not notes:
            return Response({'error': 'notes is required.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'Reviewer Rejected'
        instance.is_reviewed = False
        instance.reviewer_notes = notes
        instance.save(update_fields=['approval_status', 'is_reviewed', 'reviewer_notes'])
        return Response({'message': 'Invoice rejected by reviewer.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='approve-by-approver')
    def approve_by_approver(self, request, pk=None):
        instance = get_object_or_404(Invoice, pk=pk)
        user = request.user
        is_assigned = instance.approver_id == user.pk
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'APPROVER'] and not is_assigned:
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        if not instance.is_reviewed:
            return Response({'error': 'Must be reviewed first.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.is_approved = True
        instance.approval_status = 'Approved'
        instance.save(update_fields=['is_approved', 'approval_status'])
        return Response({'message': 'Invoice approved.', 'data': self.get_serializer(instance).data})

    @action(detail=True, methods=['post'], url_path='reject-by-approver')
    def reject_by_approver(self, request, pk=None):
        instance = get_object_or_404(Invoice, pk=pk)
        user = request.user
        is_assigned = instance.approver_id == user.pk
        if user.roles not in ['ADMIN', 'SUPER ADMIN', 'APPROVER'] and not is_assigned:
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        notes = (request.data.get('notes') or '').strip()
        if not notes:
            return Response({'error': 'notes is required.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'Approver Rejected'
        instance.approver_notes = notes
        instance.save(update_fields=['approval_status', 'approver_notes'])
        return Response({'message': 'Invoice rejected by approver.', 'data': self.get_serializer(instance).data})
