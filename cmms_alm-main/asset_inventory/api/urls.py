from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (WarehouseViewSet, AssetViewSet, 
                    InventoryViewSet, TransferViewSet, ItemViewSet, 
                    MovementHistoryViewSet, InventoryTypeViewSet, 
                    ItemRequestViewSet, DepartmentViewSet,
                    ManufacturerViewSet, ModelReferenceViewSet, InventoryReferenceViewSet, 
                    AssetCategoryViewSet, AssetSubCategoryViewSet, StoreViewSet)

app_name = 'asset_inventory_api'

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'transfers', TransferViewSet, basename='transfer')
router.register(r'items', ItemViewSet, basename='item')
router.register(r'item-request', ItemRequestViewSet, basename='item-request')
router.register(r'movement_history', MovementHistoryViewSet, basename='movement_history')
router.register(r'inventory-types', InventoryTypeViewSet, basename='inventory-type')
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')
router.register(r'model-references', ModelReferenceViewSet, basename='model-reference')
router.register(r'inventory-references', InventoryReferenceViewSet, basename='inventory-reference')
router.register(r'asset-categories', AssetCategoryViewSet, basename='asset-category')
router.register(r'asset-subcategories', AssetSubCategoryViewSet, basename='asset-subcategory')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
]
