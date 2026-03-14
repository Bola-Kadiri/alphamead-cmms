from modeltranslation.translator import register, TranslationOptions
from .models import (AssetCategory, AssetSubCategory, 
                     Asset, Inventory, Item, Transfer, ItemRequest,
                     Warehouse)

@register(AssetCategory)
class AssetCategoryTranslationOptions(TranslationOptions):
    fields = ('description',)

# @register(AssetSubCategory)
# class AssetSubCategoryTranslationOptions(TranslationOptions):
#     fields = ('title','description')

@register(Asset)
class AssetTranslationOptions(TranslationOptions):
    fields = ('oem_warranty',)

# @register(Inventory)
# class InventoryTranslationOptions(TranslationOptions):
#     fields = ('warranty_description',)

@register(Item)
class ItemTranslationOptions(TranslationOptions):
    fields = ('description',)

@register(ItemRequest)
class ItemRequestTranslationOptions(TranslationOptions):
    fields = ('description', 'comment')

@register(Transfer)
class TransferTranslationOptions(TranslationOptions):
    # fields = ('remark',)
    pass

@register(Warehouse)
class WarehouseTranslationOptions(TranslationOptions):
    fields = ('description', 'capacity')