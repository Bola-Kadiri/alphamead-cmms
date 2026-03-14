from django.db import transaction
from django.db.models import Sum, F

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from rest_framework import serializers


from cmms_instanta.permissions import RoleBasedPermissionMixin

from ..models import Asset, Inventory, Warehouse, Transfer, Item, Store, ItemRequest, ItemRequestItem
from accounts.models import Vendor, Category, Subcategory, Department
from asset_inventory.models import MovementHistory
from asset_inventory.models.inventory_reference import InventoryType, Manufacturer, ModelReference, InventoryReference
from asset_inventory.models.assets_category import AssetCategory, AssetSubCategory

from .serializers import (AssetSerializer, InventorySerializer, WarehouseSerializer, 
                          TransferSerializer, ItemSerializer, MovementHistorySerializer, 
                          InventoryTypeSerializer, ManufacturerSerializer, ModelReferenceSerializer, 
                          InventoryReferenceSerializer, AssetCategorySerializer, DepartmentSerializer,
                          AssetSubCategorySerializer, StoreSerializer, ItemRequestSerializer)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class StoreViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Store.objects.select_related('facility', 'warehouse').all().order_by('-id')
    serializer_class = StoreSerializer
    # feature = "store_management"
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class WarehouseViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('-id')
    serializer_class = WarehouseSerializer
    feature = "inventory_register"
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AssetViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.all().order_by('-created_at')
    serializer_class = AssetSerializer
    feature = "asset_register"
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
        
class InventoryViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Inventory.objects.all().order_by('-updated_at')
    serializer_class = InventorySerializer
    feature = "inventory_adjustment"
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
    

class ItemViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('name')
    serializer_class = ItemSerializer
    feature = "item_request"
    # permission_classes = [IsAuthenticated]


class TransferViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.select_related(
        'request_from', 'transfer_to', 'requested_by', 'category', 'subcategory'
    ).prefetch_related('items', 'confirmation_required_from')
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]
    feature = "movement_history"

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("Raw request.data:", request.data)
        data = request.data.copy()
        print("Data after copy:", data)

        # Create the Transfer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save(requested_by=request.user, user=request.user)

        # Return the created Transfer with related details
        serializer = self.get_serializer(transfer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
"""
class TransferViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.all().order_by('-id')
    serializer_class = TransferSerializer
    feature = "transfer_form"
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
"""


class MovementHistoryViewSet(viewsets.ModelViewSet):
    queryset = MovementHistory.objects.select_related('inventory', 'user', 'from_store', 'to_store').all().order_by('-movement_date')
    serializer_class = MovementHistorySerializer
    feature = "movement_history"
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InventoryTypeViewSet(viewsets.ModelViewSet):
    queryset = InventoryType.objects.all()
    serializer_class = InventoryTypeSerializer


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer


class ModelReferenceViewSet(viewsets.ModelViewSet):
    queryset = ModelReference.objects.all()
    serializer_class = ModelReferenceSerializer


class InventoryReferenceViewSet(viewsets.ModelViewSet):
    queryset = InventoryReference.objects.all()
    serializer_class = InventoryReferenceSerializer


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all().order_by('-id')
    serializer_class = AssetCategorySerializer
    feature = "asset_category"


class AssetSubCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetSubCategory.objects.all().order_by('-id')
    serializer_class = AssetSubCategorySerializer
    feature = "asset_subcategory"

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('-id')
    serializer_class = DepartmentSerializer
    # feature = "department_management"
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ItemRequestViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = ItemRequest.objects.all()
    serializer_class = ItemRequestSerializer
    permission_classes = [IsAuthenticated]
    feature = "item_request"

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("Raw request.data:", request.data)
        data = request.data.copy()
        items_data = data.get('items', [])
        print("Items data:", items_data)

        # Validate that items are provided
        if not items_data:
            return Response({"items": "At least one item is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the ItemRequest
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        item_request = serializer.save(requested_by=request.user)

        # Create ItemRequestItem entries
        for item_data in items_data:
            category = AssetCategory.objects.get(id=item_data.get('category')) if item_data.get('category') else None
            subcategory = AssetSubCategory.objects.get(id=item_data.get('subcategory')) if item_data.get('subcategory') else None
            model = ModelReference.objects.get(id=item_data.get('model')) if item_data.get('model') else None

            try:
                ItemRequestItem.objects.create(
                    item_request=item_request,
                    item_id=item_data.get('item_id'),
                    quantity=item_data.get('quantity', 1),
                    description=item_data.get('description', ''),
                    category=category,
                    subcategory=subcategory,
                    model=model
                )
            except Exception as e:
                print(f"Error creating ItemRequestItem: {e}")
                return Response({"error": f"Failed to create item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Return the created ItemRequest with related items
        serializer = self.get_serializer(item_request)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_description="Approve or reject an item request",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['Pending Approval', 'Approved', 'Rejected'],
                    description="New status to set for the request"
                )
            },
            required=['status']
        ),
        responses={200: ItemRequestSerializer(), 400: "Error response", 403: "Forbidden"}
    )
    @transaction.atomic
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve or reject an item request."""
        item_request = self.get_object()
        requested_status = request.data.get('status') 

        valid_statuses = [choice[0] for choice in item_request._meta.get_field('status').choices]
        if not requested_status or requested_status not in valid_statuses:
            return Response({"error": "Invalid or missing status value"}, status=status.HTTP_400_BAD_REQUEST)

        if requested_status in ['Approved', 'Rejected'] and item_request.status != 'Pending Approval':
            return Response({"error": "Can only approve or reject from Pending Approval status"}, status=status.HTTP_400_BAD_REQUEST)

        if item_request.approved_by != request.user and not request.user.is_staff:
            return Response({"error": "Only the designated approver or an admin can approve this request"}, status=status.HTTP_403_FORBIDDEN)

        try:
            item_request.approve(request.user, requested_status)
            serializer = self.get_serializer(item_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
"""
class ItemRequestViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = ItemRequest.objects.all()
    serializer_class = ItemRequestSerializer
    permission_classes = [IsAuthenticated]
    feature = "item_request"

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("Raw request.data:", request.data)
        data = request.data.copy()
        items_data = data.get('items', [])
        print("Items data:", items_data)

        # Validate that items are provided
        if not items_data:
            return Response({"items": "At least one item is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the ItemRequest
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        item_request = serializer.save(requested_by=request.user)

        # Create ItemRequestItem entries
        for item_data in items_data:
            try:
                ItemRequestItem.objects.create(
                    item_request=item_request,
                    item_id=item_data.get('item_id'),
                    quantity=item_data.get('quantity', 1),
                    description=item_data.get('description', '')
                )
            except Exception as e:
                print(f"Error creating ItemRequestItem: {e}")
                return Response({"error": f"Failed to create item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Return the created ItemRequest with related items
        serializer = self.get_serializer(item_request)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)  
"""
