from django.db import models
from django.conf import settings
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from utils.models import Dated, OwnerPrivModel, ImageAttachment
from accounts.models import Vendor, Department
from facility.models import Facility, Apartment


class InventoryRequest(Dated, OwnerPrivModel, models.Model):
    REQUEST_TYPE_CHOICES = [
        ('vendor', _('Request from Vendor')),
        ('store', _('Request from Store')),
    ]
    
    
    """Main model for inventory requests"""
    # Relations from the form
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=10, editable=False)
    store = models.ForeignKey('asset_inventory.Store', on_delete=models.SET_NULL, null=True, blank=True)
    required_date = models.DateField()
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    items = models.ManyToManyField('asset_inventory.Item')
    
    attachment = models.ManyToManyField(ImageAttachment, blank=True, related_name='personnel_documents')
    
    def save(self, *args, **kwargs):
        # Only generate an invoice number for new records without one
        if not self.pk and not self.invoice_number:
            # Get the current maximum invoice_number (as a string)
            max_invoice = InventoryRequest.objects.aggregate(max_num=Max('invoice_number'))['max_num']
            if max_invoice:
                try:
                    next_number = int(max_invoice) + 1
                except (ValueError, TypeError):
                    next_number = 1
            else:
                next_number = 1

            invoice_candidate = f"{next_number:05d}"
            # Ensure uniqueness by checking for existing records
            while InventoryRequest.objects.filter(invoice_number=invoice_candidate).exists():
                next_number += 1
                invoice_candidate = f"{next_number:05d}"
            self.invoice_number = invoice_candidate

        super().save(*args, **kwargs)


    def __str__(self):
        return f"Request #{self.id} - {self.requested_by.get_full_name()}"
    
    
