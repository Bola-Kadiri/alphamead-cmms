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
    
    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.CASCADE,
        related_name='spaces_subsystems',
        help_text=_("Building or system to which this space or sub-system belongs.")
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