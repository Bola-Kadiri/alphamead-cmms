# work/api/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from cmms_instanta.permissions import RoleBasedPermissionMixin
from work.models import WorkRequest, WorkOrder, Comment, PaymentItem, PaymentRequisition, PPM, WorkOrderCompletion
from .serializers import WorkRequestSerializer, WorkOrderSerializer, CommentSerializer, PaymentItemSerializer, PaymentRequisitionSerializer, PPMSerializer, WorkOrderCompletionSerializer

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from accounts.models import Personnel, Vendor
from accounts.api.serializers import PersonnelSerializer, VendorSerializer

# Import facility and asset models and serializers
from facility.models import Facility, Building
from facility.api.serializers import BuildingSerializer
from asset_inventory.models import Asset
from asset_inventory.api.serializers import AssetSerializer

User = get_user_model()


class WorkRequestViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    # queryset = WorkRequest.objects.all().order_by('-id')
    serializer_class = WorkRequestSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """
        This view should return a list of all the work requests
        for the currently authenticated user if they are not an admin.
        """
        user = self.request.user
        if user.is_authenticated:
            # Add your admin roles here
            admin_roles = ['Super Admin', 'Facility Admin'] 
            if user.roles not in admin_roles:
                return WorkRequest.objects.filter(owner=user).order_by('-id')
        return WorkRequest.objects.all().order_by('-id')

    def perform_create(self, serializer):
        # Only allow creation by Facility Officer, Facility Store, or Facility Admin
        allowed_roles = ['Facility Officer', 'Facility Store', 'Facility Admin']
        if self.request.user.roles not in allowed_roles:
            raise PermissionError("Only Facility Officer, Facility Store, or Facility Admin can create work requests.")
        serializer.save(owner=self.request.user, requester=self.request.user)
        
    @action(detail=False, methods=['get'], url_path='procurement-users')
    def procurement_users(self, request):
        procurement_users = User.objects.filter(roles='Facility Procurement')
        data = [{"id": user.id, "name": user.name, "email": user.email} for user in procurement_users]
        return Response(data)
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_request(self, request, slug):
        # Only allow approval by Facility Manager, Facility Auditor, or Facility Admin
        allowed_roles = ['Facility Manager', 'Facility Auditor', 'Facility Admin']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only Facility Manager, Facility Auditor, or Facility Admin can approve work requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = get_object_or_404(WorkRequest, slug=slug)
        
        # Get approval data from request
        cost = request.data.get('cost')
        currency = request.data.get('currency')
        priority = request.data.get('priority')
        approval_status = request.data.get('approval_status')
        
        # Validate required fields
        required_fields = ['cost', 'currency', 'priority', 'approval_status']
        missing_fields = [field for field in required_fields if request.data.get(field) is None]
        if missing_fields:
            return Response(
                {"error": f"Missing required field(s): {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate values
        if priority not in ['Low', 'Medium', 'High']:
            return Response({"error": "Priority must be one of: Low, Medium, High"}, status=status.HTTP_400_BAD_REQUEST)
        
        if currency not in ['USD', 'EUR', 'NGN']:
            return Response({"error": "Currency must be one of: USD, EUR, NGN"}, status=status.HTTP_400_BAD_REQUEST)
        
        if approval_status not in ['Approved', 'Rejected']:
            return Response({"error": "Approval status must be one of: Approved, Rejected"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the work request
        instance.approval_status = approval_status
        instance.cost = cost
        instance.currency = currency
        instance.priority = priority
        instance.save(update_fields=['approval_status', 'cost', 'currency', 'priority'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='po-requisition')
    def po_requisition(self, request):
        """
        Get all work requests that are assigned to users with Facility Procurement role.
        Only Facility Procurement users can access this endpoint.
        """
        # Check if user has Facility Procurement role
        if request.user.roles != 'Facility Procurement':
            return Response(
                {"error": "Only users with Facility Procurement role can access this endpoint."}, 
                status=status.HTTP_403_
            )
        
        # Get all work requests assigned to Facility Procurement users
        procurement_users = User.objects.filter(roles='Facility Procurement')
        work_requests = WorkRequest.objects.filter(
            request_to__in=procurement_users
        ).distinct().order_by('-id')
        
        serializer = self.get_serializer(work_requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'patch'], url_path='update-requisition')
    def update_requisition(self, request, slug):
        """
        Allow Facility Procurement users to update work requests assigned to them.
        """
        # Check if user has Facility Procurement role
        if request.user.roles != 'Facility Procurement':
            return Response(
                {"error": "Only users with Facility Procurement role can update work requests."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        
        # Check if the current user is assigned to this work request
        if request.user not in instance.request_to.all():
            return Response(
                {"error": "You can only update work requests assigned to you."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='buildings-by-facility/(?P<facility_id>[^/.]+)')
    def buildings_by_facility(self, request, facility_id=None):
        """
        Get all buildings for a specific facility.
        """
        try:
            # Get the facility by ID
            facility = get_object_or_404(Facility, id=facility_id)
            
            # Get all buildings associated with this facility
            buildings = Building.objects.filter(facility=facility).order_by('-id')
            
            serializer = BuildingSerializer(buildings, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"Error retrieving buildings: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='assets-by-facility/(?P<facility_id>[^/.]+)')
    def assets_by_facility(self, request, facility_id=None):
        """
        Get all assets for a specific facility.
        """
        try:
            # Get the facility by ID
            facility = get_object_or_404(Facility, id=facility_id)
            
            # Get all assets associated with this facility
            assets = Asset.objects.filter(facility=facility).order_by('-id')
            
            serializer = AssetSerializer(assets, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"Error retrieving assets: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkOrderViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all().order_by('-id')
    serializer_class = WorkOrderSerializer
    permission_classes = [IsAuthenticated]
    feature = "work_order"
    lookup_field = 'slug'

    def perform_create(self, serializer):
        # Only allow creation by Facility Officer, Facility Store, or Facility Admin
        allowed_roles = ['Facility Officer', 'Facility Store', 'Facility Admin']
        if self.request.user.roles not in allowed_roles:
            raise PermissionError("Only Facility Officer, Facility Store, or Facility Admin can create work orders.")
        serializer.save(owner=self.request.user, requester=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_order(self, request, slug=None):
        # Only allow approval by Facility Manager, Facility Auditor, or Facility Admin
        allowed_roles = ['Facility Manager', 'Facility Auditor', 'Facility Admin']
        if request.user.roles not in allowed_roles:
            return Response(
                {"error": "Only Facility Manager, Facility Auditor, or Facility Admin can approve work orders."},
                status=status.HTTP_403_FORBIDDEN
            )
        # Filter by slug
        instance = get_object_or_404(WorkOrder, slug=slug)
        instance.approval_status = 'Approved'
        instance.save(update_fields=['approval_status'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentRequisitionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = PaymentRequisition.objects.all().order_by('-id')
    serializer_class = PaymentRequisitionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Only allow creation by Facility Officer, Facility Store, or Facility Admin
        allowed_roles = ['Facility Officer', 'Facility Store', 'Facility Admin']
        if self.request.user.roles not in allowed_roles:
            raise PermissionError("Only Facility Officer, Facility Store, or Facility Admin can create payment requests.")
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, slug):
        # Approval logic based on role and amount
        instance = get_object_or_404(PaymentRequisition, slug=slug)
        user_role = request.user.roles
        amount = instance.amount if hasattr(instance, 'amount') else 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0

        if user_role == 'Facility Account':
            pass  # Always allowed
        elif user_role == 'Facility Admin' and amount > 1000000:
            pass  # Allowed for > 1,000,000
        elif user_role == 'Facility Manager' and amount <= 1000000:
            pass  # Allowed for <= 1,000,000
        else:
            return Response(
                {"error": "You do not have permission to approve this payment request."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.approval_status = 'Approved'
        instance.save(update_fields=['approval_status'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='personnel-list')
    def personnel_list(self, request):
        """
        Returns a list of all Personnel.
        """
        personnel = Personnel.objects.all()
        serializer = PersonnelSerializer(personnel, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='vendor-list')
    def vendor_list(self, request):
        """
        Returns a list of all Vendors.
        """
        vendors = Vendor.objects.all()
        serializer = VendorSerializer(vendors, many=True)
        return Response(serializer.data)


class PaymentItemViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all().order_by('-id')
    serializer_class = PaymentItemSerializer
    feature = "requisition"
    # permission_classes = [IsAuthenticated]


class CommentViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-id')
    serializer_class = CommentSerializer
    feature = "comment"
    # permission_classes = [IsAuthenticated]


class PPMViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = PPM.objects.all().order_by('-id')
    serializer_class = PPMSerializer
    feature = "ppm_setting"
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class WorkOrderCompletionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = WorkOrderCompletion.objects.all().order_by('-id')
    serializer_class = WorkOrderCompletionSerializer
    permission_classes = [IsAuthenticated]
