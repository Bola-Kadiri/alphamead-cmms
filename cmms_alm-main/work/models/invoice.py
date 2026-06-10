from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from utils.models import OwnerPrivModel, Dated, FileAttachment


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(
        'Invoice', on_delete=models.CASCADE, related_name='items'
    )
    item_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return f"{self.item_name} — {self.amount}"


class Invoice(OwnerPrivModel, Dated, models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'USD'), ('NGN', 'NGN'), ('EUR', 'EUR'), ('GBP', 'GBP'),
    ]
    APPROVAL_STATUSES = [
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Approved', 'Approved'),
        ('Reviewer Rejected', 'Reviewer Rejected'),
        ('Approver Rejected', 'Approver Rejected'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)

    facility = models.ForeignKey(
        'facility.Facility', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices',
    )
    work_order = models.ForeignKey(
        'work.WorkOrder', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices',
    )
    work_completion = models.ForeignKey(
        'work.WorkOrderCompletion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices',
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices_raised',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices_to_approve',
    )
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='invoices_to_review',
    )

    invoice_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=30, default='Draft')
    tracker_status = models.CharField(max_length=30, default='Pending')
    sent_date = models.DateField(blank=True, null=True)
    opened_date = models.DateField(blank=True, null=True)
    pdf_file = models.FileField(upload_to='invoices/pdfs/', blank=True, null=True)

    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUSES, default='Pending'
    )
    is_reviewed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    reviewer_notes = models.TextField(blank=True, null=True)
    approver_notes = models.TextField(blank=True, null=True)

    attachments = GenericRelation(
        FileAttachment, related_query_name='invoice_attachments',
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.work_completion_id:
            raise ValidationError(
                "An invoice must be linked to a Work Completion Certificate."
            )
        if self.work_completion and self.work_completion.approval_status != 'Approved':
            raise ValidationError(
                "Invoice can only be raised against an Approved Work Completion Certificate. "
                f"Current WCC status: {self.work_completion.approval_status}."
            )

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from django.utils import timezone
            year = timezone.now().year
            last = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{year}-'
            ).order_by('-invoice_number').first()
            if last:
                try:
                    seq = int(last.invoice_number.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.invoice_number = f'INV-{year}-{seq:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number
