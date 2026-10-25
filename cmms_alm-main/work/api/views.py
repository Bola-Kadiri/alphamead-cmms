# work/api/views.py

import json
import logging

from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.db.models import Q
from cmms_instanta.permissions import (
    FINANCE_ROLES, SEE_ALL_INVOICE_ROLES, SEE_ALL_ROLES, RoleBasedPermissionMixin, accessible_facilities,
)
from work.models import (WorkRequest, WorkRequestQuotationItem, WorkOrder, Comment, PaymentItem,
                          PaymentRequisition, PPM, WorkOrderCompletion, Invoice)
from work.models.raise_payment_settings import RaisePaymentApprovalSettings
from work.models import work_request_flow as stage1
from work.models import work_order_flow as stage2
from work.models.action_log import history
from work.models.approval_matrix import ApprovalMatrix
from work.models.delegation import Delegation
from work.models.flow_rules import ActionRefused
from .serializers import (WorkRequestSerializer, WorkOrderSerializer, CommentSerializer,
                          PaymentItemSerializer, PaymentRequisitionSerializer,
                          PPMSerializer, WorkOrderCompletionSerializer, InvoiceSerializer)

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from accounts.models import Personnel, Vendor
from accounts.api.serializers import PersonnelSerializer, VendorSerializer

from facility.models import Facility, Building, Zone, Subsystem
from facility.api.serializers import BuildingSerializer, ZoneSerializer, SubsystemSerializer
from asset_inventory.models import Asset
from asset_inventory.api.serializers import AssetSerializer

User = get_user_model()

logger = logging.getLogger(__name__)

REJECTED_STATUSES = {'Rejected – Vendor Changed', 'Reviewer Rejected', 'Approver Rejected'}

# Work Order approval statuses that mean "this WR still has no live Work Order"
_WO_DEAD_STATUSES = ['Reviewer Rejected', 'Approver Rejected', 'Rejected', 'Final Approver Rejected']


def _exceeds_approval_limit(user, amount):
    """
    Approval-matrix check shared by WorkRequest.final_approve and
    PaymentRequisition.approve. Returns an error message if `amount` exceeds
    `user.approval_limit`, else None. A user with no limit set (None) is
    treated as unlimited, matching the field's existing optional semantics.
    """
    limit = getattr(user, 'approval_limit', None)
    if limit is None or not amount:
        return None
    if amount > limit:
        return (
            f"This request's amount ({amount}) exceeds your approval limit "
            f"({limit}). Route it to an approver with sufficient authority."
        )
    return None


def _auto_create_payment_requisition(work_order, acting_user, expected_payment_date=None):
    """
    Draft Payment Requisition auto-created once its Work Order has an
    Approved WCC — called both when the WCC itself is approved (so it's
    ready to be filled in immediately, no manual "create" step) and again
    at Work Order close time (idempotent, so that's a no-op by then).

    - Idempotent: returns the existing requisition if one is already linked
      to this work order.
    - Pre-filled from the work order's own vendor and cost; `expected_payment_date`
      comes from the closing request payload when supplied; everything
      else (items, approvers, withholding tax, remark) is left for the
      requester or finance to fill in via the normal
      PaymentRequisitionViewSet endpoints.
    - Never raises: any failure is logged and swallowed so it can't block
      whatever action triggered it.
    """
    try:
        existing = work_order.linked_payments.order_by('id').first()
        if existing:
            return existing

        requisition = PaymentRequisition.objects.create(
            requisition_date=timezone.now().date(),
            owner=acting_user,
            payee_type='vendor' if work_order.vendor_id else None,
            pay_to=work_order.vendor,
            expected_payment_amount=work_order.cost or work_order.item_cost or 0,
            expected_payment_date=expected_payment_date,
        )
        requisition.work_orders.add(work_order)
        return requisition
    except Exception as exc:
        logger.warning(
            "Auto Payment Requisition creation failed for WorkOrder %s: %s",
            getattr(work_order, 'pk', None), exc,
        )
        return None


def _create_raise_payment_requisition(work_order, acting_user):
    """
    Raise Payment (known-cost bill — EKEDC, waste…): the work order's final approval
    *is* the payment approval, so the requisition is created already approved
    from the payment details captured on the work order, with the bill copied
    across as its attachment, and Finance is notified to disburse.

    Idempotent. Unlike _auto_create_payment_requisition this raises on failure,
    so the caller's transaction rolls the approval back rather than leaving an
    approved bill with no payment.
    """
    existing = work_order.linked_payments.order_by('id').first()
    if existing:
        return existing

    requisition = PaymentRequisition.objects.create(
        requisition_date=timezone.now().date(),
        owner=work_order.owner or work_order.requester,
        payee_type='vendor',
        pay_to=work_order.payee,
        expected_payment_amount=work_order.cost,
        expected_payment_date=work_order.expected_payment_date,
        withholding_tax=work_order.withholding_tax,
        approval_status='approve',
        remark=f"Raise Payment — Work Order {work_order.work_order_number}: {work_order.description or ''}".strip(),
    )
    requisition.work_orders.add(work_order)

    # The bill uploaded on the work order becomes the requisition's attachment
    # (same stored file, no copy).
    from django.contrib.contenttypes.models import ContentType
    from utils.models import FileAttachment
    pr_type = ContentType.objects.get_for_model(PaymentRequisition)
    for bill in work_order.resources.all():
        FileAttachment.objects.create(content_type=pr_type, object_id=requisition.pk, file=bill.file.name)

    if not work_order.vendor_id:
        work_order.vendor = work_order.payee
        work_order.save(update_fields=['vendor'])

    def _notify_finance():
        try:
            from work.utils.email_service import send_notification_email, create_in_app_notifications
            finance = list(User.objects.filter(roles__in=FINANCE_ROLES, is_active=True))
            send_notification_email(
                subject=f'[AlphaCMMS] Payment Requisition {requisition.requisition_number} — Ready for Disbursement',
                template='emails/payment_requisition_approved.html',
                context={'instance': requisition},
                recipient_list=[u.email for u in finance if u.email],
            )
            create_in_app_notifications(
                recipients=finance,
                title=f'Ready for Disbursement: {requisition.requisition_number}',
                message=f'Raise Payment approved on Work Order {work_order.work_order_number}.',
                notification_type='PAYMENT_REQUISITION',
                object_id=requisition.pk,
            )
        except Exception as exc:  # noqa: BLE001 — notification must not undo the payment
            logger.error('Raise Payment Finance notification failed (PR %s): %s', requisition.pk, exc)

    transaction.on_commit(_notify_finance)
    return requisition


def _client_work_orders(qs, user):
    """
    Work orders a CLIENT may see: those at their client's facilities. Raise
    Payment bills (EKEDC, waste…) only where that client has show_utility_bills.
    """
    qs = qs.filter(facility__in=accessible_facilities(user))
    return qs.exclude(
        Q(type=WorkOrder.RAISE_PAYMENT) & ~Q(facility__client__show_utility_bills=True)
    )


def _signer_facilities(user, slot):
    """Facilities where `user` is the named signer for `slot`, or currently covers for that signer."""
    covered = Delegation.objects.active().filter(stand_in=user).values_list('person_id', flat=True)
    return ApprovalMatrix.objects.filter(
        Q(**{slot: user}) | Q(**{f'{slot}__in': covered})
    ).values_list('facility_id', flat=True)


def _flow_data(wr, user):
    """Everything the Work Request screen needs about the five-stage flow."""
    client_step = stage1.client_approves(wr)
    steps = ['requester', 'approver'] + (['client_rep'] if client_step else [])
    chain = []
    for step in steps:
        people = stage1.people_for(wr, step)
        entry = {'step': step, 'label': stage1.STEP_LABELS[step], 'kind': 'team' if step == 'requester' else 'named'}
        if step == 'requester':
            entry['people'] = len(people)
        else:
            entry['person'] = (people[0].name.strip() or people[0].email) if people else None
        chain.append(entry)
    timing = stage1.timing(wr)
    return {
        'flow': wr.flow,
        'status': wr.approval_status,
        'client_approves': client_step,
        'waiting_on': stage1.WAITING_ON.get(wr.approval_status),
        'chain': chain,
        'history': [
            {'action': a.action, 'label': a.get_action_display(), 'actor': a.actor_name, 'role': a.actor_role,
             'on_behalf_of': a.on_behalf_of_name or None, 'reason': a.reason or None, 'signature': a.signature or None,
             'at': a.at, 'since_previous_seconds': a.since_previous.total_seconds() if a.since_previous else None}
            for a in (history(wr) if wr.pk else [])
        ],
        'timing': timing,
        'my_actions': stage1.available_actions(wr, user) if wr.pk else [],
        'replaces': {'slug': wr.replaces.slug, 'number': wr.replaces.work_request_number} if wr.replaces_id else None,
    }


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
        if role == 'CLIENT':
            return qs.filter(facility__in=accessible_facilities(user)).order_by('-id')
        if role in SEE_ALL_ROLES:
            return qs.order_by('-id')
        if role == 'PROCUREMENT AND STORE':
            # No one is routed at creation any more — show requests
            # specifically assigned to this user, plus any still-unrouted
            # Pending Review request, so any Procurement & Store user can
            # pick it up.
            return qs.filter(
                Q(request_to=user) | Q(request_to__isnull=True, approval_status='Pending Review')
            ).distinct().order_by('-id')
        five_stage = Q(flow=WorkRequest.FIVE_STAGE)
        if role == 'APPROVER':
            return qs.filter(
                Q(approver=user) | five_stage & Q(facility__in=_signer_facilities(user, 'approver'))
            ).distinct().order_by('-id')
        if role == 'REVIEWER':
            return qs.filter(reviewers=user).order_by('-id')
        if role == 'REQUESTER':
            # Five-stage requests belong to the facility's Site Manager team.
            return qs.filter(
                Q(owner=user) | five_stage & Q(facility__in=accessible_facilities(user))
            ).distinct().order_by('-id')
        return qs.filter(owner=user).order_by('-id')

    @transaction.atomic
    def perform_create(self, serializer):
        allowed_roles = ['REQUESTER', 'ADMIN', 'SUPER ADMIN']
        if self.request.user.roles not in allowed_roles:
            raise PermissionDenied("Only REQUESTER, ADMIN, or SUPER ADMIN can create work requests.")

        facility = serializer.validated_data.get('facility')
        if stage1.facility_is_live(facility):
            # Five-stage flow: nobody is picked; the Approval Matrix routes it.
            replaces = serializer.validated_data.get('replaces')
            if replaces and not (replaces.flow == WorkRequest.FIVE_STAGE and replaces.approval_status == 'Client Rejected'):
                raise ValidationError({'replaces': 'Only a request the client rejected can be raised again.'})
            work_request = serializer.save(
                owner=self.request.user, requester=self.request.user, approval_status='Pending Review',
                is_locked=True, flow=WorkRequest.FIVE_STAGE, approver=None,
            )
            work_request.request_to.clear()
            work_request.reviewers.clear()
            try:
                stage1.raise_request(work_request, self.request.user)
            except ActionRefused as exc:
                raise PermissionDenied(str(exc))
            return
        serializer.validated_data.pop('replaces', None)

        # No routing is picked at creation any more — Procurement & Store is
        # notified broadly (see work/signals.py) and picks it up from their
        # queue; the Requester adds Reviewer + Approver afterward, once
        # Procurement & Store has priced it (via Edit, while CP Approved —
        # see cp_approve unlocking is_locked below).
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

    # ── Five-stage flow (Stage 1) ────────────────────────────────────────────

    def _flow_call(self, request, func, *args):
        work_request = self.get_object()
        try:
            func(work_request, request.user, *args)
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        work_request.refresh_from_db()
        return Response(_flow_data(work_request, request.user))

    @action(detail=False, methods=['get'], url_path='flow-preview')
    def flow_preview(self, request):
        """For the form: does this facility use the five-stage flow, and who will handle the request."""
        facility = Facility.objects.filter(pk=request.query_params.get('facility')).select_related('client').first()
        if facility is None or not stage1.facility_is_live(facility):
            return Response({'live': False})
        preview = WorkRequest(facility=facility, flow=WorkRequest.FIVE_STAGE)
        data = _flow_data(preview, request.user)
        return Response({'live': True, 'client_approves': data['client_approves'], 'chain': data['chain']})

    @action(detail=True, methods=['get'])
    def flow(self, request, slug=None):
        """Chain, history, timing and the actions this person may take."""
        return Response(_flow_data(self.get_object(), request.user))

    @action(detail=True, methods=['post'], url_path='flow-review')
    def flow_review(self, request, slug=None):
        return self._flow_call(request, stage1.review, request.data.get('signature', ''), request.data.get('note', ''))

    @action(detail=True, methods=['post'], url_path='flow-send-back')
    def flow_send_back(self, request, slug=None):
        return self._flow_call(request, stage1.send_back, request.data.get('reason', ''))

    @action(detail=True, methods=['post'], url_path='flow-resubmit')
    def flow_resubmit(self, request, slug=None):
        return self._flow_call(request, stage1.resubmit)

    @action(detail=True, methods=['post'], url_path='flow-approve')
    def flow_approve(self, request, slug=None):
        return self._flow_call(request, stage1.client_approve, request.data.get('signature', ''))

    @action(detail=True, methods=['post'], url_path='flow-reject')
    def flow_reject(self, request, slug=None):
        return self._flow_call(request, stage1.client_reject, request.data.get('reason', ''))

    @transaction.atomic
    def _save_and_resubmit_if_rejected(self, request, partial=False):
        instance = self.get_object()
        if instance.is_locked:
            return Response(
                {"error": "This request is locked. It must be rejected before it can be edited."},
                status=status.HTTP_403_FORBIDDEN,
            )
        was_rejected = instance.approval_status in REJECTED_STATUSES
        # CP Approved is unlocked specifically so the Requester can come
        # back, once Procurement & Store has priced it, and add Reviewer +
        # Approver — nobody was picked at creation. That's a one-time edit;
        # re-lock once it's saved so the request doesn't stay generally
        # editable through the rest of the approval chain.
        was_awaiting_routing = instance.approval_status == 'CP Approved'
        kwargs = {'partial': partial}
        serializer = self.get_serializer(instance, data=request.data, **kwargs)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if was_rejected:
            instance.refresh_from_db()
            instance.approval_status = 'Pending Review'
            instance.is_locked = True
            instance.save(update_fields=['approval_status', 'is_locked'])
            serializer = self.get_serializer(instance)
        elif was_awaiting_routing:
            instance.refresh_from_db()
            instance.is_locked = True
            instance.save(update_fields=['is_locked'])
            serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        return self._save_and_resubmit_if_rejected(request, partial=False)

    def partial_update(self, request, *args, **kwargs):
        return self._save_and_resubmit_if_rejected(request, partial=True)

    # ── Step 2: Procurement & Store ───────────────────────────────────────────

    def _parse_quotation_items(self, request):
        """
        Accepts an optional `items` payload on cp-approve — a JSON string
        (multipart form upload, since po_document is a file) or a native
        list (plain JSON request). Returns a validated list of dicts, or
        raises a ValidationError-shaped dict via the caller's Response.
        """
        raw = request.data.get('items')
        if not raw:
            return [], None
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (TypeError, ValueError):
                return None, "items must be valid JSON."
        if not isinstance(raw, list):
            return None, "items must be a list."

        from decimal import Decimal, InvalidOperation
        parsed = []
        for idx, row in enumerate(raw):
            try:
                description = (row.get('description') or '').strip()
                if not description:
                    return None, f"items[{idx}].description is required."
                estimate = row.get('unit_cost_estimate')
                parsed.append({
                    'description': description,
                    'quantity': Decimal(str(row.get('quantity', 1))),
                    'unit_cost_estimate': Decimal(str(estimate)) if estimate not in (None, '') else None,
                    'unit_cost_vendor': Decimal(str(row['unit_cost_vendor'])),
                    'unit_cost_client': Decimal(str(row['unit_cost_client'])),
                    'add_vat': bool(row.get('add_vat', False)),
                })
            except (KeyError, InvalidOperation, TypeError, AttributeError):
                return None, f"items[{idx}] must include description, unit_cost_vendor and unit_cost_client."
        return parsed, None

    def _apply_quotation_data(self, instance, request):
        """
        Shared by save_quotation (draft entry, no stage change) and
        cp_approve (still accepts the same payload directly, for backward
        compatibility with a one-shot submit). Saves whatever fields are
        present in the request onto instance; leaves anything not provided
        untouched — so calling this twice (once from save_quotation, once
        from a payload-less cp_approve) never clobbers earlier data.
        Returns an error string, or None on success.
        """
        quotation_items, items_error = self._parse_quotation_items(request)
        if items_error:
            return items_error

        update_fields = []

        po_number = request.data.get('po_number')
        if po_number is not None and str(po_number).strip():
            instance.po_number = str(po_number).strip()
            update_fields.append('po_number')

        po_amount = request.data.get('po_amount')
        if po_amount is not None:
            try:
                from decimal import Decimal
                instance.po_amount = Decimal(str(po_amount))
                update_fields.append('po_amount')
            except Exception:
                return "po_amount must be a valid number."

        po_vendor_id = request.data.get('po_vendor')
        if po_vendor_id:
            instance.po_vendor = get_object_or_404(Vendor, pk=po_vendor_id)
            update_fields.append('po_vendor')
        elif not instance.po_vendor_id:
            # First time anything's been saved — default to the original
            # vendor. Never clobber a po_vendor a prior call already set.
            instance.po_vendor = instance.vendor
            update_fields.append('po_vendor')

        po_document = request.FILES.get('po_document')
        if po_document:
            instance.po_document = po_document
            update_fields.append('po_document')

        if update_fields:
            instance.save(update_fields=update_fields)

        if quotation_items:
            # Replace any prior lines so a resubmitted quotation doesn't
            # silently accumulate stale rows alongside the new ones.
            instance.quotation_items.all().delete()
            WorkRequestQuotationItem.objects.bulk_create([
                WorkRequestQuotationItem(work_request=instance, **item)
                for item in quotation_items
            ])

        return None

    @action(detail=True, methods=['post'], url_path='save-quotation')
    def save_quotation(self, request, slug=None):
        """
        Procurement & Store fills in Quotation/PO/Vendor from the Quotation
        accordion, as its own step — re-callable any number of times while
        still Pending Review, entirely separate from actually approving.
        """
        if request.user.roles not in ('PROCUREMENT AND STORE', 'ADMIN', 'SUPER ADMIN'):
            return Response(
                {"error": "Only PROCUREMENT AND STORE users can save a quotation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkRequest, slug=slug)

        if instance.approval_status != 'Pending Review':
            return Response(
                {"error": f"Cannot edit the quotation on a request with status '{instance.approval_status}'. Expected 'Pending Review'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Nobody is routed at creation any more — whoever from Procurement &
        # Store picks it up first "claims" it here, so it drops out of
        # everyone else's unrouted queue.
        if request.user.roles == 'PROCUREMENT AND STORE' and not instance.request_to.filter(pk=request.user.pk).exists():
            instance.request_to.add(request.user)

        error = self._apply_quotation_data(instance, request)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cp-approve')
    def cp_approve(self, request, slug=None):
        """
        Procurement & Store approves the request, committing it to the next
        stage. Still accepts the full Quotation/PO/Vendor payload directly
        (backward compatible, one-shot submit) — but in the normal flow
        that data was already saved via save_quotation from the Quotation
        accordion, so this only needs a PO number to already be on record.
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

        if not instance.request_to.filter(pk=request.user.pk).exists():
            instance.request_to.add(request.user)

        error = self._apply_quotation_data(instance, request)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        instance.refresh_from_db(fields=['po_number', 'currency'])

        # Procurement & Store must have actually priced this — a cost
        # (quotation line) or a PO — before they can approve it at all.
        # Approving with neither would just wave the request through with no
        # commitment on record.
        if not instance.quotation_items.exists() and not instance.po_number:
            return Response(
                {"error": "Add a cost (quotation line) or a PO number before approving."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # PO is only mandatory once the quotation (Cost to Client) actually
        # needs one — quotation always comes first, PO requirement is
        # derived from it. Only defined for NGN; other currencies keep the
        # conservative always-required behaviour since no threshold was set
        # for them.
        from decimal import Decimal
        po_threshold = Decimal('100000')
        po_required = instance.currency != 'NGN' or (instance.total_cost_client or Decimal('0')) > po_threshold
        if po_required and not instance.po_number:
            return Response(
                {"error": "A PO number is required before approving — the Cost to Client exceeds ₦100,000. Save the quotation with a PO first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.approval_status = 'CP Approved'
        # Unlocked so the Requester can now find this request and Edit it to
        # add Reviewer + Approver — nothing was picked for those at
        # creation. Re-locked once the Requester actually saves that edit
        # (see _save_and_resubmit_if_rejected).
        instance.is_locked = False
        instance.save(update_fields=['approval_status', 'is_locked'])

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

    # ── Requester: assign resources + approver (after cost is imputed) ─────────
    #
    # A Work Request is locked from the moment it's created (see perform_create)
    # — the generic update()/partial_update() endpoints refuse to touch it
    # unless it was rejected. This dedicated action is the one deliberate hole
    # in that lock: once Procurement & Store has priced the request, the
    # Requester comes back to pick the vendor/technician "resources" and,
    # crucially, the approving officer who'll actually sign off — now that the
    # real cost (and therefore the right approval threshold) is known.

    @action(detail=True, methods=['post'], url_path='assign-resources')
    def assign_resources(self, request, slug=None):
        """
        Sets vendor/technician/approver on a Work Request — three different
        fields with three different owners:
          - vendor: Procurement & Store (or Admin) only. This is the payee the
            eventual Payment Requisition is raised to, so it stays a
            procurement decision, not the Requester's.
          - technician / approver: the Requester who raised the request (or
            Admin).
        Blocked until Procurement & Store has imputed a cost and a PO (added
        at least one quotation line + a PO number via cp-approve), and
        blocked once the request has reached a terminal state (Fully Approved
        or any Rejected status).
        """
        instance = get_object_or_404(WorkRequest, slug=slug)

        is_admin = request.user.roles in ('ADMIN', 'SUPER ADMIN')
        is_owner = instance.owner_id == request.user.id or instance.requester_id == request.user.id
        is_procurement = request.user.roles == 'PROCUREMENT AND STORE'

        if not (is_admin or is_owner or is_procurement):
            return Response(
                {"error": "You are not authorised to modify this request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not instance.quotation_items.exists() or not instance.po_number:
            return Response(
                {"error": "Procurement & Store has not imputed a cost and PO yet. You cannot add resources or an approving officer until both are attached."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        terminal_statuses = REJECTED_STATUSES | {'Fully Approved'}
        if instance.approval_status in terminal_statuses:
            return Response(
                {"error": f"Cannot assign resources on a request with status '{instance.approval_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = []

        if 'vendor' in request.data:
            if not (is_admin or is_procurement):
                return Response(
                    {"error": "Only Procurement & Store (or an Admin) can set the vendor."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            vendor_id = request.data.get('vendor') or None
            instance.vendor = get_object_or_404(Vendor, pk=vendor_id) if vendor_id else None
            update_fields.append('vendor')

        if 'technician' in request.data:
            if not (is_admin or is_owner):
                return Response(
                    {"error": "Only the Requester who raised this request (or an Admin) can set the technician."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            technician_id = request.data.get('technician') or None
            instance.technician = get_object_or_404(User, pk=technician_id) if technician_id else None
            update_fields.append('technician')

        if 'approver' in request.data:
            if not (is_admin or is_owner):
                return Response(
                    {"error": "Only the Requester who raised this request (or an Admin) can set the approving officer."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            approver_id = request.data.get('approver') or None
            if not approver_id:
                return Response({"error": "approver cannot be cleared — select an approving officer."}, status=status.HTTP_400_BAD_REQUEST)
            instance.approver = get_object_or_404(User, pk=approver_id)
            update_fields.append('approver')

        if not update_fields:
            return Response({"error": "Provide at least one of vendor, technician, approver."}, status=status.HTTP_400_BAD_REQUEST)

        instance.save(update_fields=update_fields)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='eligible-approvers')
    def eligible_approvers(self, request, slug=None):
        """
        Approvers whose personal approval_limit can cover this request's
        current cost — the "approval matrix" the Requester picks from once
        cost is known. A null limit means unlimited, so those users always
        qualify. Ordered by limit ascending so the most tightly-scoped (most
        appropriate) approver for the amount is offered first.
        """
        instance = get_object_or_404(WorkRequest, slug=slug)
        cost = instance.total_cost_client or 0

        users = User.objects.filter(roles='APPROVER', status='Active').filter(
            Q(approval_limit__isnull=True) | Q(approval_limit__gte=cost)
        ).order_by('approval_limit')

        data = [
            {"id": u.id, "name": u.name, "email": u.email, "approval_limit": u.approval_limit}
            for u in users
        ]
        return Response(data)

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

        # Reviewer/Approver aren't chosen at creation any more — the
        # Requester adds them once Procurement & Store has priced it. Until
        # that happens, nobody with the REVIEWER role should be able to act
        # on this specific request.
        if not instance.reviewers.exists():
            return Response(
                {"error": "No Reviewer has been assigned to this request yet — ask the Requester to add one first."},
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

        if not instance.reviewers.exists():
            return Response(
                {"error": "No Reviewer has been assigned to this request yet — ask the Requester to add one first."},
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

    def _auto_create_work_order(self, work_request, acting_user):
        """
        Spin up the Work Order that belongs to a just-approved Work Request so the
        Requester gets a clickable work-order reference on the request page.

        - Idempotent: returns the existing Work Order if this request already has
          one that isn't in a dead/rejected state.
        - Never raises: any failure is logged and swallowed so it can't block the
          approval that triggered it.
        """
        try:
            existing = work_request.derived_work_orders.exclude(
                approval_status__in=_WO_DEAD_STATUSES
            ).order_by('id')
            if existing.exists():
                return existing.first()

            return WorkOrder.objects.create(
                source_work_request=work_request,
                type='FROM-WORK-REQUEST',
                requester=work_request.requester or work_request.owner or acting_user,
                owner=work_request.owner,
                facility=work_request.facility,
                building=work_request.building,
                category=work_request.category,
                subcategory=work_request.subcategory,
                department=work_request.department,
                asset=work_request.asset,
                description=work_request.description,
                priority=work_request.priority or 'Medium',
                currency=work_request.currency or 'USD',
                # Carried forward from whatever the Requester picked as
                # "resources" on the Work Request (see assign_resources) —
                # both stay optional here and can still be set/changed at
                # Work Order close time if the Requester never assigned them.
                vendor=work_request.vendor,
                technician=work_request.technician,
            )
        except Exception as exc:  # noqa: BLE001 — must not break the approval
            logger.warning(
                "Auto Work Order creation failed for WorkRequest %s: %s",
                getattr(work_request, 'pk', None), exc,
            )
            return None

    @action(detail=True, methods=['post'], url_path='final-approve')
    def final_approve(self, request, slug=None):
        """
        Approver reviews the full package and gives executive sign-off with a digital
        signature. The request is atomically committed to the ledger and permanently locked.
        Status → Fully Approved. A linked Work Order is auto-created on approval.
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

        if not instance.approver_id:
            return Response(
                {"error": "No Approver has been assigned to this request yet — ask the Requester to add one first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.roles == 'APPROVER':
            amount = instance.total_cost_client or instance.po_amount or instance.cost
            limit_error = _exceeds_approval_limit(request.user, amount)
            if limit_error:
                return Response({"error": limit_error}, status=status.HTTP_403_FORBIDDEN)

        instance.fully_approved_at = timezone.now()
        instance.approval_status = 'Fully Approved'
        instance.is_locked = True
        instance.save(update_fields=['fully_approved_at', 'approval_status', 'is_locked'])

        self._auto_create_work_order(instance, request.user)

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

        if not instance.approver_id:
            return Response(
                {"error": "No Approver has been assigned to this request yet — ask the Requester to add one first."},
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
        work_requests = self._base_queryset().filter(
            Q(request_to=request.user) | Q(request_to__isnull=True, approval_status='Pending Review')
        ).distinct().order_by('-id')
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

    @action(detail=False, methods=['get'], url_path='zones-by-facility/(?P<facility_id>[^/.]+)')
    def zones_by_facility(self, request, facility_id=None):
        try:
            facility = get_object_or_404(Facility, id=facility_id)
            zones = Zone.objects.filter(facility=facility).order_by('-id')
            serializer = ZoneSerializer(zones, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Error retrieving zones: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='subsystems-by-zone/(?P<zone_id>[^/.]+)')
    def subsystems_by_zone(self, request, zone_id=None):
        try:
            zone = get_object_or_404(Zone, id=zone_id)
            subsystems = Subsystem.objects.filter(zone=zone).order_by('-id')
            serializer = SubsystemSerializer(subsystems, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Error retrieving subzones: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='assets-by-subsystem/(?P<subsystem_id>[^/.]+)')
    def assets_by_subsystem(self, request, subsystem_id=None):
        try:
            subsystem = get_object_or_404(Subsystem, id=subsystem_id)
            assets = Asset.objects.filter(subsystem=subsystem).order_by('-id')
            serializer = AssetSerializer(assets, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Error retrieving assets: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


def _money(value):
    return str(value) if value is not None else None


def _wo_flow_data(wo, user):
    """Everything the Work Order screen needs about Stage 2, masked by role."""
    is_client = user.roles == 'CLIENT'
    is_contractor = user.roles == 'CONTRACTOR'
    actions = stage2.available_actions(wo, user)

    lines = []
    for line in wo.quote_lines.all():
        entry = {'id': line.id, 'description': line.description, 'quantity': str(line.quantity)}
        if not is_client:
            entry.update(unit_cost_vendor=str(line.unit_cost_vendor), total_vendor=str(line.total_vendor))
        if not is_contractor:
            entry.update(unit_cost_client=str(line.unit_cost_client), total_client=str(line.total_client))
        lines.append(entry)

    pricing = {}
    if not is_contractor:
        pricing['client_price'] = _money(wo.client_price)
    if not is_client:
        pricing['vendor_cost'] = _money(wo.cost)
    if not (is_client or is_contractor) and wo.client_price and wo.cost is not None:
        margin = wo.client_price - wo.cost
        pricing['margin'] = str(margin)
        pricing['margin_percent'] = round(float(margin / wo.client_price * 100), 1) if wo.client_price else None

    chain = []
    for step in ('procurement', 'approver', 'client_rep'):
        people = stage2.people_for(wo, step)
        entry = {'step': step, 'label': stage2.STEP_LABELS[step], 'kind': 'team' if step == 'procurement' else 'named'}
        if step == 'procurement':
            entry['people'] = len(people)
        else:
            entry['person'] = (people[0].name.strip() or people[0].email) if people else None
        chain.append(entry)

    wr = wo.source_work_request
    return {
        'flow': wo.flow,
        'status': wo.approval_status,
        'waiting_on': stage2.WAITING_ON.get(wo.approval_status),
        'chain': chain,
        'lines': lines,
        'pricing': pricing,
        'vendor': None if is_client or wo.vendor_id is None else {
            'id': wo.vendor_id, 'name': wo.vendor.name, 'has_bank_details': wo.vendor.has_bank_details},
        'quotation_reference': wo.quotation_reference,
        'po_number': wo.po_number,
        'expected_start_date': wo.expected_start_date,
        'files': [{'id': f.id, 'url': f.file.url if f.file else None, 'name': f.file.name.rsplit('/', 1)[-1] if f.file else ''}
                  for f in wo.resources.all()] if not is_client else [],
        'pricing_problems': stage2.pricing_problems(wo) if 'submit' in actions else [],
        'price_check': stage2.price_check(wo) if not (is_client or is_contractor) else [],
        'accepted': {'at': wo.accepted_at, 'start_date': wo.confirmed_start_date,
                     'technician': wo.contractor_technician} if wo.accepted_at else None,
        'source_work_request': {'slug': wr.slug, 'number': wr.work_request_number} if wr else None,
        'history': [
            {'action': a.action, 'label': a.get_action_display(), 'actor': a.actor_name, 'role': a.actor_role,
             'on_behalf_of': a.on_behalf_of_name or None, 'reason': a.reason or None, 'signature': a.signature or None,
             'at': a.at, 'since_previous_seconds': a.since_previous.total_seconds() if a.since_previous else None}
            for a in history(wo)
        ],
        'timing': stage2.timing(wo),
        'my_actions': actions,
    }


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
        if role == 'CLIENT':
            return _client_work_orders(qs, user).order_by('-id')
        if role in SEE_ALL_ROLES:
            return qs.order_by('-id')
        # A Raise Payment bill's second approver sees it too, whatever their role.
        five_stage = Q(flow=WorkOrder.FIVE_STAGE)
        if role == 'REVIEWER':
            return qs.filter(Q(reviewers=user) | Q(final_approver=user)).distinct().order_by('-id')
        if role == 'APPROVER':
            return qs.filter(
                Q(approver=user) | Q(final_approver=user)
                | five_stage & Q(facility__in=_signer_facilities(user, 'approver'))
            ).distinct().order_by('-id')
        if role == 'PROCUREMENT AND STORE':
            return qs.filter(Q(owner=user) | Q(final_approver=user) | five_stage).distinct().order_by('-id')
        if role == 'REQUESTER':
            return qs.filter(
                Q(owner=user) | Q(final_approver=user) | five_stage & Q(facility__in=accessible_facilities(user))
            ).distinct().order_by('-id')
        if role == 'CONTRACTOR':
            # Only their own company's jobs, once the client has approved the price.
            if not user.vendor_id:
                return qs.none()
            return qs.filter(five_stage, vendor_id=user.vendor_id, approval_status='Approved').order_by('-id')
        return qs.filter(Q(owner=user) | Q(final_approver=user)).order_by('-id')

    def update(self, request, *args, **kwargs):
        if self.get_object().flow == WorkOrder.FIVE_STAGE:
            return Response({'error': "Change this work order through its own screen actions."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().flow == WorkOrder.FIVE_STAGE:
            return Response({'error': "Five-stage work orders are kept for the record and cannot be deleted."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    # ── Five-stage flow (Stage 2) ────────────────────────────────────────────

    def _stage2_call(self, request, func, *args, **kwargs):
        work_order = self.get_object()
        try:
            func(work_order, request.user, *args, **kwargs)
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        work_order.refresh_from_db()
        return Response(_wo_flow_data(work_order, request.user))

    @action(detail=False, methods=['get'], url_path='procurement-queue')
    def procurement_queue(self, request):
        """Client-approved Work Requests waiting for a Work Order (Procurement & Store)."""
        if request.user.roles not in ('PROCUREMENT AND STORE', 'SUPER ADMIN', 'ADMIN'):
            return Response([])
        rows = []
        for wr in stage2.ready_requests():
            client = wr.facility.client if wr.facility_id else None
            timing = (stage2.step_timing(stage2.STAGE, wr.fully_approved_at, client)
                      if wr.fully_approved_at else None)
            rows.append({'slug': wr.slug, 'number': wr.work_request_number, 'description': wr.description,
                         'facility': wr.facility.name if wr.facility_id else None,
                         'category': wr.category.name if wr.category_id else None,
                         'client_approved_at': wr.fully_approved_at, 'timing': timing})
        return Response(rows)

    @action(detail=False, methods=['post'], url_path='flow-start')
    def flow_start(self, request):
        work_request = get_object_or_404(WorkRequest, slug=request.data.get('work_request'))
        try:
            work_order = stage2.start(work_request, request.user)
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'slug': work_order.slug, **_wo_flow_data(work_order, request.user)},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def flow(self, request, slug=None):
        return Response(_wo_flow_data(self.get_object(), request.user))

    @action(detail=True, methods=['post'], url_path='flow-pricing')
    def flow_pricing(self, request, slug=None):
        lines = request.data.get('lines')
        if isinstance(lines, str):
            try:
                lines = json.loads(lines)
            except ValueError:
                return Response({'error': "The quote lines could not be read."}, status=status.HTTP_400_BAD_REQUEST)
        vendor = None
        if request.data.get('vendor'):
            vendor = Vendor.objects.filter(pk=request.data.get('vendor')).first()
            if vendor is None:
                return Response({'error': "That vendor does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        start = request.data.get('expected_start_date')
        return self._stage2_call(
            request, stage2.save_pricing, lines=lines, vendor=vendor,
            quotation_reference=request.data.get('quotation_reference'), po_number=request.data.get('po_number'),
            expected_start_date=start if start is not None else None, files=request.FILES.getlist('resources'),
        )

    @action(detail=True, methods=['post'], url_path='flow-submit')
    def flow_submit(self, request, slug=None):
        return self._stage2_call(request, stage2.submit)

    @action(detail=True, methods=['post'], url_path='flow-review')
    def flow_review(self, request, slug=None):
        return self._stage2_call(request, stage2.review, request.data.get('signature', ''), request.data.get('note', ''))

    @action(detail=True, methods=['post'], url_path='flow-send-back')
    def flow_send_back(self, request, slug=None):
        return self._stage2_call(request, stage2.send_back, request.data.get('reason', ''))

    @action(detail=True, methods=['post'], url_path='flow-approve')
    def flow_approve(self, request, slug=None):
        confirmed = str(request.data.get('confirmed', '')).lower() in ('true', '1', 'yes')
        return self._stage2_call(request, stage2.client_approve, request.data.get('signature', ''), confirmed)

    @action(detail=True, methods=['post'], url_path='flow-reject')
    def flow_reject(self, request, slug=None):
        return self._stage2_call(request, stage2.client_reject, request.data.get('reason', ''))

    @action(detail=True, methods=['post'], url_path='flow-accept')
    def flow_accept(self, request, slug=None):
        return self._stage2_call(request, stage2.accept, request.data.get('start_date') or None,
                                 request.data.get('technician', ''))

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

    @action(detail=True, methods=['post'], url_path='assign-routing')
    def assign_routing(self, request, slug=None):
        """
        Requester (or Admin) assigns Reviewer(s) and an Approver to their own
        Work Order — its own approval routing, separate from the Work
        Request's (the auto-created Work Order starts with neither set).
        Notifies the newly-assigned people by email + in-app immediately;
        the existing on_work_order_saved signal separately notifies the
        approver once the work order is actually Reviewed.
        """
        instance = get_object_or_404(WorkOrder, slug=slug)

        is_admin = request.user.roles in ('ADMIN', 'SUPER ADMIN')
        is_owner = instance.owner_id == request.user.id or instance.requester_id == request.user.id
        if not (is_admin or is_owner):
            return Response(
                {"error": "Only the Requester who raised this work order (or an Admin) can assign its routing."},
                status=status.HTTP_403_FORBIDDEN,
            )

        terminal_statuses = {'Approved', 'Reviewer Rejected', 'Approver Rejected', 'Rejected', 'Final Approver Rejected'}
        if instance.approval_status in terminal_statuses:
            return Response(
                {"error": f"Cannot change routing on a work order with status '{instance.approval_status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data
        reviewer_ids = data.getlist('reviewers') if hasattr(data, 'getlist') else data.get('reviewers', [])
        approver_id = data.get('approver')

        if not reviewer_ids and not approver_id:
            return Response({"error": "Provide at least one of reviewers, approver."}, status=status.HTTP_400_BAD_REQUEST)

        from work.utils.email_service import send_notification_email, create_in_app_notifications
        ctx = {'instance': instance}

        if reviewer_ids:
            instance.reviewers.set(reviewer_ids)
            reviewer_users = list(instance.reviewers.all())
            emails = [u.email for u in reviewer_users if u.email]
            send_notification_email(
                subject=f'[AlphaCMMS] Work Order {instance.work_order_number} — Review Required',
                template='emails/work_order_created.html',
                context=ctx,
                recipient_list=emails,
            )
            create_in_app_notifications(
                recipients=reviewer_users,
                title=f'Work Order {instance.work_order_number} — Review Required',
                message='You have been assigned to review this work order.',
                notification_type='WORK_ORDER',
                object_id=instance.pk,
            )

        if approver_id:
            instance.approver_id = approver_id
            instance.save(update_fields=['approver'])
            instance.refresh_from_db(fields=['approver'])
            if instance.approver and instance.approver.email:
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Order {instance.work_order_number} — Assigned as Approver',
                    template='emails/work_order_approver_assigned.html',
                    context=ctx,
                    recipient_list=[instance.approver.email],
                )
            create_in_app_notifications(
                recipients=[instance.approver] if instance.approver else [],
                title=f'Work Order {instance.work_order_number} — Assigned as Approver',
                message='You have been assigned as the approver for this work order.',
                notification_type='WORK_ORDER',
                object_id=instance.pk,
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Raise Payment, approver-first route: Approver → Reviewer → second approver for
    # large bills (see RaisePaymentApprovalSettings). Other work orders never come here.

    @action(detail=False, methods=['get'], url_path='final-approvers')
    def final_approvers(self, request):
        """Who the Requester can select as final approver, and from what amount it's required."""
        approval_settings = RaisePaymentApprovalSettings.current()
        user = approval_settings.second_approver()
        return Response({
            'threshold': str(approval_settings.threshold),
            'currency': 'NGN',
            'approvers': [{'id': user.id, 'name': user.name, 'email': user.email}] if user else [],
        })

    def _release_raise_payment(self, instance, user, **changes):
        """Last approval of a Raise Payment bill: approve it and raise its payment, all or nothing."""
        try:
            with transaction.atomic():
                for field, value in changes.items():
                    setattr(instance, field, value)
                instance.approval_status = 'Approved'
                instance.save(update_fields=[*changes, 'approval_status'])
                _create_raise_payment_requisition(instance, user)
        except Exception as exc:  # noqa: BLE001 — report it, approval was rolled back
            logger.error("Raise Payment approval failed for WorkOrder %s: %s", instance.pk, exc)
            return Response(
                {"error": "Approval failed while raising the payment requisition, so nothing was approved. "
                          "Please try again or contact an admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        instance.refresh_from_db()
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    def _raise_payment_first_approval(self, request, instance):
        if instance.approval_status != 'Pending':
            return Response(
                {"error": f"This bill is not waiting for the Approver (status '{instance.approval_status}')."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.roles == 'APPROVER':
            limit_error = _exceeds_approval_limit(request.user, instance.cost)
            if limit_error:
                return Response({"error": limit_error}, status=status.HTTP_403_FORBIDDEN)
        instance.is_approved = True
        instance.approval_status = 'Approver Approved'
        instance.save(update_fields=['is_approved', 'approval_status'])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    def _raise_payment_review(self, request, instance):
        if instance.approval_status != 'Approver Approved':
            return Response(
                {"error": "The Approver must approve this bill before the Reviewer can review it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        approval_settings = RaisePaymentApprovalSettings.current()
        if not approval_settings.needs_second_approval(instance.cost, instance.currency):
            return self._release_raise_payment(instance, request.user, is_reviewed=True)

        selected = instance.final_approver
        second_approver = selected if selected is not None and selected.is_active else approval_settings.second_approver()
        if second_approver is None:
            return Response(
                {"error": f"This bill needs a second approval, but no active AlphaCMMS user has the email "
                          f"{approval_settings.second_approver_email}. Ask the Super Admin to create that "
                          "account or update the Raise Payment approval setting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_reviewed = True
        instance.final_approver = second_approver
        instance.approval_status = 'Awaiting Final Approval'
        instance.save(update_fields=['is_reviewed', 'final_approver', 'approval_status'])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    def _check_final_approver(self, request, instance):
        if not instance.final_approver_id or instance.final_approver_id != request.user.pk:
            return Response(
                {"error": "Only the second approver named on this bill can act at this stage."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.approval_status != 'Awaiting Final Approval':
            return Response(
                {"error": f"This bill is not waiting for final approval (status '{instance.approval_status}')."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=['post'], url_path='final-approve')
    def final_approve(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        refused = self._check_final_approver(request, instance)
        if refused:
            return refused
        return self._release_raise_payment(instance, request.user, final_approved_at=timezone.now())

    @action(detail=True, methods=['post'], url_path='final-reject')
    def final_reject(self, request, slug=None):
        instance = get_object_or_404(WorkOrder, slug=slug)
        refused = self._check_final_approver(request, instance)
        if refused:
            return refused
        reason = (request.data.get('final_approver_reason') or '').strip()
        if not reason:
            return Response(
                {"error": "final_approver_reason is required when rejecting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.final_approver_reason = reason
        instance.approval_status = 'Final Approver Rejected'
        instance.save(update_fields=['final_approver_reason', 'approval_status'])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

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
        if instance.is_approver_first:
            return self._raise_payment_review(request, instance)
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
        if instance.is_approver_first and instance.approval_status != 'Approver Approved':
            return Response(
                {"error": "The Approver must approve this bill before the Reviewer can act on it."},
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
        if instance.is_approver_first:
            return self._raise_payment_first_approval(request, instance)
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

        if not instance.uses_raise_payment_flow:
            instance.is_approved = True
            instance.approval_status = 'Approved'
            instance.save(update_fields=['is_approved', 'approval_status'])
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Raise Payment: this approval is also the payment approval.
        if user.roles == 'APPROVER':
            limit_error = _exceeds_approval_limit(user, instance.cost)
            if limit_error:
                return Response({"error": limit_error}, status=status.HTTP_403_FORBIDDEN)
        try:
            with transaction.atomic():
                instance.is_approved = True
                instance.approval_status = 'Approved'
                instance.save(update_fields=['is_approved', 'approval_status'])
                _create_raise_payment_requisition(instance, user)
        except Exception as exc:  # noqa: BLE001 — report it, approval was rolled back
            logger.error("Raise Payment approval failed for WorkOrder %s: %s", instance.pk, exc)
            return Response(
                {"error": "Approval failed while raising the payment requisition, so nothing was approved. "
                          "Please try again or contact an admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        instance.refresh_from_db()
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
        if instance.is_approver_first:
            if instance.approval_status != 'Pending':
                return Response(
                    {"error": f"This bill is not waiting for the Approver (status '{instance.approval_status}')."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not instance.is_reviewed:
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

    # ── Work status: Closed / Pending / Rejected ────────────────────────────────

    @action(detail=True, methods=['post'], url_path='create-payment-requisition')
    def create_payment_requisition(self, request, slug=None):
        """
        Requester (or Admin) manually raises the Payment Requisition once an
        Approved WCC exists — lets this happen before the Work Order is
        closed, instead of only at close time. Idempotent via the same
        _auto_create_payment_requisition helper `set_status` itself uses, so
        closing afterwards just returns this same requisition rather than
        creating a duplicate.
        """
        instance = get_object_or_404(WorkOrder, slug=slug)

        is_admin = request.user.roles in ('ADMIN', 'SUPER ADMIN')
        is_owner = instance.owner_id == request.user.id or instance.requester_id == request.user.id
        if not (is_admin or is_owner):
            return Response(
                {"error": "Only the Requester who raised this work order (or an Admin) can raise its payment requisition."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if instance.uses_raise_payment_flow:
            requisition = instance.linked_payments.order_by('id').first()
            if requisition is None:
                return Response(
                    {"error": "A Raise Payment work order's payment requisition is raised automatically when it is fully approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {'id': requisition.id, 'requisition_number': requisition.requisition_number},
                status=status.HTTP_200_OK,
            )

        if not instance.completions.filter(approval_status='Approved').exists():
            return Response(
                {"error": "An approved Work Completion Certificate is required before a payment requisition can be raised."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requisition = _auto_create_payment_requisition(instance, request.user)
        if requisition is None:
            return Response(
                {"error": "Failed to create the payment requisition. Please try again or contact an admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {'id': requisition.id, 'requisition_number': requisition.requisition_number},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, slug=None):
        """
        Closed / Pending / Rejected tracking of the physical work — separate from
        approval_status.

        Closing (work_status='closed') requires technician, vendor, rating,
        started_at and completed_at (on the instance already, or in this
        request); an Approved WorkOrderCompletion (WCC) to already exist for
        this work order (the evidence gate); and its linked Payment
        Requisition to already be fully approved (approval_status='approve')
        — so a job can't be marked closed while its payment is still
        pending. On success this also (idempotently) ensures a Payment
        Requisition is linked, via _auto_create_payment_requisition — in the
        normal case it's already there from that last check, since
        create-payment-requisition or manual creation must have run first.
        """
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only APPROVER, ADMIN, or SUPER ADMIN can change a work order's status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(WorkOrder, slug=slug)

        new_status = (request.data.get('work_status') or '').strip().lower()
        valid_statuses = dict(WorkOrder.WORK_STATUS_CHOICES)
        if new_status not in valid_statuses:
            return Response(
                {"error": f"work_status must be one of {list(valid_statuses)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = ['work_status']
        expected_payment_date = None

        if new_status == 'closed' and instance.uses_raise_payment_flow:
            return Response(
                {"error": "A Raise Payment work order closes automatically when Finance disburses its payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == 'closed':
            if not instance.completions.filter(approval_status='Approved').exists():
                return Response(
                    {"error": "An approved Work Completion Certificate is required before this Work Order can be closed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            requisition = instance.linked_payments.order_by('id').first()
            if not requisition or requisition.approval_status != 'approve':
                return Response(
                    {"error": "The linked Payment Requisition must be fully approved before this Work Order can be closed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            vendor_id = request.data.get('vendor') or instance.vendor_id
            technician_id = request.data.get('technician') or instance.technician_id
            if not vendor_id:
                return Response({"error": "vendor is required to close this work order."}, status=status.HTTP_400_BAD_REQUEST)
            if not technician_id:
                return Response({"error": "technician is required to close this work order."}, status=status.HTTP_400_BAD_REQUEST)

            rating = request.data.get('rating')
            try:
                rating = int(rating)
                if rating not in range(1, 6):
                    raise ValueError
            except (TypeError, ValueError):
                return Response({"error": "rating is required and must be an integer from 1 to 5."}, status=status.HTTP_400_BAD_REQUEST)

            started_at = parse_datetime(request.data.get('started_at') or '')
            completed_at = parse_datetime(request.data.get('completed_at') or '')
            if not started_at or not completed_at:
                return Response(
                    {"error": "started_at and completed_at are required and must be ISO-8601 datetimes."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if request.data.get('vendor'):
                instance.vendor_id = vendor_id
                update_fields.append('vendor')
            if request.data.get('technician'):
                instance.technician_id = technician_id
                update_fields.append('technician')
            instance.rating = rating
            instance.started_at = started_at
            instance.completed_at = completed_at
            update_fields += ['rating', 'started_at', 'completed_at']

            expected_payment_date = request.data.get('expected_payment_date') or None

        instance.work_status = new_status

        reason = (request.data.get('reason') or '').strip()
        if new_status == 'rejected' and reason:
            instance.remark = reason
            update_fields.append('remark')

        instance.save(update_fields=update_fields)

        requisition = None
        if new_status == 'closed':
            requisition = _auto_create_payment_requisition(instance, request.user, expected_payment_date)

        data = self.get_serializer(instance).data
        data['payment_requisition'] = (
            {'id': requisition.id, 'requisition_number': requisition.requisition_number}
            if requisition else None
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_order(self, request, slug=None):
        allowed_roles = ['ADMIN', 'SUPER ADMIN', 'APPROVER']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only ADMIN, SUPER ADMIN, or APPROVER can approve work orders."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(WorkOrder, slug=slug)
        if instance.uses_raise_payment_flow:
            return Response(
                {"error": "Raise Payment work orders must be reviewed and then approved (approve-by-reviewer, approve-by-approver)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        rejected_statuses = {'Reviewer Rejected', 'Approver Rejected', 'Final Approver Rejected'}
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
    def approve(self, request, pk=None):
        """
        Note: previously looked up by `slug`, a field PaymentRequisition
        doesn't have (this viewset uses the default pk-based lookup) — the
        action could never actually be invoked. Fixed to pk, and the dead
        `instance.amount`/hardcoded-threshold check (amount was always 0,
        since PaymentRequisition has no `amount` field — the real field is
        `expected_payment_amount`) replaced with the same approval-limit
        matrix used on WorkRequest.final_approve.
        """
        instance = get_object_or_404(PaymentRequisition, pk=pk)
        if instance.is_disbursed:
            return Response(
                {"error": "This payment requisition has already been disbursed and is locked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_role = request.user.roles
        if user_role not in {'SUPER ADMIN', 'ADMIN', 'APPROVER'} | FINANCE_ROLES:
            return Response(
                {"error": "You do not have permission to approve this payment request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user_role == 'APPROVER':
            limit_error = _exceeds_approval_limit(request.user, instance.expected_payment_amount)
            if limit_error:
                return Response({"error": limit_error}, status=status.HTTP_403_FORBIDDEN)

        instance.approval_status = 'approve'
        instance.save(update_fields=['approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        instance = get_object_or_404(PaymentRequisition, pk=pk)
        if instance.is_disbursed:
            return Response(
                {"error": "This payment requisition has already been disbursed and is locked."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.roles not in {'SUPER ADMIN', 'ADMIN', 'APPROVER'} | FINANCE_ROLES:
            return Response(
                {"error": "You do not have permission to reject this payment request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        comment = (request.data.get('comment') or '').strip()
        if not comment:
            return Response({"error": "comment is required when rejecting."}, status=status.HTTP_400_BAD_REQUEST)
        instance.approval_status = 'reject'
        instance.comment = comment
        instance.save(update_fields=['approval_status', 'comment'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='disburse')
    def disburse(self, request, pk=None):
        """Finance's final step. Locks the record — see PaymentRequisitionSerializer.validate."""
        if request.user.roles not in {'SUPER ADMIN', 'ADMIN'} | FINANCE_ROLES:
            return Response(
                {"error": "Only HEAD OF FINANCE & TREASURY, ADMIN, or SUPER ADMIN can disburse a payment."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = get_object_or_404(PaymentRequisition, pk=pk)
        if instance.is_disbursed:
            return Response({"error": "This payment requisition has already been disbursed."}, status=status.HTTP_400_BAD_REQUEST)
        if instance.approval_status != 'approve':
            return Response(
                {"error": f"Cannot disburse a payment with status '{instance.approval_status}'. Expected 'approve'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.pay_to_id and not instance.pay_to.has_bank_details:
            return Response(
                {"error": f"'{instance.pay_to.name}' has no bank details yet. Ask the Super Admin to add "
                          "the account name, bank and account number before disbursing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        with transaction.atomic():
            instance.is_disbursed = True
            instance.disbursed_at = now
            instance.disbursed_by = request.user
            instance.save(update_fields=['is_disbursed', 'disbursed_at', 'disbursed_by'])

            # Raise Payment: disbursement is the last step — close the
            # requisition and its work order automatically.
            raise_payment_orders = instance.work_orders.filter(type=WorkOrder.RAISE_PAYMENT, payee__isnull=False)
            if raise_payment_orders.exists():
                for work_order in raise_payment_orders:
                    if work_order.work_status != 'closed':
                        work_order.work_status = 'closed'
                        work_order.completed_at = now
                        work_order.save(update_fields=['work_status', 'completed_at'])
                instance.is_closed = True
                instance.closed_at = now
                instance.closed_by = request.user
                instance.save(update_fields=['is_closed', 'closed_at', 'closed_by'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """
        The Requester's own final step, separate from Finance's `disburse`
        above — confirms the loop is done and archives the record. Only
        possible once Finance has actually disbursed the payment.
        """
        instance = get_object_or_404(PaymentRequisition, pk=pk)
        is_admin = request.user.roles in ('ADMIN', 'SUPER ADMIN')
        is_owner = instance.owner_id == request.user.id
        if not (is_admin or is_owner):
            return Response(
                {"error": "Only the Requester who owns this payment requisition (or an Admin) can close it."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.is_closed:
            return Response({"error": "This payment requisition has already been closed."}, status=status.HTTP_400_BAD_REQUEST)
        if not instance.is_disbursed:
            return Response(
                {"error": "This payment requisition must be disbursed by Finance before it can be closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_closed = True
        instance.closed_at = timezone.now()
        instance.closed_by = request.user
        instance.save(update_fields=['is_closed', 'closed_at', 'closed_by'])
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
        if role == 'CLIENT':
            visible_orders = _client_work_orders(WorkOrder.objects.all(), user)
            return qs.filter(work_order__in=visible_orders).order_by('-id')
        if role in SEE_ALL_ROLES:
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
                    f"(WCC-{conflict.wcc_number or conflict.pk}, status: {conflict.approval_status}). "
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
        ).exclude(id__in=blocked_wo_ids).exclude(type=WorkOrder.RAISE_PAYMENT, payee__isnull=False).order_by('-id')
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
        # No manual "create" step any more — the Payment Requisition is
        # ready to be filled in the moment its WCC is Approved. Owned by the
        # Work Order's own Requester (not whoever approved the WCC), so it's
        # the same person who's allowed to fill it in and close it later.
        if instance.work_order_id:
            _auto_create_payment_requisition(instance.work_order, instance.work_order.requester)
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
        if role in SEE_ALL_INVOICE_ROLES:
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
