from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from cmms_instanta.permissions import RoleBasedPermissionMixin
from facility.models import (
    Facility, Building,
    Region, Cluster, Zone, Subsystem
)

from .serializers import (
    FacilitySerializer, 
    BuildingSerializer,  RegionSerializer, ClusterSerializer,
    ZoneSerializer, SubsystemSerializer
)

class RegionViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Region.objects.all().order_by('-id')
    serializer_class = RegionSerializer
    feature = "requisition"

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ClusterViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Cluster.objects.all().order_by('-id')
    serializer_class = ClusterSerializer
    feature = "requisition"

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class FacilityViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Facility.objects.all().order_by('-id')
    serializer_class = FacilitySerializer
    feature = "requisition"
    lookup_field = 'code'
    
    @action(detail=True, methods=['get'], url_path='buildings')
    def list_buildings(self, request, code=None):
        facility = self.get_object()
        buildings = facility.buildings.all()
        serializer = BuildingSerializer(buildings, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ZoneViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Zone.objects.all().order_by('-id')
    serializer_class = ZoneSerializer
    feature = "requisition"
    
    @action(detail=False, methods=['get'], url_path='by-facility/(?P<facility_id>[^/.]+)')
    def by_facility(self, request, facility_id=None):
        """
        Get all zones for a specific facility
        """
        zones = self.queryset.filter(facility_id=facility_id)
        serializer = self.get_serializer(zones, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
class BuildingViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Building.objects.all().order_by('-id')
    serializer_class = BuildingSerializer
    feature = "requisition"
    
    @action(detail=False, methods=['get'], url_path='zones-by-facility/(?P<facility_id>[^/.]+)')
    def zones_by_facility(self, request, facility_id=None):
        """
        Get all zones for a specific facility (for building creation/editing)
        """
        zones = Zone.objects.filter(facility__id=facility_id)
        serializer = ZoneSerializer(zones, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class SubsystemViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Subsystem.objects.all().order_by('-id')
    serializer_class = SubsystemSerializer
    feature = "requisition"

    @action(detail=False, methods=['get'], url_path='buildings-by-facility/(?P<facility_id>[^/.]+)')
    def buildings_by_facility(self, request, facility_id=None):
        """
        Get all buildings for a specific facility (for subsystem creation/editing)
        """
        buildings = Building.objects.filter(facility__id=facility_id)
        serializer = BuildingSerializer(buildings, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        