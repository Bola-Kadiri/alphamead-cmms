from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class Building(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a building or flat associated with a facility or location.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique code for the building or flat.")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the building or flat.")
    )
    
    zone = models.ForeignKey(
        'facility.Zone',
        on_delete=models.CASCADE,
        blank=True, null=True,
        related_name='buildings',
        help_text=_("Zone associated with the building.")
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.CASCADE,
        related_name='buildings',
        blank=True, null=True,
        help_text=_("facility associated with this building (optional).")
    )

    
    def __str__(self):
        return f"{self.name}"
