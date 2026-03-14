from django.contrib import admin
from .models import Warehouse, Asset, Item, Transfer, Inventory, MovementHistory, Store, ItemRequest, ItemRequestItem
from .models.inventory_reference import InventoryType, Manufacturer, ModelReference, InventoryReference
from .models.assets_category import AssetCategory, AssetSubCategory


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "address",
        "capacity",
        "facility",
        "is_active",
        "owner",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "facility")
    search_fields = ("code", "name", "address")

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'asset_name',
        'asset_tag',
        'asset_type',
        'condition',
        'facility',
        'zone',
        'building',
        'subsystem',
        'category',
        'subcategory',
        'purchase_date',
        'purchased_amount',
    )
    list_filter = (
        'asset_type',
        'condition',
        'facility',
        'zone',
        'building',
        'subsystem',
        'category',
        'subcategory',
    )
    search_fields = (
        'asset_name',
        'serial_number',
        'asset_tag',
    )
    readonly_fields = ('serial_number',)  
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'asset_name',
                'asset_type',
                'condition',
                'facility',
                'zone',
                'building',
                'subsystem',
                'category',
                'subcategory',
            )
        }),
        ('Identification & Purchase Info', {
            'fields': (
                'asset_tag',
                'serial_number',
                'purchase_date',
                'purchased_amount',
                'lifespan',
                'oem_warranty',
            )
        }),
    )
    
    
admin.site.register(Item)
admin.site.register(Inventory)    
admin.site.register(ItemRequest)
admin.site.register(ItemRequestItem)

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'type',
        'request_from',
        'transfer_to',
        'requested_by',
        'required_date',
        'created_at',
        'updated_at',
    )
    list_filter = ('type', 'request_from', 'transfer_to', 'requested_by', 'required_date', 'created_at')
    filter_horizontal = ('items', 'confirmation_required_from')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': (
                'type',
                'request_from',
                'transfer_to',
                'requested_by',
                'required_date',
                'category',
                'subcategory',
                'items',
                'confirmation_required_from',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(MovementHistory)
class MovementHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id","item_no", "inventory", "user", "model", "movement_date", "from_store", "to_store",
        "transfer_quantity", "transfer_unit_price", "transfer_amount", "description"
    )
    list_filter = ("from_store", "to_store", "user", "movement_date")
    search_fields = ("model", "description")
    readonly_fields = ("transfer_amount", "movement_date", "item_no")

@admin.register(InventoryType)
class InventoryTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "unit_of_measurement")
    search_fields = ("code", "type", "unit_of_measurement")

@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)

@admin.register(ModelReference)
class ModelReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "subcategory", "manufacturer")
    search_fields = ("code", "name")
    list_filter = ("subcategory", "manufacturer")

@admin.register(InventoryReference)
class InventoryReferenceAdmin(admin.ModelAdmin):
    list_display = ("inventory_type", "category", "subcategory", "model_reference", "manufacturer")
    search_fields = ("inventory_type__type", "category__name", "subcategory__name", "model_reference__name", "manufacturer__name")
    list_filter = ("inventory_type", "category", "subcategory", "manufacturer")

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("type", "code", "name", "salvage_value_percent", "useful_life_year")
    search_fields = ("type", "code", "name")

@admin.register(AssetSubCategory)
class AssetSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "asset_category", "is_active")
    search_fields = ("code", "name", "type", "asset_category__name")

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "facility",
        "warehouse",
        "capacity",
        "location",
        "status",
        "owner",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "facility", "warehouse")
    search_fields = ("code", "name", "location")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            'fields': (
                'facility',
                'warehouse',
                'name',
                'code',
                'capacity',
                'location',
                'status',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
