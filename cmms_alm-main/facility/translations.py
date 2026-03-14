from modeltranslation.translator import register, TranslationOptions
from .models import (Apartment, ApartmentType, BulkNotification, InvoicePayment, Facility)

# @register(Apartment)
# class ApartmentTranslationOptions(TranslationOptions):
#     fields = ('type','description',)

# @register(ApartmentType)
# class ApartmentTypeTranslationOptions(TranslationOptions):
#     fields = ('name',)

# @register(BulkNotification)
# class BulkNotificationTranslationOptions(TranslationOptions):
#     fields = ('message',)

# @register(InvoicePayment)
# class InvoicePaymentTranslationOptions(TranslationOptions):
#     fields = ('mode', 'remark')

# @register(Facility)
# class FacilityTranslationOptions(TranslationOptions):
#     fields = ('type',)