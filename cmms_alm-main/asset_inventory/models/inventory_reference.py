from django.db import models
from accounts.models import Category, Subcategory
from asset_inventory.models.assets_category import AssetCategory, AssetSubCategory

class InventoryType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=100)
    unit_of_measurement = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.code} - {self.type}"

class Manufacturer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ModelReference(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    subcategory = models.ForeignKey(AssetSubCategory, on_delete=models.CASCADE, related_name='models')
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='models')

    def __str__(self):
        return self.name

class InventoryReference(models.Model):
    inventory_type = models.ForeignKey(InventoryType, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_references')
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_references')
    subcategory = models.ForeignKey(AssetSubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_references')
    model_reference = models.ForeignKey(ModelReference, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_references')
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_references')

    def __str__(self):
        return f"Ref: {self.inventory_type or ''} | {self.category or ''} | {self.subcategory or ''} | {self.model_reference or ''} | {self.manufacturer or ''}"
