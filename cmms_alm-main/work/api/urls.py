# work/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from work.api.views import WorkRequestViewSet, WorkOrderViewSet, PaymentRequisitionViewSet, PaymentItemViewSet, CommentViewSet, PPMViewSet, WorkOrderCompletionViewSet

router = DefaultRouter()
router.register(r'work-requests', WorkRequestViewSet, basename='work-request')
router.register(r'work-orders', WorkOrderViewSet, basename='workorder')
router.register(r'payment-requisitions', PaymentRequisitionViewSet, basename='paymentrequisition')
router.register(r'payment-items', PaymentItemViewSet, basename='paymentitem')
router.register(r'payment-comments', CommentViewSet, basename='paymentcomment')
router.register(r'ppm', PPMViewSet, basename='ppm')
router.register(r'work-order-completions', WorkOrderCompletionViewSet, basename='workordercompletion')

urlpatterns = [
    path('', include(router.urls)),
]
