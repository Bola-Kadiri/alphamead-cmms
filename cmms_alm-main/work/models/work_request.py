import random
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from utils.models import UserPrivModel, Dated, OwnerPrivModel, FileAttachment, Status


class WorkRequest(OwnerPrivModel, Dated, models.Model):

    WORK_TYPES = [
        ("Planned", "Planned"),
        ("Unplanned", "Unplanned"),
    ]

    APPROVAL_STATUSES = [
        ("Pending Review", "Pending Review"),
        ("CP Approved", "CP Approved"),
        ("Reviewed", "Reviewed"),
        ("Fully Approved", "Fully Approved"),
        ("Rejected – Vendor Changed", "Rejected – Vendor Changed"),
        ("Reviewer Rejected", "Reviewer Rejected"),
        ("Approver Rejected", "Approver Rejected"),
    ]

    PRIORITY_LEVELS = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("NGN", "NGN"),
    ]

    type = models.CharField(
        max_length=255, choices=[("Work", _("Work")), ("Procument", _("Procument"))],
        help_text=_("Type of the work request.")
    )

    category = models.ForeignKey(
        'asset_inventory.AssetCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text=_("Category of the work request.")
    )

    work_request_number = models.CharField(
        max_length=15,
        blank=True,
        help_text=_("Unique work request number in REQ-YYYY-NNNNN format.")
    )

    slug = models.SlugField(
        max_length=300,
        unique=True,
        blank=True,
        help_text=_("Auto-generated unique slug for the work request.")
    )

    subcategory = models.ForeignKey(
        'asset_inventory.AssetSubCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text=_("Subcategory of the work request.")
    )

    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="Department associated with the work request."
    )

    require_mobilization_fee = models.BooleanField(
        default=False,
        help_text="Indicates if a Mobilization Fee is required for the request."
    )

    description = models.TextField(
        blank=True, null=True,
        help_text="Brief description of the work request."
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default="Medium",
        help_text="Priority level of the work request."
    )

    attachment = models.FileField(
        upload_to='work_requests/attachments/',
        blank=True, null=True,
        help_text="General file attachment for the work request."
    )

    # Vendor invoice uploaded by the Requester
    vendor_invoice = models.FileField(
        upload_to='work_requests/vendor_invoices/',
        blank=True, null=True,
        help_text="Invoice from the vendor, uploaded by the Requester."
    )

    require_quotation = models.BooleanField(
        default=True
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="User who made the request."
    )

    # Step 1 route selection: Procurement & Store → Reviewer → Approver
    request_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='work_request_to',
        help_text="Procurement & Store handler(s) assigned to audit this request."
    )

    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='work_requests_to_review',
        help_text="Users assigned to review this work request."
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_to_approve',
        help_text="User assigned to give final approval."
    )

    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="Facility associated with the work request."
    )

    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_buildings',
        help_text="Building associated with the work request."
    )

    asset = models.ForeignKey(
        'asset_inventory.Asset',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_assets',
        help_text="Asset associated with the work request."
    )

    # Original vendor from the Requester's invoice
    vendor = models.ForeignKey(
        'accounts.Vendor',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_original_vendor',
        help_text="Original vendor from the Requester's invoice."
    )

    # ── Workflow state fields (managed by action endpoints only) ──────────────

    approval_status = models.CharField(
        max_length=30,
        choices=APPROVAL_STATUSES,
        default="Pending Review",
        help_text="Current workflow status of the work request."
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Locked after submission. Unlocked only when rejected for correction."
    )

    # Step 2 – set by Procurement & Store on approve or reject
    po_number = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="Purchase Order number entered by Procurement & Store."
    )

    po_document = models.FileField(
        upload_to='work_requests/po_documents/',
        blank=True, null=True,
        help_text="PO document uploaded by Procurement & Store."
    )

    po_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True, null=True,
        help_text="PO amount entered by Procurement & Store on approval."
    )

    po_vendor = models.ForeignKey(
        'accounts.Vendor',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_po_vendor',
        help_text="Vendor on the PO (may differ from the original vendor)."
    )

    cp_reason = models.TextField(
        blank=True, null=True,
        help_text="Mandatory reason entered by Procurement & Store when changing vendor."
    )

    # Step 3 – set by Reviewer on reject
    reviewer_reason = models.TextField(
        blank=True, null=True,
        help_text="Mandatory reason provided when Reviewer rejects."
    )

    # Step 4 – set by Approver
    approver_reason = models.TextField(
        blank=True, null=True,
        help_text="Mandatory reason provided when Approver rejects."
    )

    digital_signature = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text="Approver's digital signature on final approval."
    )

    fully_approved_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp when request was fully approved and committed to the ledger."
    )

    # ── General fields ────────────────────────────────────────────────────────

    follow_up_notes = models.TextField(
        blank=True, null=True,
        help_text="Notes for follow-ups related to the work request."
    )

    payment_requisition = models.BooleanField(
        default=False,
        help_text="Indicates if a payment requisition should be created."
    )

    invoice_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="Invoice number associated with the work request."
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text="Currency for the work request."
    )

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True,
        help_text="Cost of the work request."
    )

    add_discount = models.BooleanField(
        default=False,
        help_text="Indicates if a discount should be applied."
    )

    exclude_management_fee = models.BooleanField(
        default=False,
        help_text="Indicates if the management fee should be excluded."
    )

    resources = GenericRelation(
        FileAttachment,
        related_query_name='work_request_resources',
        help_text="Resources attached to the work request."
    )

    files = GenericRelation(
        FileAttachment,
        related_query_name='work_request_files',
        help_text="Files attached to the work request."
    )

    def attach_file(self, file_instance):
        file_instance.content_object = self
        file_instance.save()

    def get_attached_files(self):
        return self.files.all()

    def prepopulate_slug(self):
        base_slug = slugify(self.type)
        unique_slug = base_slug
        num = 1
        while WorkRequest.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{num}"
            num += 1
        return unique_slug

    def generate_unique_work_request_number(self):
        from django.db import connection
        from django.utils import timezone
        year = timezone.now().year
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('work_request_number_seq')")
            seq = cursor.fetchone()[0]
        return f"REQ-{year}-{str(seq).zfill(5)}"

    def generate_po_number(self):
        from django.utils import timezone
        year = timezone.now().year
        while True:
            suffix = str(random.randint(1000000, 9999999))
            po = f"PO-{year}-{suffix}"
            if not WorkRequest.objects.filter(po_number=po).exists():
                return po

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.prepopulate_slug()
        if not self.work_request_number:
            self.work_request_number = self.generate_unique_work_request_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Work Request: {self.type} - {self.requester}"
