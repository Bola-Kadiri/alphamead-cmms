from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from accounts.models import Vendor, User
from utils.models import FileAttachment, OwnerPrivModel, Dated
from procurement.enum import VendorContractType


class VendorContract(OwnerPrivModel, Dated, models.Model):
    """
    Represents a vendor contract with all contract details.
    """
    # Basic Details
    contract_title = models.CharField(
        max_length=255,
        help_text=_("Contract title.")
    )
    
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_contracts',
        help_text=_("Selected vendor for the contract.")
    )
    
    contract_type = models.CharField(
        max_length=50,
        choices=VendorContractType.choices,
        help_text=_("Type of contract.")
    )
    
    # Dates
    start_date = models.DateField(
        help_text=_("Contract start date.")
    )
    
    end_date = models.DateField(
        help_text=_("Contract end date.")
    )
    
    # Financial
    proposed_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Proposed contract value.")
    )
    
    # Reviewer
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_contracts',
        help_text=_("User assigned to review the contract.")
    )
    
    # Agreement Document
    agreement = GenericRelation(
        FileAttachment,
        related_query_name='vendor_contract_agreement',
        help_text=_("Supporting documents/agreement file.")
    )

    def __str__(self):
        return f"{self.contract_title} - {self.vendor.name if self.vendor else 'No Vendor'}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Vendor Contract"
        verbose_name_plural = "Vendor Contracts"

