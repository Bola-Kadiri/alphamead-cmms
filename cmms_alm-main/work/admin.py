from django.contrib import admin
from .models import WorkRequest, WorkOrder, PaymentItem, PaymentRequisition, PPM
from work.models import WorkOrderCompletion

class WorkRequestAdmin(admin.ModelAdmin):
    list_display = ("type", "requester", "category", "facility", "created_at",)
    search_fields = ("type", "requester__username", "category__name", "facility__name")
    list_filter = ("category", "require_mobilization_fee", "facility", "created_at")
    readonly_fields = ("slug",)  

admin.site.register(WorkRequest, WorkRequestAdmin)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id',  'type', 'priority', 'facility', 'requester', 'approval_status', 'expected_start_date')
    list_filter = ('type', 'priority', 'approval_status', 'facility', 'department')
    search_fields = ( 'work_order_number', 'requester__username', 'requester__email', 'facility__name')
    readonly_fields = ('work_order_number', 'slug')
    ordering = ('-expected_start_date',)
    autocomplete_fields = ('requester', 'work_owner', 'facility', 'department', 'category', 'subcategory', 'asset', 'request_to')
    
    
@admin.register(PaymentItem)
class PaymentItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for PaymentItem.
    """
    list_display = ("item_name", "work_order", "amount")
    search_fields = ("item_name", "work_order__id")
    list_filter = ("work_order",)
    ordering = ("item_name",)


@admin.register(PaymentRequisition)
class PaymentRequisitionAdmin(admin.ModelAdmin):
    """
    Admin configuration for PaymentRequisition.
    """
    list_display = ("requisition_number", "pay_to", "requisition_date", "expected_payment_date", "status", "approval_status", "expected_payment_amount")
    search_fields = ("requisition_number", "pay_to__username", "pay_to__email")
    list_filter = ("status", "approval_status", "retirement")
    ordering = ("-requisition_date",)
    autocomplete_fields = ("pay_to", "request_to", "items", "work_orders")  # For better UX in selection fields
    readonly_fields = ("requisition_number",)  # Prevent modification of generated requisition number
    filter_horizontal = ("items", "work_orders", "request_to")  # Better UI for ManyToMany fields

    fieldsets = (
        ("Payment Information", {
            "fields": ("requisition_number", "requisition_date", "pay_to", "expected_payment_date", "expected_payment_amount", "withholding_tax"),
        }),
        ("Details", {
            "fields": ("retirement", "remark", "comment"),
        }),
        ("Work Orders & Items", {
            "fields": ("work_orders", "items"),
        }),
        ("Approval & Status", {
            "fields": ("approval_status", "status", "request_to"),
        }),
    )
    
    
@admin.register(PPM)
class PPMAdmin(admin.ModelAdmin):
    """
    Admin configuration for Planned Preventive Maintenance (PPM).
    """
    list_display = (
        "id",
        "description",
        "category",
        "subcategory",
        "frequency",
        "frequency_unit",
        "notify_before_due",
        "send_reminder_every",
        "currency",
        "auto_create_work_order",
        "create_work_order_as_approved",
    )
    search_fields = ("description", "category__name", "subcategory__name")
    list_filter = ("category", "auto_create_work_order", "create_work_order_as_approved", "currency")
    ordering = ("-id",)
    autocomplete_fields = ("category", "subcategory", "assets", "facilities",  "items")  # Improves UX
    filter_horizontal = ("assets", "facilities",  "items")  # ManyToMany Fields
    readonly_fields = ("id",)

    fieldsets = (
        ("General Information", {
            "fields": ("description", "category", "subcategory"),
        }),
        ("Maintenance Frequency", {
            "fields": ("frequency", "frequency_unit", "notify_before_due", "notify_unit", "send_reminder_every", "reminder_unit"),
        }),
        ("Financial Information", {
            "fields": ("currency",),
        }),
        ("Automation", {
            "fields": ("auto_create_work_order", "create_work_order_as_approved"),
        }),
        ("Linked Resources", {
            "fields": ("assets", "facilities", "apartments", "items"),
        }),
        ("Additional Notes", {
            "fields": ("activities_safety_tips",),
        }),
    )

@admin.register(WorkOrderCompletion)
class WorkOrderCompletionAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'file', 'created_at', 'updated_at')
    search_fields = ('work_order__slug',)