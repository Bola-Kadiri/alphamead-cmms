from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, OwnerPrivModel
from accounts.models import Vendor, Category, Subcategory
from facility.models import Facility
from .assets_category import AssetCategory, AssetSubCategory
from .inventory_reference import ModelReference, InventoryType

class Inventory(OwnerPrivModel, Dated, models.Model):
    STATUS_CHOICES = [
        ("Available", _("Available")),
        ("Low Stock", _("Low Stock")),
        ("Out of Stock", _("Out of Stock")),
        ("Discontinued", _("Discontinued")),
    ]
    
    # Inventory status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=_("Available"))

    # 1–3: Type, Category, Subcategory
    type = models.ForeignKey(InventoryType, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, related_name='inventory_categories')
    subcategory = models.ForeignKey(AssetSubCategory, on_delete=models.CASCADE, related_name='inventory_subcategories')

    # 4–6: Model, Part No, Tag
    model = models.ForeignKey(ModelReference, on_delete=models.SET_NULL, blank=True, null=True)
    part_no = models.CharField(max_length=100, null=True, blank=True)
    tag = models.CharField(max_length=100, null=True, blank=True)

    # 7: Serial Number
    serial_number = models.CharField(max_length=100, null=True, blank=True)

    # 8–9: Quantity, Unit Price
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], help_text=_("Current quantity in stock"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], help_text=_("Unit price in NGN"))


    # 11: Vendor
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_vendors')

    # 12–14: Purchase Number, Purchase Date, Manufacture Date
    purchase_number = models.CharField(max_length=100, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)

    # 15–16: Expiry Date, Warranty End Date
    expiry_date = models.DateField(null=True, blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)

    # 17: Facility
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_facility')

    # 18–20: Reorder Level, Min Stock, Max Stock
    reorder_level = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0)
    max_stock = models.PositiveIntegerField(default=0)

    # 21: Flags (e.g., status flags)
    flags = models.CharField(max_length=100, null=True, blank=True)

    
    
    # 22: Restock button (not stored in DB – action/UI logic)
    def restock(self):
        # Logic to trigger restock can go here
        pass
    
    # 10: Log Value (quantity * unit_price)
    @property
    def log_value(self):
        return self.quantity * self.unit_price if self.unit_price else 0

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.type} - {self.serial_number or 'No Serial'}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.quantity < 0:
            raise ValidationError({'quantity': _('Quantity cannot be negative')})

        if self.expiry_date and self.manufacture_date and self.expiry_date < self.manufacture_date:
            raise ValidationError({'expiry_date': _('Expiry date cannot be earlier than manufacture date')})

        if self.warranty_end_date and self.purchase_date and self.warranty_end_date < self.purchase_date:
            raise ValidationError({'warranty_end_date': _('Warranty end date cannot be earlier than purchase date')})

        if self.quantity == 0:
            self.status = _("Out of Stock")
        elif self.quantity <= self.reorder_level:
            self.status = _("Low Stock")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
