from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class Apartment(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents an apartment or room within a building.
    """
    OWNERSHIP_CHOICES = [
        ('Freehold', _('Freehold')),
        ('Freehold (Leased Out)', _('Freehold (Leased Out)')),
        ('Leasehold', _('Leasehold')),
    ]

    no = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique number or identifier for the apartment.")
    )
    
    type = models.CharField(
        max_length=100,
        help_text=_("Type of the apartment or room (e.g., 1-bedroom, studio).")
    )
    
    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.CASCADE,
        related_name='apartments',
        help_text=_("Building or flat associated with this apartment.")
    )
    
    no_of_sqm = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Size of the apartment in square meters (SQM).")
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Additional description of the apartment.")
    )
    
    landlord = models.ForeignKey(
        'facility.Landlord',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='apartments',
        help_text=_("Landlord associated with this apartment.")
    )
    
    ownership_type = models.CharField(
        max_length=50,
        choices=OWNERSHIP_CHOICES,
        help_text=_("Ownership type of the apartment.")
    )
    
    service_power_charge_start_date = models.DateField(
        blank=True, null=True,
        help_text=_("Start date for service or power charges.")
    )
    
    address = models.TextField(
        blank=True, null=True,
        help_text=_("Address of the apartment.")
    )
    
    bookable = models.BooleanField(
        default=False,
        help_text=_("Indicates if the apartment is bookable.")
    )
    
    common_area = models.BooleanField(
        default=False,
        help_text=_("Indicates if the apartment is part of a common area.")
    )
    
    available_for_lease = models.BooleanField(
        default=False,
        help_text=_("Indicates if the apartment is available for lease.")
    )
    
    remit_lease_payment = models.BooleanField(
        default=False,
        help_text=_("Whether the apartment requires lease payments to be remitted.")
    )
    
    def __str__(self):
        return f"{self.no} - {self.type} ({self.building})"
