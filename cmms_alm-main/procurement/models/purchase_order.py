from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from accounts.models import Vendor, User, Department
from facility.models import Facility
from utils.models import FileAttachment, OwnerPrivModel, Dated
from procurement.enum import PurchaseOrderStatus


class PurchaseOrder(OwnerPrivModel, Dated, models.Model):
    # Basic Details
    type = models.CharField(max_length=100)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders_requested')
    requested_date = models.DateField()

    # Vendor & Shipment
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    ship_to = models.TextField(blank=True, null=True)

    # Other
    terms_and_conditions = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)

    # Attachments
    attachment = GenericRelation(FileAttachment, related_query_name='purchase_order_attachment')

    def __str__(self):
        return f"PO-{self.id} ({self.type})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    description = models.TextField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit = models.CharField(max_length=50)
    specification = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.description} ({self.quantity} {self.unit})"


class PurchaseOrderComment(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user} on PO-{self.purchase_order.id}"


class PurchaseOrderApproval(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    decision_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{'Approved' if self.approved else 'Rejected'} by {self.approver}"
