"""
Time stamp on every action in the five-stage flow: who did what, to which
document, when, and how long it took since the previous action on that document.

Append-only. A row can be added but never changed or deleted — not through the
model, the queryset, or the admin — so the trail and the speed report can be trusted.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

STAGE_CHOICES = [
    ('work_request', 'Work Request'),
    ('work_order', 'Work Order'),
    ('wcc', 'Completion (WCC)'),
    ('vendor_invoice', 'Vendor Invoice'),
    ('payment', 'Payment'),
]

ACTION_CHOICES = [
    ('raised', 'Raised'),
    ('claimed', 'Claimed'),
    ('assigned', 'Assigned'),
    ('reviewed', 'Reviewed'),
    ('approved', 'Approved'),
    ('sent_back', 'Sent back'),
    ('resubmitted', 'Resubmitted'),
    ('rejected', 'Rejected'),
    ('accepted', 'Accepted'),
    ('paid', 'Paid'),
    ('payment_failed', 'Payment failed'),
    # Raise Payment (see raise_payment_trail).
    ('procured', 'PO & quotation added'),
    ('final_approved', 'Final approval'),
]


class ActionLogError(Exception):
    pass


class FlowActionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ActionLogError("The action log cannot be changed.")

    def delete(self):
        raise ActionLogError("The action log cannot be deleted.")


class FlowAction(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    document = GenericForeignKey('content_type', 'object_id')

    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    facility = models.ForeignKey('facility.Facility', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')

    # Who acted. Name and role are copied so the trail reads the same after a rename or role change.
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    actor_name = models.CharField(max_length=255)
    actor_role = models.CharField(max_length=50)
    # Set when a stand-in acts for someone away (delegation).
    on_behalf_of = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='+')
    on_behalf_of_name = models.CharField(max_length=255, blank=True)

    reason = models.TextField(blank=True)
    signature = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField(default=timezone.now, db_index=True)
    since_previous = models.DurationField(null=True, blank=True,
                                          help_text="Time since the previous action on the same document.")

    objects = FlowActionQuerySet.as_manager()

    class Meta:
        ordering = ['at', 'id']
        indexes = [models.Index(fields=['content_type', 'object_id', 'at'])]
        verbose_name = "Action time stamp"
        verbose_name_plural = "Action time stamps"

    def __str__(self):
        return f"{self.get_stage_display()} · {self.get_action_display()} by {self.actor_name} at {self.at:%d %b %Y %H:%M}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ActionLogError("The action log cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ActionLogError("The action log cannot be deleted.")


def _name(user):
    return (user.name.strip() or user.email) if user else ''


def record_action(document, stage, action, actor, *, reason='', signature='', on_behalf_of=None, facility=None):
    """Stamp an action on `document`. Call it in the same transaction as the change it records."""
    content_type = ContentType.objects.get_for_model(document)
    now = timezone.now()
    previous = (FlowAction.objects.filter(content_type=content_type, object_id=document.pk)
                .order_by('-at', '-id').values_list('at', flat=True).first())
    if facility is None:
        facility = getattr(document, 'facility', None)
    return FlowAction.objects.create(
        content_type=content_type, object_id=document.pk, stage=stage, action=action,
        facility=facility, actor=actor, actor_name=_name(actor), actor_role=getattr(actor, 'roles', ''),
        on_behalf_of=on_behalf_of, on_behalf_of_name=_name(on_behalf_of),
        reason=reason, signature=signature, at=now,
        since_previous=(now - previous) if previous else None,
    )


def history(document):
    """Every action on `document`, oldest first."""
    content_type = ContentType.objects.get_for_model(document)
    return FlowAction.objects.filter(content_type=content_type, object_id=document.pk)
