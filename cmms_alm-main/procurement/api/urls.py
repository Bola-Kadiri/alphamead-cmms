from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RequestForQuotationViewSet,
    PurchaseOrderViewSet,
    GoodsReceivedNoteViewSet,
    PurchaseOrderRequisitionViewSet,
    VendorContractViewSet
)

router = DefaultRouter()
router.register(r'request-quotation', RequestForQuotationViewSet, basename='rfq')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'goods-received-note', GoodsReceivedNoteViewSet, basename='goods-received-note')
router.register(r'po-requisitions', PurchaseOrderRequisitionViewSet, basename='po-requisition')
router.register(r'vendor-contracts', VendorContractViewSet, basename='vendor-contract')

urlpatterns = [
    path('', include(router.urls)),
]
