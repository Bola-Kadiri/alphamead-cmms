import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated


class FacilityInvoice(UserPrivModel, Dated, models.Model):
    """
    Represents an invoice for a facility or location, including payment details, items, and client information.
    """
    STATUS_CHOICES = [
        ('Payment Pending', _('Payment Pending')),
        ('Part Paid', _('Part Paid')),
        ('Paid', _('Paid')),
    ]
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    TYPE_CHOICES = [
        ('Rent', _('Rent')),
        ('Maintenance', _('Maintenance')),
        ('Utility',_('Utility')),
        ('Other', _('Other')),
    ]
    
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        help_text=_("Type of invoice.")
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.CASCADE,
        help_text=_("Facility or location associated with this invoice.")
    )
    
    # apartment = models.ForeignKey(
    #     'Apartment',
    #     on_delete=models.CASCADE,
    #     blank=True, null=True,
    #     help_text="Apartment or room associated with this invoice."
    # )
    
    client = models.CharField(
        max_length=255,
        help_text=_("Client associated with the invoice.")
    )
    
    vat_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("VAT number for the invoice.")
    )
    
    tin_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("TIN number for the invoice.")
    )
    
    purchase_order_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("Purchase order number for this invoice.")
    )
    
    payment_terms = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Payment terms for this invoice.")
    )
    
    bank_account_currency = models.CharField(
        max_length=255,
        help_text=_("Bank account and currency associated with the payment.")
    )
    
    expected_payment_date = models.DateField(
        blank=True, null=True,
        help_text=_("Expected payment date for the invoice.")
    )
    
    template = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Template used for this invoice.")
    )
    
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Payment Pending',
        help_text=_("Status of the invoice payment.")
    )
    
    payment_details = models.TextField(
        blank=True, null=True,
        help_text=_("Details about the payment.")
    )
    
    client_address = models.TextField(
        blank=True, null=True,
        help_text=_("Address of the client.")
    )
    
    def __str__(self):
        return f"Invoice {self.id} - {self.type} ({self.status})"


class InvoiceItem(models.Model):
    """
    Represents individual items in the invoice, such as quantity, price, and description.
    """
    invoice = models.ForeignKey(
        FacilityInvoice,
        on_delete=models.CASCADE,
        related_name='items',
        help_text=_("Invoice this item belongs to.")
    )
    
    quantity = models.PositiveIntegerField(
        help_text=_("Quantity of the item.")
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Price per unit of the item.")
    )
    
    vatable = models.BooleanField(
        default=False,
        help_text=_("Indicates if the item is vatable.")
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Description of the item.")
    )
    
    def __str__(self):
        return f"Item for Invoice {self.invoice.id} - {self.description or 'No Description'}"


class InvoicePayment(models.Model):
    """
    Represents payment details for the invoice, including mode, amount, and remarks.
    """
    WITHHOLDING_TAX_CHOICES = [
        ('N/A', 'N/A'),
        ('5%', '5%'),
        ('10%', '10%'),
    ]
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    invoice = models.ForeignKey(
        FacilityInvoice,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text=_("Invoice this payment belongs to.")
    )
    
    withholding_tax = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("Withholding tax applicable to this payment.")
    )
    
    payment_date = models.DateField(
        blank=True, null=True,
        help_text=_("Date of the payment.")
    )
    
    mode = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("Mode of payment (e.g., Bank transfer, Cash).")
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Amount paid in this transaction.")
    )
    
    bank_account = models.ForeignKey(
        'accounts.BankAccount',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_("Bank account used for this payment.")
    )
    
    remark = models.TextField(
        blank=True, null=True,
        help_text=_("Additional remarks about the payment.")
    )
    
    def __str__(self):
        return f"Payment for Invoice {self.invoice.id} - {self.amount_paid}"
