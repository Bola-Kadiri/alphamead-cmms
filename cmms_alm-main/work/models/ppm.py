import random
from django.db import models
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class PPM(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a Planned Preventive Maintenance (PPM) schedule.
    """

    FREQUENCY_UNIT_CHOICES = [
        ('Hours', 'Hour(s)'),
        ('Days', 'Day(s)'),
        ('Weeks', 'Week(s)'),
        ('Months', 'Month(s)'),
    ]

    description = models.TextField(
        help_text="Describe this maintenance task."
    )

    category = models.ForeignKey(
        'accounts.Category',
        on_delete=models.CASCADE,
        help_text="Category of the maintenance task."
    )

    subcategory = models.ForeignKey(
        'accounts.Subcategory',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Subcategory of the maintenance task."
    )

    frequency = models.IntegerField(
        help_text="Frequency of maintenance (e.g., in days)."
    )

    frequency_unit = models.CharField(
        max_length=10,
        choices=FREQUENCY_UNIT_CHOICES,
        help_text="Frequency unit (e.g., hours, days)."
    )

    notify_before_due = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of days/hours before notifying the responsible team."
    )

    notify_unit = models.CharField(
        max_length=10,
        choices=FREQUENCY_UNIT_CHOICES,
        help_text="Unit of notification (e.g., hours, days)."
    )

    send_reminder_every = models.IntegerField(
        blank=True,
        null=True,
        help_text="Frequency of reminders before the due date (e.g., in days)."
    )

    reminder_unit = models.CharField(
        max_length=10,
        choices=FREQUENCY_UNIT_CHOICES,
        help_text="Unit for reminders."
    )

    currency = models.CharField(
        max_length=3,
        choices=[
            ('NGN', 'Nigerian Naira'),
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
        ],
        default='NGN',
        help_text="Currency for associated costs."
    )

    auto_create_work_order = models.BooleanField(
        default=False,
        help_text="Automatically create a work order for this PPM."
    )

    create_work_order_as_approved = models.BooleanField(
        default=False,
        help_text="Automatically approve the created work order."
    )

    assets = models.ManyToManyField(
        'asset_inventory.Asset',
        blank=True,
        related_name='ppms',
        help_text="Assets involved in the maintenance."
    )

    facilities = models.ManyToManyField(
        'facility.Facility',
        blank=True,
        related_name='ppms',
        help_text="Facilities associated with the maintenance."
    )

    apartments = models.ManyToManyField(
        'facility.Apartment',
        blank=True,
        related_name='ppms',
        help_text="Apartments or rooms associated with the maintenance."
    )

    items = models.ManyToManyField(
        'work.PaymentItem',
        blank=True,
        related_name='ppms',
        help_text="Items required for this maintenance task."
    )

    activities_safety_tips = models.TextField(
        blank=True,
        null=True,
        help_text="Activities or safety tips related to the maintenance task."
    )

    class Meta:
        verbose_name = "PPM"
        verbose_name_plural = "PPM)"

    def __str__(self):
        return f"PPM: {self.description[:50]} ({self.id})"
