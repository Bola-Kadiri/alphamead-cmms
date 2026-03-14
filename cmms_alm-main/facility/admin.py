from django.contrib import admin
from .models import *

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'select_manager', 'created_at', 'updated_at')
    list_filter = ('country', 'created_at', 'updated_at')
    search_fields = ('name', 'country')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'select_manager', 'created_at', 'updated_at')
    list_filter = ('region', 'created_at', 'updated_at')
    search_fields = ('name', 'region__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'cluster', 'type', 'manager', 'created_at', 'updated_at')
    list_filter = ('cluster', 'type', 'created_at', 'updated_at')
    search_fields = ('name',  'cluster__name')
    readonly_fields = ('created_at', 'updated_at')
   
# @admin.register(Facility)
# class FacilityAdmin(admin.ModelAdmin):
#     list_display = ('name',  'cluster', 'type', 'manager', 'created_at', 'updated_at')
#     list_filter = ('cluster', 'type', 'created_at', 'updated_at')
#     search_fields = ('name',  'cluster__name')
#     readonly_fields = ('created_at', 'updated_at')
#     fieldsets = (
#         ('General Information', {
#             'fields': ('owner', 'cluster',  'name', 'type', 'status')
#         }),
#         ('Contact Details', {
#             'fields': ('contact_name', 'email', 'phone', 'address', 'address_gps')
#         }),
#         ('Management', {
#             'fields': ('manager', 'facility_officer')
#         }),
#         ('Store', {
#             'fields': ('store',)
#         }),
#         ('Limits and Areas', {
#             'fields': ('non_procurement_limit', 'no_of_sqm', 'common_area')
#         }),
#         ('Lease Settings', {
#             'fields': ('available_for_lease', 'approval_required_for_imprest', 'remit_lease_payment')
#         }),
#     )

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'facility',  'created_at', 'updated_at')
    list_filter = ('facility',  'created_at', 'updated_at')
    search_fields = ('code', 'name', 'facility__name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'zone', 'facility', 'created_at', 'updated_at')
    list_filter = ('zone', 'facility', 'created_at', 'updated_at')
    search_fields = ('code', 'name', 'zone__name', 'facility__name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'building',  'created_at', 'updated_at')
    list_filter = ('building',  'created_at', 'updated_at')
    search_fields = ('name', 'building__name')
    readonly_fields = ('created_at', 'updated_at')

