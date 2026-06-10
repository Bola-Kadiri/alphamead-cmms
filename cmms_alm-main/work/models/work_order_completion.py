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
    ]

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name='completions'
    )
    file = models.FileField(upload_to='work_order_completions/', blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)

    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUSES, default='Pending'
    )
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

    ACTIVE_STATUSES = {'Pending', 'Reviewed', 'Approved'}

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
                f"(WCC-{existing.pk}, status: {existing.approval_status}). "
                "Resolve or reject the existing WCC before creating a new one."
            )

    def __str__(self):
        return f"Completion for {self.work_order}"