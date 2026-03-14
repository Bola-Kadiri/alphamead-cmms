from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.models import  Dated, Status, OwnerPrivModel


class Zone(OwnerPrivModel, Dated, models.Model):
    """
    Represents a zone within a facility or a broader geographical area.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique code for the zone.")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the zone.")
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.CASCADE,
        related_name='facility_zones',
        blank=True, null=True,
        help_text=_("facility associated with this zone (optional).")
    )

    def __str__(self):
        return f"{self.name}"