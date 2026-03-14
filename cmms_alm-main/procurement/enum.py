from django.db import models
from django.utils.translation import gettext_lazy as _


class RFQType(models.TextChoices):
    """Type choices for Request for Quotation"""
    IFM_SERVICES = 'IFM Services', _('IFM Services')
    SUPPLY = 'Supply', _('Supply')
    GENERAL_SERVICES = 'General Services', _('General Services')
    OTHER_SERVICES = 'Other Services', _('Other Services')


class PurchaseOrderStatus(models.TextChoices):
    """Status choices for Purchase Order"""
    DRAFT = "Draft", _("Draft")
    PENDING = "Pending", _("Pending")
    SENT = "Sent", _("Sent")
    DELIVERED = "Delivered", _("Delivered")
    CANCELLED = "Cancelled", _("Cancelled")


class VendorContractType(models.TextChoices):
    """Contract type choices for Vendor Contract"""
    SERVICE = 'Service', _('Service')
    PURCHASE = 'Purchase', _('Purchase')
    LEASE = 'Lease', _('Lease')
    NDA = 'NDA', _('NDA')

