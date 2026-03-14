from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.models import  Dated, Status, OwnerPrivModel


class Cluster(OwnerPrivModel, Dated, models.Model):
    """
    Represents a cluster of facilities within a region.
    """
    region = models.ForeignKey(
        'facility.Region',
        on_delete=models.CASCADE,
        related_name='clusters',
        help_text=_("Region to which this cluster belongs.")
    )
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the cluster.")
    )
    
    select_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_clusters',
        help_text=_("Manager responsible for this cluster.")
    )

    def __str__(self):
        return f"{self.name} ({self.region.name})"