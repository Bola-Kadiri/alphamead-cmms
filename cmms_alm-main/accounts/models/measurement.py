from django.db import models
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel
from django.utils.translation import gettext_lazy as _

class UnitOfMeasurement(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a unit of measurement with details like code, description, symbol, type, and status.
    """
    
    TYPE_CHOICES = [
        ('Area', _('Area')),
        ('Packing', _('Packing')),
        ('Piece', _('Piece')),
        ('Time', _('Time')),
        ('Volume', _('Volume')),
        ('Weight', _('Weight')),
        ('Other', _('Other'))
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique code for the unit of measurement.")
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Description of the unit of measurement.")
    )
    
    symbol = models.CharField(
        max_length=10,
        blank=True, null=True,
        help_text=_("Symbol representing the unit of measurement.")
    )
    
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        help_text=_("Type of the unit of measurement.")
    )
    
    class Meta:
        ordering = ['-id']
    
    def __str__(self):
        return f"{self.code} ({self.symbol})"
