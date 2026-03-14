from rest_framework import serializers
from facility.models import (
    Facility, Building, Apartment,
    Region, Cluster, Zone, Subsystem
)

from utils.translation_mixin import TranslatableFieldMixin

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'country', 'select_manager',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class RegionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'country']

class ClusterSerializer(serializers.ModelSerializer):
    region_detail = RegionSimpleSerializer(source='region', read_only=True)
    
    class Meta:
        model = Cluster
        # fields = [
        #     'id', 'region', 'region_detail', 'name', 'select_manager', 'status',
        #     'created_at', 'updated_at'
        # ]
        fields = [
            'id', 'region', 'region_detail', 'name', 'select_manager',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'region_detail', 'created_at', 'updated_at']

class ClusterSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = ['id', 'name', 'region']


class FacilitySerializer(serializers.ModelSerializer):
    cluster_detail = ClusterSimpleSerializer(source='cluster', read_only=True)
    
    class Meta:
        model = Facility
        fields = [
            'id', 'cluster', 'cluster_detail', 'code', 'name', 'address_gps',
            'type', 'manager', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'cluster_detail', 'created_at', 'updated_at']
        # translatable_fields = ['type']

class FacilitySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'code', 'name', 'cluster']

class ZoneSerializer(serializers.ModelSerializer):
    facility_detail = FacilitySimpleSerializer(source='facility', read_only=True)
    
    class Meta:
        model = Zone
        # fields = [
        #     'id', 'code', 'name', 'facility', 'facility_detail', 'status',
        #     'created_at', 'updated_at'
        # ]
        fields = [
            'id', 'code', 'name', 'facility', 'facility_detail',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'facility_detail', 'created_at', 'updated_at']

class ZoneSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'code', 'name']

class BuildingSerializer(serializers.ModelSerializer):
    zone_detail = ZoneSimpleSerializer(source='zone', read_only=True)
    facility_detail = FacilitySimpleSerializer(source='facility', read_only=True)

    class Meta:
        model = Building
        fields = [
            'id', 'code', 'name', 'zone', 'zone_detail', 'facility', 'facility_detail', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'zone_detail', 'facility_detail', 'created_at', 'updated_at']
        
class BuildingSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'code', 'name']

class SubsystemSerializer(serializers.ModelSerializer):
    building_detail = BuildingSimpleSerializer(source='building', read_only=True)
    
    class Meta:
        model = Subsystem
        # fields = [
        #     'id', 'name', 'building', 'building_detail', 'status',
        #     'created_at', 'updated_at'
        # ]
        fields = [
            'id', 'name', 'building', 'building_detail',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'building_detail', 'created_at', 'updated_at']

class SubsystemSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subsystem
        fields = ['id', 'name']


class ApartmentSerializer(serializers.ModelSerializer):
    building_detail = BuildingSimpleSerializer(source='building', read_only=True)
    
    class Meta:
        model = Apartment
        fields = [
            'id', 'no', 'type', 'building', 'building_detail', 'no_of_sqm',
            'description', 'landlord', 'ownership_type', 'service_power_charge_start_date',
            'address', 'bookable', 'common_area', 'available_for_lease',
            'remit_lease_payment', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'building_detail', 'created_at', 'updated_at']


class ApartmentSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ['id', 'no', 'type', 'building']
