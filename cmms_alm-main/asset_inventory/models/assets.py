from django.db import models
from django.conf import settings
from utils.models import Dated, UserPrivModel, OwnerPrivModel
from accounts.models import Category, Subcategory
from .assets_category import AssetCategory, AssetSubCategory
from facility.models import Facility, Zone, Building, Subsystem
from django.utils.translation import gettext_lazy as _

class Asset(OwnerPrivModel, Dated, models.Model):
    """
    Represents an asset in the asset registry.
    """
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Facility where the asset is located.")
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Zone where the asset is located.")
    )
    building = models.ForeignKey(
        Building,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Building where the asset is located.")
    )
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Subsystem where the asset is located.")
    )
    asset_name = models.CharField(
        max_length=255,
        help_text=_("Name of the asset.")
    )
    asset_type = models.CharField(
        max_length=50,
        choices=[
            ("Asset", _("Asset")),
            ("Consumable", _("Consumable")),
        ],
        default="Asset",
        help_text=_("Type of the asset item.")
    )
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Category of the asset.")
    )
    subcategory = models.ForeignKey(
        AssetSubCategory,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assets',
        help_text=_("Subcategory of the asset.")
    )
    condition = models.CharField(
        max_length=50,
        choices=[
            ("Used", _("Used")),
            ("Brand New", _("Brand New")),
        ],
        blank=True, null=True,
        help_text=_("Condition of the asset.")
    )
    purchase_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("Date when the asset was purchased.")
    )
    purchased_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True, null=True,
        help_text=_("Amount for which the asset was purchased.")
    )
    serial_number = models.CharField(
        max_length=255,
        blank=True, null=True,
        unique=True,
        help_text=_("Unique serial number of the asset.")
    )
    asset_tag = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Unique asset tag identifier.")
    )
    lifespan = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Expected lifespan of the asset (e.g., '5 years').")
    )
    oem_warranty = models.TextField(
        blank=True, null=True,
        help_text=_("Details of the OEM warranty.")
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.asset_name} ({self.asset_tag})"
