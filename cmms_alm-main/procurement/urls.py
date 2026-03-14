from django.urls import path, include
from procurement import views

app_name = "procurement"

urlpatterns = [
     path('api/', include('procurement.api.urls')),
    path("request_quotation/", views.request_quotation, name="request_quotation"),
    path("purchase_order/", views.purchase_order, name="purchase_order"),
    path("goods_received/", views.goods_received, name="goods_received"),
    path("payment_requisition/", views.payment_requisition, name="payment_requisition"),
    # path("movement_history/", views.movement_history, name="movement_history"),
    path("saving_loss_report/", views.saving_loss_report, name="saving_loss_report"),

]