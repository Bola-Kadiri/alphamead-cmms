import random
import string

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericRelation

from utils.models import UserPrivModel, Dated, Status, FileAttachment, OwnerPrivModel


class PaymentItem(models.Model):
    """
    Represents individual items linked to payments.
    """
    
    item_name = models.CharField(
        max_length=255
    )
    
    work_order = models.ForeignKey(
        "work.WorkOrder",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="payment_items",
        help_text="Work order linked to the item.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount associated with the item.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the item.",
    )

    def __str__(self):
        return str(self.item_name)



class PaymentRequisition(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a payment requisition entity linked to work orders, users, comments, approvals, and file attachments.
    """
    
    APPROVAL_STATUS_CHOICES = [
        ("request", "Request Approval"),
        ("approve", "Approve"),
    ]

    requisition_date = models.DateField(
        help_text="Date of the payment record."
    )

    pay_to = models.ForeignKey(
        'accounts.Vendor',
        on_delete=models.CASCADE,
        related_name="payments_user",
        help_text="User or entity to whom the payment is made."
    )
    
    requisition_number = models.CharField(
        max_length=255,
        blank=True, null=True
    )
    
    expected_payment_date = models.DateField(
        blank=True,
        null=True,
        help_text="Expected payment date."
    )

    retirement = models.BooleanField(
        default=False,
        help_text="Indicates if the payment is for retirement purposes."
    )

    remark = models.TextField(
        blank=True,
        null=True,
        help_text="Additional remarks for the payment."
    )

    work_orders = models.ManyToManyField(
        "work.WorkOrder",
        blank=True,
        related_name="linked_payments",
        help_text="Work orders linked to the payment."
    )

    request_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="payment_requests",
        help_text="Users to whom the payment approval requests are sent."
    )

    items = models.ManyToManyField(
        PaymentItem,
        blank=True,
        related_name="payment_items",
        help_text="Items linked to this payment requisition."
    )

    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default="request",
        help_text="Approval status for the payment."
    )

    comment = models.TextField(
        blank=True,
        null=True,
        help_text="User comments regarding the payment."
    )

    attachment = GenericRelation(
        FileAttachment,
        related_query_name='work_order_attachment',
        help_text="Resources attached to the work request."
    )

    withholding_tax = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Selected withholding tax option."
    )

    expected_payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Expected payment amount for this requisition."
    )
    
    
    @property
    def total_item_cost(self):
        total_cost = 0
        if self.items:
            for item in self.items:
                total_cost += item.amount
        return total_cost
    
    

    
    def generate_unique_requisition_number(self):
        """Generate a unique 7-digit work request number."""
        while True:
            number = str(random.randint(1000000, 9999999))  # Generate 7-digit number
            if not PaymentRequisition.objects.filter(requisition_number=number).exists():
                return number

    def save(self, *args, **kwargs):
        """Override save method to generate slug if not set"""
            
        if not self.requisition_number:
            self.requisition_number = self.generate_unique_requisition_number()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment to {self.pay_to} on {self.requisition_date} - Status: {self.status}"
























class Comment(models.Model):
    """
    Represents comments linked to payments.
    """
    payment = models.ForeignKey(
        PaymentRequisition,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="Payment associated with the comment.",
    )
    send_notification = models.BooleanField(
        default=False,
        help_text="Indicates whether to send a notification for this comment.",
    )
    message = models.TextField(
        help_text="Comment message.",
    )
    internal_only = models.BooleanField(
        default=True,
        help_text="Indicates whether the comment is for internal use only.",
    )
    attachment = models.FileField(
        upload_to="comments/",
        blank=True,
        null=True,
        help_text="File attachment for the comment.",
    )

    def __str__(self):
        return f"Comment on Payment {self.payment.id}"


