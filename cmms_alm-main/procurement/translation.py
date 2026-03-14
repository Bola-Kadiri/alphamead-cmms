from modeltranslation.translator import register, TranslationOptions
from .models import (
    PurchaseOrderRequisition,
    PurchaseOrder, PurchaseOrderComment, PurchaseOrderApproval,
    RequestForQuotation,
    GoodsReceivedNote,
    VendorContract
)


@register(PurchaseOrderRequisition)
class PurchaseOrderRequisitionTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


@register(PurchaseOrder)
class PurchaseOrderTranslationOptions(TranslationOptions):
    fields = ('type', 'terms_and_conditions')


@register(PurchaseOrderComment)
class PurchaseOrderCommentTranslationOptions(TranslationOptions):
    fields = ('comment',)


@register(PurchaseOrderApproval)
class PurchaseOrderApprovalTranslationOptions(TranslationOptions):
    fields = ('comment',)


@register(RequestForQuotation)
class RequestForQuotationTranslationOptions(TranslationOptions):
    fields = ('title', 'terms')


@register(VendorContract)
class VendorContractTranslationOptions(TranslationOptions):
    fields = ('contract_title',)
