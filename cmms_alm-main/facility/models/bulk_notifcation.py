from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.models import UserPrivModel, Dated


class BulkNotification(UserPrivModel, Dated, models.Model):
    """
    Represents a bulk notification sent to multiple users or apartments.
    """
    title = models.CharField(
        max_length=255,
        help_text=_("Title of the notification message.")
    )
    
    facility_locations = models.ManyToManyField(
        'facility.Facility',
        blank=True,
        related_name='bulk_notifications',
        help_text=_("Facilities or locations associated with the notification.")
    )
    
    apartments = models.ManyToManyField(
        'facility.Apartment',
        blank=True,
        related_name='bulk_notifications',
        help_text=_("Apartments or rooms associated with the notification.")
    )
    
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='bulk_notifications',
        help_text=_("Users to whom the notification is sent.")
    )
    
    send_to_all_users = models.BooleanField(
        default=False,
        help_text=_("Whether to send the notification to all users.")
    )
    
    send_to_all_apartments = models.BooleanField(
        default=False,
        help_text=_("Whether to send the notification to all apartments.")
    )
    
    message = models.TextField(
        help_text=_("Content of the notification message.")
    )
    
    send_as_email = models.BooleanField(
        default=False,
        help_text=_("Whether to send the notification as an email.")
    )
    
    send_as_sms = models.BooleanField(
        default=False,
        help_text=_("Whether to send the notification as an SMS.")
    )
    
    def __str__(self):
        return self.title
