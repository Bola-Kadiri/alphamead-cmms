from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from utils.models import  Dated, Status, OwnerPrivModel



class Subsystem(OwnerPrivModel, Dated, models.Model):
    """
    Represents a specific space or a sub-system within a building or system.
    Note: Renamed from 'Space/Sub-System' to avoid '/' in class name.
    """
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the space or sub-system.")
    )

    zone = models.ForeignKey(
        'facility.Zone',
        on_delete=models.SET_NULL,
        related_name='subsystems',
        blank=True, null=True,
        help_text=_("Zone this space/sub-system belongs to (optional).")
    )

    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.SET_NULL,
        related_name='spaces_subsystems',
        blank=True, null=True,
        help_text=_("Building to which this space or sub-system belongs (optional — some sites track spaces directly under a zone with no building).")
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.CASCADE,
        related_name='zones',
        blank=True, null=True,
        help_text=_("facility associated with this space/sub-system (optional).")
    )


    def __str__(self):
        return f"{self.name}"