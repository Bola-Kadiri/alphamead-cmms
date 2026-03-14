from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class Landlord(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a landlord with details such as name, address, phone, and email.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the landlord.")
    )
    
    address = models.TextField(
        blank=True, null=True,
        help_text=_("Address of the landlord.")
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text=_("Phone number of the landlord.")
    )
    
    email = models.EmailField(
        blank=True, null=True,
        help_text=_("Email address of the landlord.")
    )
    
    def __str__(self):
        return self.name
