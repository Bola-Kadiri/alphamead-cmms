from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from utils.models import  Dated, Status, OwnerPrivModel



class Region(OwnerPrivModel, Dated, models.Model):
    """
    Represents a geographical region.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the region.")
    )
    
    country = models.CharField(
        max_length=100,
        help_text=_("Country where the region is located.")
    )
    
    select_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_regions',
        help_text=_("Manager responsible for this region.")
    )

    def __str__(self):
        return self.name