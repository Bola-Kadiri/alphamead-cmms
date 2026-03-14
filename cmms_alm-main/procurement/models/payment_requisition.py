from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from accounts.models import Vendor
from utils.models import FileAttachment, OwnerPrivModel, Dated


class PurchaseOrderRequisition(OwnerPrivModel, Dated, models.Model):
    # Basic Details
    title = models.CharField(
        max_length=255,
        help_text=_("Title of the purchase requisition.")
    )
    
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_requisitions',
        help_text=_("Vendor for the requisition.")
    )
    
    invoice_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text=_("Auto-generated invoice number with format INV-000000.")
    )
    
    sage_reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("SAGE reference number (optional).")
    )
    
    description = models.TextField(
        help_text=_("Description of the purchase requisition.")
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Total amount of the requisition.")
    )
    
    expected_delivery_date = models.DateField(
        help_text=_("Expected delivery date.")
    )

    attachment = GenericRelation(FileAttachment, related_query_name='po_requisition_attachment')

    def generate_invoice_number(self):
        """Generate a unique invoice number with format INV-000000"""
        if not self.invoice_number:
            # Get the maximum existing invoice number
            max_invoice = PurchaseOrderRequisition.objects.aggregate(
                max_num=Max('invoice_number')
            )['max_num']
            
            if max_invoice and max_invoice.startswith('INV-'):
                try:
                    # Extract the number part after "INV-"
                    number_part = max_invoice.replace('INV-', '')
                    next_number = int(number_part) + 1
                except (ValueError, TypeError):
                    next_number = 1
            else:
                next_number = 1
            
            # Format as INV-000000 (6 digits)
            invoice_candidate = f"INV-{next_number:06d}"
            
            # Ensure uniqueness by checking for existing records
            while PurchaseOrderRequisition.objects.filter(invoice_number=invoice_candidate).exists():
                next_number += 1
                invoice_candidate = f"INV-{next_number:06d}"
            
            return invoice_candidate
        return self.invoice_number

    def save(self, *args, **kwargs):
        """Override save method to auto-generate invoice number if not set"""
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PO Requisition - {self.invoice_number or 'No Invoice'}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Purchase Order Requisition"
        verbose_name_plural = "Purchase Order Requisitions"
