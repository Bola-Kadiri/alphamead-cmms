from django.db import models
from utils.models import OwnerPrivModel, Dated
from django.utils.translation import gettext_lazy as _

class AssetCategory(OwnerPrivModel, Dated, models.Model):
    """
    Represents a category for assets.
    """
    type = models.CharField(
        max_length=50,
        help_text=_('Type of the asset category.')
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique code for the asset category.')
    )
    name = models.CharField(
        max_length=100,
        help_text=_('Name of the asset category.')
    )
    salvage_value_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        blank=True, null=True,
        help_text=_('Salvage Value Percentage.')
    )
    useful_life_year = models.IntegerField(
        blank=True, null=True,
        help_text=_('Useful Life (years).')
    )
    description = models.TextField(
        blank=True, null=True,
        help_text=_('Detailed description of the asset category.')
    )
    def __str__(self):
        return str(self.name) if self.name else ''


class AssetSubCategory(OwnerPrivModel, Dated, models.Model):
    """
    Represents a subcategory within an asset category.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique code for the asset subcategory.')
    )
    name = models.CharField(
        max_length=100,
        help_text=_('Name of the asset subcategory.')
    )
    type = models.CharField(
        max_length=50,
        help_text=_('Type of the asset subcategory.')
    )
    description = models.TextField(
        blank=True, null=True,
        help_text=_('Detailed description of the asset subcategory.')
    )
    asset_category = models.ForeignKey(
        AssetCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        help_text=_('The asset category this subcategory belongs to.')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Is this subcategory active?')
    )
    def __str__(self):
        return str(self.name) if self.name else ''
