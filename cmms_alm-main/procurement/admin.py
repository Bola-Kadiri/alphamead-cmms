from django.contrib import admin
from .models import (
    RequestForQuotation,
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderApproval, PurchaseOrderComment,
    GoodsReceivedNote,
    PurchaseOrderRequisition,
    VendorContract
)


# --- RFQ ---
@admin.register(RequestForQuotation)
class RequestForQuotationAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'currency', 'requester', 'facility', 'created_at']
    search_fields = ['title', 'type']
    list_filter = ['type', 'currency', 'created_at']
    raw_id_fields = ['requester', 'facility']
    filter_horizontal = ['vendors']


# --- Purchase Order ---
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['type', 'facility', 'department', 'vendor', 'status', 'requested_date']
    search_fields = ['type']
    list_filter = ['status', 'type', 'requested_date']
    raw_id_fields = ['facility', 'department', 'vendor', 'requested_by']


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'description', 'quantity', 'unit']
    search_fields = ['description']
    raw_id_fields = ['purchase_order']


@admin.register(PurchaseOrderComment)
class PurchaseOrderCommentAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'user', 'created_at']
    search_fields = ['comment']
    raw_id_fields = ['purchase_order', 'user']


@admin.register(PurchaseOrderApproval)
class PurchaseOrderApprovalAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'approver', 'approved', 'decision_date']
    list_filter = ['approved', 'decision_date']
    raw_id_fields = ['purchase_order', 'approver']


# --- GRN ---
@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = ['grn_number', 'purchase_order', 'vendor', 'facility', 'date_of_receipt', 'received_by']
    search_fields = ['grn_number', 'delivery_note_number', 'invoice_number']
    list_filter = ['date_of_receipt', 'created_at']
    raw_id_fields = ['purchase_order', 'facility', 'vendor', 'received_by']


# --- PO Requisition ---
@admin.register(PurchaseOrderRequisition)
class PurchaseOrderRequisitionAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor', 'invoice_number', 'amount', 'expected_delivery_date', 'created_at']
    search_fields = ['title', 'invoice_number', 'sage_reference_number']
    list_filter = ['expected_delivery_date', 'created_at']
    raw_id_fields = ['vendor']


# --- Vendor Contract ---
@admin.register(VendorContract)
class VendorContractAdmin(admin.ModelAdmin):
    list_display = ['contract_title', 'vendor', 'contract_type', 'start_date', 'end_date', 'proposed_value', 'reviewer']
    search_fields = ['contract_title']
    list_filter = ['contract_type', 'start_date', 'end_date']
    raw_id_fields = ['vendor', 'reviewer']
