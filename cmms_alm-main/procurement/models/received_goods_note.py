from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from procurement.models import PurchaseOrder
from facility.models import Facility
from accounts.models import User, Vendor
from utils.models import OwnerPrivModel, Dated


class GoodsReceivedNote(OwnerPrivModel, Dated, models.Model):
    # Core Fields
    grn_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text=_("Auto-generated GRN number with format GRN-000000.")
    )
    
    date_of_receipt = models.DateField(
        help_text=_("Date goods were received.")
    )
    
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goods_received_notes',
        help_text=_("Reference to the original Purchase Order.")
    )
    
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grns',
        help_text=_("Vendor who delivered the goods.")
    )
    
    delivery_note_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Vendor's delivery reference number.")
    )
    
    invoice_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Vendor's invoice reference number.")
    )
    
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goods_facility',
        help_text=_("Facility where goods were received.")
    )
    
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_goods',
        help_text=_("User who received the goods (All Requester).")
    )

    def generate_grn_number(self):
        """Generate a unique GRN number with format GRN-000000"""
        if not self.grn_number:
            # Get the maximum existing GRN number
            max_grn = GoodsReceivedNote.objects.aggregate(
                max_num=Max('grn_number')
            )['max_num']
            
            if max_grn and max_grn.startswith('GRN-'):
                try:
                    # Extract the number part after "GRN-"
                    number_part = max_grn.replace('GRN-', '')
                    next_number = int(number_part) + 1
                except (ValueError, TypeError):
                    next_number = 1
            else:
                next_number = 1
            
            # Format as GRN-000000 (6 digits)
            grn_candidate = f"GRN-{next_number:06d}"
            
            # Ensure uniqueness by checking for existing records
            while GoodsReceivedNote.objects.filter(grn_number=grn_candidate).exists():
                next_number += 1
                grn_candidate = f"GRN-{next_number:06d}"
            
            return grn_candidate
        return self.grn_number

    def save(self, *args, **kwargs):
        """Override save method to auto-generate GRN number if not set"""
        if not self.grn_number:
            self.grn_number = self.generate_grn_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.grn_number or f'GRN-{self.id}'}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Goods Received Note"
        verbose_name_plural = "Goods Received Notes"
