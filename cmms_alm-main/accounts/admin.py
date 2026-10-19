import io
from functools import reduce

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import path, reverse

from accounts.models import *
from accounts.forms import UserAdminCreationForm, UserAdminChangeForm, UserChangeForm
from accounts.vendor_import import (
    import_vendors_from_csv, TEMPLATE_HEADER as VENDOR_TEMPLATE_HEADER, TEMPLATE_ROWS as VENDOR_TEMPLATE_ROWS,
)
from utils.csv_import import csv_template_response, is_super_admin

User = get_user_model()

@admin.register(Onboarding)
class AuthorAdmin(admin.ModelAdmin):
    pass

class SearchableAdmin(admin.ModelAdmin):
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        search_fields = self.get_search_fields(request)
        if search_fields and search_term:
            orm_lookups = [
                f'{search_field}__icontains' for search_field in search_fields
            ]
            or_queries = [Q(**{orm_lookup: search_term}) for orm_lookup in orm_lookups]
            queryset = queryset.filter(reduce(lambda x, y: x | y, or_queries))
        return queryset, use_distinct


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for the User model.
    """
    form = UserChangeForm
    add_form = UserAdminCreationForm

    list_display = [
        'id', 'email', 'first_name', 'last_name', 'roles', 'is_active', 'is_verified',
        'is_blocked', 'is_staff', 'is_admin', 'is_superuser', 'last_login',
    ]
    list_filter = ['is_superuser', 'is_staff', 'is_active', 'is_verified', 'is_blocked', 'roles']

    fieldsets = (
        (None, {
            'fields': (
                'email', 'password', 'first_name', 'last_name', 'slug', 'roles', 'phone', 'designation',
                'supervisor', 'date_of_birth', 'gender', 'avatar', 'nationality', 'passport_number', 'address'
            )
        }),
        ('Privileges and Permissions', {
            'fields': (
                'status', 'team_lead', 'generate_reports', 'approval_limit', 'is_verified',
                'is_blocked', 'is_active', 'is_staff', 'is_admin', 'is_superuser',
                'access_to_all_facilities', 'facility',
                'access_to_all_apartments', 'apartments',
                'access_to_all_categories', 'categories', 'access_to_all_buildings', 'buildings',
                'access_to_all_warehouses',
                'warehouse', 'access_to_all_clients', 'clients'
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password', 'password_2', 'first_name', 'last_name', 'roles',
                'phone', 'designation', 'date_of_birth', 'gender', 'nationality', 'passport_number',
                'address', 'is_active', 'is_staff', 'is_admin', 'is_superuser'
            )
        }),
    )

    search_fields = ['email', 'first_name', 'last_name', 'roles']
    ordering = ['id']
    filter_horizontal = ('facility', 'buildings', 'apartments', 'categories', 'warehouse', 'clients')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """
    Admin configuration for BankAccount model.
    """
    list_display = (
        "account_name",
        "account_number",
        "bank",
        "currency",
        "status",
        
        "created_at",
        "updated_at",
    )
    list_filter = (
        "bank",
        "currency",
        "status",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "account_name",
        "account_number",
    )
    readonly_fields = (
        
        
        "created_at",
        "updated_at",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for Category model.
    """
    list_display = (
        "code",
        "problem_type",
        "work_request_approved",
        "exclude_costing_limit",
        "power",
        "create_payment_requisition",
        "status",
        
        "created_at",
        "updated_at",
    )
    list_filter = (
        "exclude_costing_limit",
        "power",
        "create_payment_requisition",
        "status",
        "work_request_approved",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "code",
        "problem_type",
    )
    readonly_fields = (
        
        "created_at",
        "updated_at",
    )
    
    

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "code", "email", "phone", "group",   "created_at", "updated_at")
    search_fields = ("name", "code", "email", "phone", "group")
    list_filter = ("type", "group", "created_at", "updated_at")
    readonly_fields = (  "created_at", "updated_at")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "created_at", "updated_at")
    search_fields = ("name", "code")
    list_filter = ("status", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UnitOfMeasurement)
class UnitOfMeasurementAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "symbol", "status",   "created_at", "updated_at")
    search_fields = ("code", "symbol")
    list_filter = ("type", "status", "created_at", "updated_at")
    readonly_fields = (  "created_at", "updated_at")


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ("staff_number", "first_name", "last_name", "email", "phone_number",   "created_at", "updated_at")
    search_fields = ("staff_number", "owner__first_name", "owner__last_name", "owner__email", "owner__phone")
    readonly_fields = (  "created_at", "updated_at")


@admin.register(Contact)
class ContactDetailsAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "email", "status")
    search_fields = ("first_name", "last_name", "phone", "email")
    list_filter = ("status",)


# @admin.register(Document)
# class DocumentAdmin(admin.ModelAdmin):
#     list_display = ("id", "description", "file")
#     search_fields = ("description",)


# @admin.register(Contract)
# class ContractAdmin(admin.ModelAdmin):
#     list_display = ("contract_number", "start_date", "end_date", "access_to_all_facilities")
#     search_fields = ("contract_number",)
#     list_filter = ("start_date", "end_date", "access_to_all_facilities")




@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Vendor model.
    """
    
    list_display = ("name", "type", "account_name", "bank", "bank_details", "currency", "status", "created_at", "updated_at")
    search_fields = ("name", "account_name", "account_number", "bank", "email", "phone")
    list_filter = ("type", "currency", "status", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("About Vendor", {
            "fields": ("name", "type", "status")
        }),
        ("Contact Details", {
            "fields": ("phone", "email")
        }),
        ("Bank Account Details", {
            "fields": ("account_name", "bank", "account_number", "currency")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    @admin.display(boolean=True, description="Can be paid")
    def bank_details(self, obj):
        return obj.has_bank_details

    # ── Super Admin bulk upload of vendors (same rules as the app's Bulk
    # Upload: preview first, all-or-nothing, adds only). ────────────────────
    BULK_SESSION_KEY = 'vendor_bulk_upload_csv'
    BULK_MAX_BYTES = 2 * 1024 * 1024

    def get_urls(self):
        custom_urls = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view),
                 name='accounts_vendor_bulk_upload'),
            path('bulk-upload/template/', self.admin_site.admin_view(self.bulk_upload_template_view),
                 name='accounts_vendor_bulk_upload_template'),
        ]
        return custom_urls + super().get_urls()

    def bulk_upload_template_view(self, request):
        return csv_template_response('vendors_template.csv', VENDOR_TEMPLATE_HEADER, VENDOR_TEMPLATE_ROWS)

    def bulk_upload_view(self, request):
        changelist = reverse('admin:accounts_vendor_changelist')
        if not is_super_admin(request.user):
            messages.error(request, "Only a Super Admin can bulk upload vendors.")
            return redirect(changelist)

        result = None
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'preview':
                upload = request.FILES.get('csv_file')
                if not upload:
                    messages.error(request, "Choose a CSV file first.")
                elif upload.size > self.BULK_MAX_BYTES:
                    messages.error(request, "The file is too large (max 2 MB).")
                else:
                    raw = upload.read()
                    try:
                        result = import_vendors_from_csv(io.BytesIO(raw), owner=request.user, dry_run=True)
                    except ValueError as exc:
                        messages.error(request, str(exc))
                    else:
                        # Keep the previewed file so "Confirm" saves exactly what was shown.
                        request.session[self.BULK_SESSION_KEY] = raw.decode('utf-8-sig')
            elif action == 'confirm':
                content = request.session.pop(self.BULK_SESSION_KEY, None)
                if content is None:
                    messages.error(request, "Please choose the file and preview it again.")
                else:
                    try:
                        result = import_vendors_from_csv(
                            io.BytesIO(content.encode('utf-8')), owner=request.user, dry_run=False)
                    except ValueError as exc:
                        messages.error(request, str(exc))
                    else:
                        if result['saved']:
                            counts = result['counts']
                            messages.success(
                                request,
                                f"Upload complete: {counts.get('created', 0)} added, "
                                f"{counts.get('updated', 0)} updated, {counts.get('skipped', 0)} already existed.",
                            )
                            return redirect(changelist)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk upload vendors',
            'opts': self.model._meta,
            'result': result,
            'can_confirm': bool(result and result['dry_run'] and not result['errors']
                                and (result['counts'].get('created') or result['counts'].get('updated'))),
        }
        return render(request, 'admin/accounts/vendor_bulk_upload.html', context)


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'description', 'exclude_costing_limit', 'status')
    list_filter = ('status', 'exclude_costing_limit', 'category')
    search_fields = ('description', 'category__code')
    ordering = ('category',)
    list_per_page = 20

    fieldsets = (
        ("Subcategory Details", {
            'fields': ('category', 'title', 'description', 'status', 'exclude_costing_limit')
        }),
    )