"""
Time limit for each stage of the five-stage flow, with a reminder point.

A setting, not code: the Super Admin keeps a company default per stage and may
override it for a client whose contract sets different response times. Until a
row exists the defaults below apply. Calendar hours (weekends included) for now.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from work.models.action_log import STAGE_CHOICES

DEFAULT_HOURS = {
    'work_request': 24,
    'work_order': 48,
    'wcc': 72,
    'vendor_invoice': 48,
    'payment': 72,
}
DEFAULT_REMINDER_PERCENT = 75


class StageTimeLimit(models.Model):
    client = models.ForeignKey('accounts.Client', null=True, blank=True, on_delete=models.CASCADE,
                               related_name='stage_time_limits',
                               help_text="Leave empty for the company default; set it to override for one client.")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    hours = models.PositiveIntegerField(help_text="Calendar hours allowed for the stage.")
    reminder_percent = models.PositiveSmallIntegerField(default=DEFAULT_REMINDER_PERCENT,
                                                        help_text="Remind the person holding the step at this % of the time.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['client__name', 'stage']
        constraints = [
            models.UniqueConstraint(fields=['stage'], condition=models.Q(client__isnull=True),
                                    name='one_company_default_per_stage'),
            models.UniqueConstraint(fields=['client', 'stage'], condition=models.Q(client__isnull=False),
                                    name='one_override_per_client_and_stage'),
            models.CheckConstraint(condition=models.Q(hours__gt=0), name='time_limit_hours_positive'),
            models.CheckConstraint(condition=models.Q(reminder_percent__gt=0, reminder_percent__lt=100),
                                   name='reminder_percent_between_1_and_99'),
        ]
        verbose_name = "Stage time limit"
        verbose_name_plural = "Stage time limits"

    def __str__(self):
        who = self.client.name if self.client_id else 'Company default'
        return f"{who} · {self.get_stage_display()} · {self.hours} h (remind at {self.reminder_percent}%)"


def time_limit_for(stage, client=None):
    """(hours, reminder_percent) for `stage`: the client's override, else the company default, else the built-in."""
    rows = StageTimeLimit.objects.filter(stage=stage)
    row = (client is not None and rows.filter(client=client).first()) or rows.filter(client__isnull=True).first()
    if row:
        return row.hours, row.reminder_percent
    return DEFAULT_HOURS[stage], DEFAULT_REMINDER_PERCENT


def step_timing(stage, started_at, client=None, now=None):
    """When a step is due, when to remind, and whether it is on time, due for a reminder, or late."""
    now = now or timezone.now()
    hours, percent = time_limit_for(stage, client)
    due_at = started_at + timedelta(hours=hours)
    remind_at = started_at + timedelta(hours=hours * percent / 100)
    state = 'late' if now >= due_at else 'reminder' if now >= remind_at else 'on_time'
    return {'state': state, 'due_at': due_at, 'remind_at': remind_at, 'hours': hours}
