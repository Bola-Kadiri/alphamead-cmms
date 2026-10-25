import random

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from work.models.work_order import WorkOrder
from utils.models import OwnerPrivModel, Dated, FileAttachment


class WorkOrderCompletion(OwnerPrivModel, Dated, models.Model):

    APPROVAL_STATUSES = [
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Approved', 'Approved'),
        ('Reviewer Rejected', 'Reviewer Rejected'),
        ('Approver Rejected', 'Approver Rejected'),
        # Five-stage flow (Stage 3): Site Managers raise with evidence → Central Ops verify → Category Manager approves.
        ('Draft', 'Draft'),
        ('Awaiting Verification', 'Awaiting Verification'),
        ('Sent Back', 'Sent Back'),
        ('Awaiting Approval', 'Awaiting Approval'),
    ]

    LEGACY = 'legacy'
    FIVE_STAGE = 'five_stage'
    FLOW_CHOICES = [
        (LEGACY, "Original flow"),
        (FIVE_STAGE, "Five-stage flow"),
    ]

    wcc_number = models.CharField(
        max_length=7,
        blank=True,
        help_text="Unique 7-digit WCC number, auto-generated on submission.",
    )

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name='completions'
    )
    file = models.FileField(upload_to='work_order_completions/', blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)

    approval_status = models.CharField(
        max_length=30, choices=APPROVAL_STATUSES, default='Pending'
    )

    # ── Five-stage flow (Stage 3) ────────────────────────────────────────────
    flow = models.CharField(max_length=20, choices=FLOW_CHOICES, default=LEGACY,
                            help_text="Which approval flow this certificate follows; set when created and never changed.")
    started_at = models.DateTimeField(blank=True, null=True, help_text="When the work started on site.")
    finished_at = models.DateTimeField(blank=True, null=True, help_text="When the work finished on site.")
    technician = models.CharField(max_length=255, blank=True, default='', help_text="Vendor's person who did the work.")
    vendor_rating = models.PositiveSmallIntegerField(blank=True, null=True, help_text="Site Manager's rating of the vendor, 1 to 5.")
    completion_notes = models.TextField(blank=True, default='')
    site_visit_date = models.DateField(blank=True, null=True, help_text="When Central Operations checked the work on site.")
    is_reviewed = models.BooleanField(default=False)

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='completions_to_approve',
    )
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='completions_to_review',
    )

    reviewer_notes = models.TextField(blank=True, null=True)
    approver_notes = models.TextField(blank=True, null=True)

    resources = GenericRelation(
        FileAttachment,
        related_query_name='completion_resources',
    )

    ACTIVE_STATUSES = {'Pending', 'Reviewed', 'Approved', 'Draft', 'Awaiting Verification', 'Sent Back', 'Awaiting Approval'}

    def clean(self):
        from django.core.exceptions import ValidationError
        qs = WorkOrderCompletion.objects.filter(
            work_order=self.work_order,
            approval_status__in=self.ACTIVE_STATUSES,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            existing = qs.first()
            raise ValidationError(
                f"A Work Completion Certificate already exists for this Work Order "
                f"(WCC-{existing.wcc_number or existing.pk}, status: {existing.approval_status}). "
                "Resolve or reject the existing WCC before creating a new one."
            )

    def generate_unique_wcc_number(self):
        """Generate a unique 7-digit WCC number — same scheme as WorkOrder's own number."""
        while True:
            number = str(random.randint(1000000, 9999999))
            if not WorkOrderCompletion.objects.filter(wcc_number=number).exists():
                return number

    def save(self, *args, **kwargs):
        if not self.wcc_number:
            self.wcc_number = self.generate_unique_wcc_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Completion for {self.work_order}"


class WccEvidence(models.Model):
    """One piece of required evidence on a five-stage WCC. One of each kind; a new upload replaces the old."""

    BEFORE_PHOTO = 'before_photo'
    AFTER_PHOTO = 'after_photo'
    SIGNED_CHECKLIST = 'signed_checklist'
    KIND_CHOICES = [
        (BEFORE_PHOTO, 'Before photo'),
        (AFTER_PHOTO, 'After photo'),
        (SIGNED_CHECKLIST, 'Signed inspection checklist'),
    ]

    completion = models.ForeignKey(WorkOrderCompletion, on_delete=models.CASCADE, related_name='evidence')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    file = models.FileField(upload_to='wcc_evidence/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kind']
        constraints = [models.UniqueConstraint(fields=['completion', 'kind'], name='one_evidence_per_kind')]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.completion}"
