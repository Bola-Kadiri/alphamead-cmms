from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import OwnerPrivModel, Dated
from facility.models import Facility


class Warehouse(OwnerPrivModel, Dated, models.Model):
    """
    Represents a warehouse with key properties.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique code for the warehouse.")
    )

    name = models.CharField(
        max_length=100,
        help_text=_("Name of the warehouse.")
    )

    capacity = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Storage capacity of the warehouse.")
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouses',
        help_text=_("Associated facility for the warehouse.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether the warehouse is currently active.")
    )

    description = models.TextField(
        blank=True, null=True,
        help_text=_("Detailed description of the warehouse.")
    )

    address = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Physical address of the warehouse.")
    )

    def __str__(self):
        return self.name
