from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.models import OwnerPrivModel, Status, Dated
from facility.models import Facility

class Store(OwnerPrivModel, Status, Dated, models.Model):
    """
    Represents a store with details such as name, code, location, and status.
    """
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stores',
        help_text=_("Associated facility for the store.")
    )
    
    warehouse = models.ForeignKey(
        'asset_inventory.Warehouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stores',
        help_text=_("Associated warehouse for the store.")
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique code for the store.")
    )
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the store.")
    )
    
    capacity = models.PositiveIntegerField(
        blank=True, null=True,
        help_text=_("Storage capacity of the store.")
    )
    
    location = models.TextField(
        blank=True, null=True,
        help_text=_("Physical location or address of the store.")
    )
    
    def save(self, *args, **kwargs):
        if not self.code:
            last_code = (
                Store.objects.exclude(code__isnull=True)
                .exclude(code__exact='')
                .order_by('-code')
                .first()
            )
            if last_code and last_code.code.isdigit():
                next_code = int(last_code.code) + 1
            else:
                next_code = 1
            self.code = str(next_code).zfill(5)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)