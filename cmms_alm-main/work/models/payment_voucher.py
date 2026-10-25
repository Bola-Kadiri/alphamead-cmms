"""
Stage 5 (Payment) of the five-stage flow: the payment voucher raised against an approved
vendor invoice, and the withholding tax rates Finance owns.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone

from utils.models import Dated, FileAttachment


class WithholdingTaxRate(Dated, models.Model):
    """A withholding tax rate AP can pick on a voucher. Kept by Finance; switched off, never deleted."""

    name = models.CharField(max_length=100, unique=True, help_text="e.g. Contracts and supplies")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percent of the amount before VAT, e.g. 5.00")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['rate', 'name']

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class PaymentVoucher(Dated, models.Model):
    """One voucher per approved five-stage invoice. Its number never changes once given."""

    STATUSES = [
        ('Draft', 'Draft'),
        ('Awaiting Review', 'Awaiting Review'),
        ('Returned', 'Returned'),
        ('Awaiting Approval', 'Awaiting Approval'),
        ('Approved', 'Approved · to pay'),
        ('Payment Failed', 'Payment failed'),
        ('Paid', 'Paid'),
    ]
    METHODS = [
        ('bank_transfer', 'Bank transfer'),
        ('cheque', 'Cheque'),
    ]

    voucher_number = models.CharField(max_length=20, unique=True, editable=False)
    invoice = models.OneToOneField('work.Invoice', on_delete=models.PROTECT, related_name='payment_voucher')
    work_order = models.ForeignKey('work.WorkOrder', on_delete=models.PROTECT, related_name='payment_vouchers')
    facility = models.ForeignKey('facility.Facility', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.PROTECT, related_name='payment_vouchers')
    status = models.CharField(max_length=20, choices=STATUSES, default='Draft')

    # Copied from the approved invoice and locked.
    amount = models.DecimalField(max_digits=18, decimal_places=2, help_text="Invoice amount before VAT.")
    vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    # Chosen by AP.
    wht_rate = models.ForeignKey(WithholdingTaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    wht_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                      help_text="The rate as it was when chosen, so a later rate change does not alter this voucher.")
    wht_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, help_text="Amount + VAT − WHT.")
    payment_method = models.CharField(max_length=20, choices=METHODS, blank=True, default='')

    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    # Paying: confirmed by the Head of Finance & Treasury only.
    payment_date = models.DateField(null=True, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    failure_reason = models.TextField(blank=True, default='')

    attachments = GenericRelation(FileAttachment, related_query_name='payment_voucher_attachments')

    class Meta:
        ordering = ['-id']

    def save(self, *args, **kwargs):
        if not self.voucher_number:
            year = timezone.now().year
            last = (PaymentVoucher.objects.filter(voucher_number__startswith=f'PV-{year}-')
                    .order_by('-voucher_number').values_list('voucher_number', flat=True).first())
            seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
            self.voucher_number = f'PV-{year}-{seq:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.voucher_number
