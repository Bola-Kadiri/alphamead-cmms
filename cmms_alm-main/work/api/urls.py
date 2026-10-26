# work/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from work.api.views import WorkRequestViewSet, WorkOrderViewSet, PaymentRequisitionViewSet, PaymentItemViewSet, CommentViewSet, PPMViewSet, WorkOrderCompletionViewSet, InvoiceViewSet
from work.api.notification_views import NotificationViewSet
from work.api.matrix_views import ApprovalMatrixViewSet, CompanyApproversView
from work.api.delegation_views import DelegationViewSet
from work.api.my_tasks_views import MyTasksView
from work.api.payment_views import PaymentVoucherViewSet, WithholdingTaxRateViewSet

router = DefaultRouter()
router.register(r'work-requests', WorkRequestViewSet, basename='work-request')
router.register(r'work-orders', WorkOrderViewSet, basename='workorder')
router.register(r'payment-requisitions', PaymentRequisitionViewSet, basename='paymentrequisition')
router.register(r'payment-items', PaymentItemViewSet, basename='paymentitem')
router.register(r'payment-comments', CommentViewSet, basename='paymentcomment')
router.register(r'ppm', PPMViewSet, basename='ppm')
router.register(r'work-order-completions', WorkOrderCompletionViewSet, basename='workordercompletion')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'approval-matrix', ApprovalMatrixViewSet, basename='approval-matrix')
router.register(r'delegations', DelegationViewSet, basename='delegation')
router.register(r'payment-vouchers', PaymentVoucherViewSet, basename='payment-voucher')
router.register(r'wht-rates', WithholdingTaxRateViewSet, basename='wht-rate')

urlpatterns = [
    path('company-approvers/', CompanyApproversView.as_view(), name='company-approvers'),
    path('my-tasks/', MyTasksView.as_view(), name='my-tasks'),
    path('', include(router.urls)),
]
