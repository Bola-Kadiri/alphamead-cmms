from rest_framework import serializers
from ..models import Asset, Inventory, Warehouse, Item, ItemRequest, ItemRequestItem, Transfer, Store, MovementHistory
from accounts.models import Vendor, Category, Subcategory, User, Department
from facility.models import Facility, Building 

from accounts.api.serializers import VendorSerializer,  SimpleUserSerializer
from facility.api.serializers import FacilitySerializer, BuildingSerializer
from utils.serializers import ImageAttachmentSerializer

from utils.mixin import TranslatedSerializerMixin
from utils.translation_mixin import TranslatableFieldMixin
from asset_inventory.models.inventory_reference import (InventoryType, Manufacturer, 
                                                        ModelReference, InventoryReference)
from asset_inventory.models.assets_category import AssetCategory, AssetSubCategory


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = [
            'id', 'type', 'code', 'name', 'salvage_value_percent', 'useful_life_year', 'description'
        ]
        read_only_fields = ['id']

class AssetSubCategorySerializer(serializers.ModelSerializer):
    asset_category_detail = AssetCategorySerializer(source='asset_category', read_only=True)
    class Meta:
        model = AssetSubCategory
        fields = [
            'id', 'code', 'name', 'type', 'description', 'asset_category', 
            'asset_category_detail', 'is_active'
        ]
        read_only_fields = ['id', 'asset_category_detail']
        

class WarehouseSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    facility_detail = FacilitySerializer(source='facility', read_only=True)

    class Meta:
        model = Warehouse
        fields = [
            'id',
            'code',
            'name',
            'description',
            'address',
            'capacity',
            'facility',
            'facility_detail',
            'is_active',
        ]
        read_only_fields = ['id']
        translatable_fields = ['capacity','description']
        

class StoreSerializer(serializers.ModelSerializer):
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    warehouse_detail = WarehouseSerializer(source='warehouse', read_only=True)

    class Meta:
        model = Store
        fields = [
            'id',
            'facility',
            'facility_detail',
            'warehouse',
            'warehouse_detail',
            'name',
            'code',
            'capacity',
            'location',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
        
class AssetSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)

    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ['id', 'amount']
        translatable_fields = ('oem_warranty',)
        
        
class InventorySerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    log_value = serializers.ReadOnlyField()
    total_value = serializers.ReadOnlyField()

    class Meta:
        model = Inventory
        fields = [
            'id',
            'type',
            'category', 'category_detail',
            'subcategory', 'subcategory_detail',
            'model',
            'part_no',
            'tag',
            'serial_number',
            'quantity',
            'unit_price',
            'log_value',
            'vendor', 'vendor_detail',
            'purchase_number',
            'purchase_date',
            'manufacture_date',
            'expiry_date',
            'warranty_end_date',
            'facility', 'facility_detail',
            'reorder_level',
            'minimum_stock',
            'max_stock',
            'flags',
            'status',
            'created_at',
            'updated_at',
            'total_value',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'log_value',
            'total_value',
        ]
        

class ItemSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'
        translatable_fields = ['description']      


class TransferSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    items = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        many=True,
        required=True
    )
    confirmation_required_from = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )
    # requested_by = serializers.PrimaryKeyRelatedField(
    #     queryset=User.objects.all(),
    #     required=False
    # )
    request_from = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        allow_null=True
    )
    transfer_to = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        allow_null=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=AssetCategory.objects.all(),
        allow_null=True
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=AssetSubCategory.objects.all(),
        allow_null=True
    )

    # Detail fields for related objects
    request_from_detail = StoreSerializer(source='request_from', read_only=True)
    transfer_to_detail = StoreSerializer(source='transfer_to', read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    requested_by_detail = SimpleUserSerializer(source='requested_by', read_only=True)
    confirmation_required_from_detail = SimpleUserSerializer(
        source='confirmation_required_from',
        many=True,
        read_only=True
    )

    class Meta:
        model = Transfer
        fields = [
            'id', 'request_from', 'required_date', 
            # 'requested_by', 
            'transfer_to',
            'type', 'category', 'subcategory', 'items', 'confirmation_required_from',
            'request_from_detail', 'transfer_to_detail', 'category_detail',
            'subcategory_detail', 'requested_by_detail', 'confirmation_required_from_detail'
        ]
        read_only_fields = ['id']
        translatable_fields = []  

    def validate(self, data):
        print("TransferSerializer data:", data)
        if not data.get('items'):
            print("No items provided:", data)
            raise serializers.ValidationError({"items": "At least one item is required."})
        if data.get('request_from') == data.get('transfer_to'):
            raise serializers.ValidationError({"transfer_to": "Transfer destination cannot be the same as the source."})
        return data

    def create(self, validated_data):
        # Remove many-to-many fields from validated_data
        items_data = validated_data.pop('items', [])
        confirmation_required_from_data = validated_data.pop('confirmation_required_from', [])
        # Create the Transfer instance
        transfer = Transfer.objects.create(**validated_data)
        # Set many-to-many relationships
        transfer.items.set(items_data)
        transfer.confirmation_required_from.set(confirmation_required_from_data)
        return transfer
"""
class TransferSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    request_from_detail = StoreSerializer(source='request_from', read_only=True)
    transfer_to_detail = StoreSerializer(source='transfer_to', read_only=True)
    requested_by_detail = SimpleUserSerializer(source='requested_by', read_only=True)
    items_detail = ItemSerializer(source='items', many=True, read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    confirmation_required_from_detail = SimpleUserSerializer(source='confirmation_required_from', many=True, read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id',
            'type',
            'request_from', 'request_from_detail',
            'required_date',
            'requested_by', 'requested_by_detail',
            'transfer_to', 'transfer_to_detail',
            'category', 'category_detail',
            'subcategory', 'subcategory_detail',
            'items', 'items_detail',
            'confirmation_required_from', 'confirmation_required_from_detail',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]
"""

class MovementHistorySerializer(serializers.ModelSerializer):
    inventory_detail = InventorySerializer(source='inventory', read_only=True)
    from_store_detail = StoreSerializer(source='from_store', read_only=True)
    to_store_detail = StoreSerializer(source='to_store', read_only=True)
    user_detail = SimpleUserSerializer(source='user', read_only=True)

    class Meta:
        model = MovementHistory
        fields = [
            "id", "inventory", "inventory_detail", "user", "user_detail", "model", "movement_date",
            "from_store", "from_store_detail", "to_store", "to_store_detail",
            "transfer_quantity", "transfer_unit_price", "transfer_amount", "description"
        ]
        read_only_fields = ["id", "movement_date", "transfer_amount"]

class InventoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryType
        fields = "__all__"

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = "__all__"

class ModelReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelReference
        fields = "__all__"

class InventoryReferenceSerializer(serializers.ModelSerializer):
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    class Meta:
        model = InventoryReference
        fields = "__all__"
        extra_fields = ['category_detail', 'subcategory_detail']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['category_detail'] = AssetCategorySerializer(instance.category).data if instance.category else None
        rep['subcategory_detail'] = AssetSubCategorySerializer(instance.subcategory).data if instance.subcategory else None
        return rep



class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department  
        fields = ['id', 'name']
        ref_name = 'AssetDepartment'

class ItemRequestItemSerializer(serializers.ModelSerializer):
    item_id = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), source='item', write_only=True, help_text="ID of the item (required for creation)")
    item = serializers.ReadOnlyField(source='item.id', help_text="ID of the associated item (read-only)")
    category = serializers.PrimaryKeyRelatedField(queryset=AssetCategory.objects.all(), allow_null=True, help_text="Category of the item (optional)")
    subcategory = serializers.PrimaryKeyRelatedField(queryset=AssetSubCategory.objects.all(), allow_null=True, help_text="Subcategory of the item (optional)")
    model = serializers.PrimaryKeyRelatedField(queryset=ModelReference.objects.all(), allow_null=True, help_text="Model of the item (optional)")
    # Detail fields for related objects
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    model_detail = ModelReferenceSerializer(source='model', read_only=True)

    class Meta:
        model = ItemRequestItem
        fields = [
            'item_id', 'item', 'quantity', 'description',
            'category', 'subcategory', 'model',
            'category_detail', 'subcategory_detail', 'model_detail'
        ]

    def validate(self, data):
        print("ItemRequestItemSerializer data:", data)
        if not data.get('item'):
            raise serializers.ValidationError({"item_id": "A valid item ID is required."})
        if not isinstance(data.get('quantity', 0), int) or data.get('quantity', 0) <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be a positive integer."})
        return data
    
class ItemRequestSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    items = ItemRequestItemSerializer(many=True, required=True, help_text="List of items requested (required)")
    requested_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False, help_text="User who requested the item (optional)")
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), allow_null=True, help_text="Department associated with the request (optional)")
    request_from = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), allow_null=True, help_text="Store from which the item is requested (optional)")
    facility = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all(), allow_null=True, help_text="Facility associated with the request (optional)")
    building = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), allow_null=True, help_text="Building associated with the request (optional)")
    file = serializers.FileField(required=False, write_only=True, allow_null=True, help_text="Uploaded document (e.g., PDF, DOCX; optional, max 5MB)")
    approved_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=True, help_text="User designated to approve the request (set via approval action)")
    status = serializers.CharField(read_only=True, help_text="Current status of the request (Submitted, Pending Approval, Approved, Rejected; updated via approval action)")
    # Detail fields for related objects
    department_detail = DepartmentSerializer(source='department', read_only=True)
    request_from_detail = StoreSerializer(source='request_from', read_only=True)
    requested_by_detail = SimpleUserSerializer(source='requested_by', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    building_detail = BuildingSerializer(source='building', read_only=True)

    class Meta:
        model = ItemRequest
        fields = [
            'id', 'name', 'description', 'request_from', 'required_date',
            'requested_by', 'department', 'type', 'facility', 'building',
            'comment', 'file', 'approved_by', 'items', 'status',
            'department_detail', 'request_from_detail', 'requested_by_detail',
            'facility_detail', 'building_detail'
        ]
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        # Remove items from validated_data to prevent ManyToManyField assignment
        validated_data.pop('items', None)
        # Create the ItemRequest instance           
        return ItemRequest.objects.create(**validated_data)
    
    # def create(self, validated_data):
    #     items_data = validated_data.pop('items', None)
    #     item_request = ItemRequest.objects.create(**validated_data)
    #     if items_data:
    #         for item_data in items_data:
    #             ItemRequestItem.objects.create(
    #                 item_request=item_request,
    #                 item_id=item_data.get('item_id'),
    #                 quantity=item_data.get('quantity', 1),
    #                 description=item_data.get('description', ''),
    #                 category=item_data.get('category'),
    #                 subcategory=item_data.get('subcategory'),
    #                 model=item_data.get('model')
    #             )
    #     return item_request

    def validate_file(self, value):
        if value:
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size must not exceed 5MB.")
            allowed_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF and DOCX files are allowed.")
        return value

    def validate(self, data):
        print("ItemRequestSerializer data:", data)
        if not data.get('items'):
            print("No items provided:", data)
            raise serializers.ValidationError({"items": "At least one item is required."})
        return data

    def update(self, instance, validated_data):
        # Make approved_by read-only after creation
        if 'approved_by' in validated_data and instance.approved_by_id is not None:
            raise serializers.ValidationError({"approved_by": "Approved by cannot be changed after creation."})
        return super().update(instance, validated_data)
    
"""
class ItemRequestSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    items = ItemRequestItemSerializer(many=True, required=True, help_text="List of items requested (required)")
    requested_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False, help_text="User who requested the item (optional)")
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), allow_null=True, help_text="Department associated with the request (optional)")
    request_from = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), allow_null=True, help_text="Store from which the item is requested (optional)")
    facility = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all(), allow_null=True, help_text="Facility associated with the request (optional)")
    building = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), allow_null=True, help_text="Building associated with the request (optional)")
    file = serializers.FileField(required=False, allow_null=True, help_text="Uploaded document (e.g., PDF, DOCX; optional, max 5MB)")
    approved_by = serializers.PrimaryKeyRelatedField(read_only=True, help_text="User who approved the request (read-only)")
    status = serializers.CharField(read_only=True, help_text="Current status of the request (Submitted, Pending Approval, Approved, Rejected)")
    # Detail fields for related objects
    department_detail = DepartmentSerializer(source='department', read_only=True)
    request_from_detail = StoreSerializer(source='request_from', read_only=True)
    requested_by_detail = SimpleUserSerializer(source='requested_by', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    building_detail = BuildingSerializer(source='building', read_only=True)

    class Meta:
        model = ItemRequest
        fields = [
            'id', 'name', 'description', 'request_from', 'required_date',
            'requested_by', 'department', 'type', 'facility', 'building',
            'comment', 'file', 'approved_by', 'items', 'status',
            'department_detail', 'request_from_detail', 'requested_by_detail',
            'facility_detail', 'building_detail'
        ]
        read_only_fields = ['id', 'status', 'approved_by']
        translatable_fields = ['description', 'comment']

    def validate_file(self, value):
        if value:  # Only validate if a file is provided (since it's optional)
            # Restrict file size to 5MB (adjust as needed)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size must not exceed 5MB.")
            # Optional: Restrict to specific file types
            allowed_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF and DOCX files are allowed.")
        return value

    def validate(self, data):
        print("ItemRequestSerializer data:", data)
        if not data.get('items'):
            print("No items provided:", data)
            raise serializers.ValidationError({"items": "At least one item is required."})
        return data

    def create(self, validated_data):
        # Extract items data
        items_data = validated_data.pop('items', None)
        # Create the ItemRequest instance
        item_request = ItemRequest.objects.create(**validated_data)
        # Create ItemRequestItem instances
        if items_data:
            for item_data in items_data:
                ItemRequestItem.objects.create(item_request=item_request, **item_data)
        return item_request
"""
