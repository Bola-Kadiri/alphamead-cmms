from django.db import models
from django.conf import settings  # To reference the User model
from django.utils.translation import gettext_lazy as _

from utils.models import Dated, Status, OwnerPrivModel




class Facility(OwnerPrivModel, Dated, models.Model):
    """
    Represents a specific facility within a cluster.
    """
    cluster = models.ForeignKey(
        'facility.Cluster',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='facility_cluster',
        help_text=_("Cluster to which this facility belongs.")
    )
    
    code = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Code of the facility.")
    )
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the facility.")
    )
    
    address_gps = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("GPS coordinates or detailed address of the facility.")
    )
    
    type = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("Type of the facility (e.g., 'Office', 'Warehouse', 'Retail').")
    )
    
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_facilities',
        help_text=_("Manager responsible for this facility.")
    )
    
    def save(self, *args, **kwargs):
        if not self.code:
            last_code = (
                Facility.objects.exclude(code__isnull=True)
                .exclude(code__exact='')
                .order_by('-code')
                .first()
            )
            if last_code and last_code.code.isdigit():
                next_code = int(last_code.code) + 1
            else:
                next_code = 1
            self.code = str(next_code).zfill(5)  # Pad with leading zeros to 5 digits
        super().save(*args, **kwargs)

    def __str__(self):
        if self.cluster:
            return f"{self.name} ({self.cluster.name})"
        return self.name
