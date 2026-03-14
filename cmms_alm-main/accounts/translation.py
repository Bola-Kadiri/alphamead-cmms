from modeltranslation.translator import register, TranslationOptions
from .models import Category, Subcategory, UnitOfMeasurement, Document

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('title','description', 'problem_type')

@register(Subcategory)
class SubcategoryTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

@register(UnitOfMeasurement)
class UnitOfMeasurementTranslationOptions(TranslationOptions):
    fields = ('description',)

@register(Document)
class DocumentTranslationOptions(TranslationOptions):
    fields = ('description',)