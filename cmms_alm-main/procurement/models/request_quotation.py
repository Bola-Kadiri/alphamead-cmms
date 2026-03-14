from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from accounts.models import Vendor, User
from facility.models import Facility
from utils.models import FileAttachment, OwnerPrivModel, Dated
from procurement.enum import RFQType


class RequestForQuotation(OwnerPrivModel, Dated, models.Model):
    # Basic Details
    type = models.CharField(
        max_length=100,
        choices=RFQType.choices,
        help_text=_("Type of RFQ.")
    )
    title = models.CharField(
        max_length=255,
        help_text=_("Title of the RFQ.")
    )
    
    requester = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_rfqs',
        help_text=_("User who requested the RFQ.")
    )
    
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rfqs',
        help_text=_("Requester facility.")
    )
    currency = models.CharField(
        max_length=10,
        help_text=_("Currency for the RFQ.")
    )
    terms = models.TextField(
        blank=True,
        null=True,
        help_text=_("Terms and conditions.")
    )
    
    attachment = GenericRelation(
        FileAttachment,
        related_query_name='rfq_attachment',
        help_text=_("RFQ Supporting Document (Optional).")
    )

    # Vendors (Many RFQs can have many vendors)
    vendors = models.ManyToManyField(
        Vendor,
        related_name='rfqs',
        blank=True
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Request for Quotation"
        verbose_name_plural = "Requests for Quotation"
