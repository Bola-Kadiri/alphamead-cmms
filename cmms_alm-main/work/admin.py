from django import forms
from django.contrib import admin
from .models import WorkRequest, WorkOrder, PaymentItem, PaymentRequisition, PPM
from work.models import WorkOrderCompletion
from work.models import RaisePaymentApprovalSettings, ApprovalMatrix, CompanyApprovers, FlowAction, Delegation, StageTimeLimit
from work.models import PaymentVoucher, WithholdingTaxRate
from utils.csv_import import is_super_admin


class WorkRequestAdminForm(forms.ModelForm):
    class Meta:
        model = WorkRequest
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('facility', 'zone', 'subsystem', 'asset', 'category', 'subcategory'):
            self.fields[field_name].required = True


class WorkRequestAdmin(admin.ModelAdmin):
    form = WorkRequestAdminForm
    list_display = ("type", "requester", "category", "facility", "zone", "subsystem", "created_at",)
    search_fields = ("type", "requester__username", "category__name", "facility__name", "zone__name", "subsystem__name")
    list_filter = ("category", "require_mobilization_fee", "facility", "zone", "created_at")
    readonly_fields = ("slug",)

admin.site.register(WorkRequest, WorkRequestAdmin)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id',  'type', 'priority', 'facility', 'requester', 'approval_status', 'work_status', 'expected_start_date')
    list_filter = ('type', 'priority', 'approval_status', 'work_status', 'facility', 'department')
    search_fields = ( 'work_order_number', 'requester__username', 'requester__email', 'facility__name')
    readonly_fields = ('work_order_number', 'slug')
    ordering = ('-expected_start_date',)
    autocomplete_fields = ('requester', 'work_owner', 'facility', 'department', 'asset', 'request_to')
    
    
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
    autocomplete_fields = ("pay_to", "payee_personnel", "payee_owner", "request_to", "items", "work_orders")  # For better UX in selection fields
    readonly_fields = ("requisition_number",)  # Prevent modification of generated requisition number
    filter_horizontal = ("items", "work_orders", "request_to")  # Better UI for ManyToMany fields

    fieldsets = (
        ("Payment Information", {
            "fields": ("requisition_number", "requisition_date", "payee_type", "pay_to", "payee_personnel", "payee_owner", "expected_payment_date", "expected_payment_amount", "withholding_tax"),
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
            "fields": ("assets", "facilities", "buildings", "items"),
        }),
        ("Additional Notes", {
            "fields": ("activities_safety_tips",),
        }),
    )

@admin.register(WorkOrderCompletion)
class WorkOrderCompletionAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_order', 'file', 'created_at', 'updated_at')
    search_fields = ('work_order__slug',)


@admin.register(RaisePaymentApprovalSettings)
class RaisePaymentApprovalSettingsAdmin(admin.ModelAdmin):
    """
    One row: the amount from which a Raise Payment bill needs a second approval,
    and who gives it. Only the Super Admin can see or change it.
    """
    list_display = ('threshold', 'second_approver_email', 'second_approver_account', 'updated_at')
    readonly_fields = ('second_approver_account', 'updated_at')

    @admin.display(description='AlphaCMMS account')
    def second_approver_account(self, obj):
        user = obj.second_approver()
        return f"{user.name.strip() or user.email} ({user.roles})" if user else "No active user with this email"

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return is_super_admin(request.user) and not RaisePaymentApprovalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class SuperAdminReadOnlyAdmin(admin.ModelAdmin):
    """Shown to the Super Admin for reference; changes go through the Approval Matrix screen,
    which checks every person's role and facility."""

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApprovalMatrix)
class ApprovalMatrixAdmin(SuperAdminReadOnlyAdmin):
    list_display = ('facility', 'approver', 'client_rep', 'is_live', 'missing')
    list_filter = ('is_live',)
    search_fields = ('facility__name',)

    @admin.display(description='Still missing')
    def missing(self, obj):
        return len(obj.problems()) or '—'


@admin.register(CompanyApprovers)
class CompanyApproversAdmin(SuperAdminReadOnlyAdmin):
    list_display = ('head_of_finance', 'updated_at')


@admin.register(FlowAction)
class FlowActionAdmin(SuperAdminReadOnlyAdmin):
    """The time-stamp trail. Read-only for everyone; rows can never be changed or deleted."""
    list_display = ('at', 'stage', 'action', 'actor_name', 'actor_role', 'on_behalf_of_name', 'facility',
                    'since_previous', 'content_type', 'object_id')
    list_filter = ('stage', 'action', 'actor_role', 'facility')
    search_fields = ('actor_name', 'on_behalf_of_name', 'reason')
    date_hierarchy = 'at'


@admin.register(Delegation)
class DelegationAdmin(SuperAdminReadOnlyAdmin):
    """Cover while away, for reference; created and ended from the app."""
    list_display = ('person', 'stand_in', 'starts_at', 'ends_at', 'value_limit', 'status', 'reason', 'ended_early_at')
    search_fields = ('person__email', 'stand_in__email', 'reason')


@admin.register(StageTimeLimit)
class StageTimeLimitAdmin(admin.ModelAdmin):
    """Time limit per stage: one company default per stage, optional per-client overrides. Super Admin only."""
    list_display = ('stage', 'client', 'hours', 'reminder_percent', 'updated_at')
    list_filter = ('stage', 'client')

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return is_super_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_super_admin(request.user)


@admin.register(WithholdingTaxRate)
class WithholdingTaxRateAdmin(admin.ModelAdmin):
    """Withholding tax rates; Finance keeps them from the app. Switch off rather than delete."""
    list_display = ('name', 'rate', 'is_active', 'updated_at')
    list_filter = ('is_active',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(SuperAdminReadOnlyAdmin):
    """Five-stage payment vouchers, for reference; every change is made in the app."""
    list_display = ('voucher_number', 'vendor', 'status', 'net_amount', 'paid_at')
    list_filter = ('status',)
    search_fields = ('voucher_number', 'vendor__name', 'bank_reference')
