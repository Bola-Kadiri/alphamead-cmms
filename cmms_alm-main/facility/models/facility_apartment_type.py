from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class FacilityApartmentType(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a type of apartment in a facility with a name and status.
    """
    STATUS_CHOICES = [
        ('Active', _('Active')),
        ('Inactive', _('Inactive')),
    ]
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the apartment type.")
    )
    
    def __str__(self):
        return self.name
