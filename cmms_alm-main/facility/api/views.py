from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from cmms_instanta.permissions import RoleBasedPermissionMixin, accessible_facilities
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
    pagination_class = None

    def get_queryset(self):
        return accessible_facilities(self.request.user).order_by('-id')

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
        Get all zones for a specific facility. Scoped to facilities the
        requesting user can see — an inaccessible facility_id yields an
        empty list, matching how WorkRequest access is already isolated.
        """
        if not accessible_facilities(request.user).filter(pk=facility_id).exists():
            return Response([])
        zones = self.queryset.filter(facility_id=facility_id)
        serializer = self.get_serializer(zones, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
class BuildingViewSet(RoleBasedPermissionMixin, viewsets.ModelViewSet):
    queryset = Building.objects.all().order_by('-id')
    serializer_class = BuildingSerializer
    feature = "requisition"
    pagination_class = None
    
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

    @action(detail=False, methods=['get'], url_path='by-zone/(?P<zone_id>[^/.]+)')
    def by_zone(self, request, zone_id=None):
        """
        Get all subzones/spaces for a specific zone (for cascading
        site → zone → subzone dropdowns, e.g. when raising a Work Request).
        Scoped to facilities the requesting user can see.
        """
        if not Zone.objects.filter(pk=zone_id, facility__in=accessible_facilities(request.user)).exists():
            return Response([])
        subsystems = self.queryset.filter(zone_id=zone_id)
        serializer = self.get_serializer(subsystems, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-facility/(?P<facility_id>[^/.]+)')
    def by_facility(self, request, facility_id=None):
        """
        Get all subzones/spaces for a specific facility, regardless of zone
        (fallback for sites that don't organise subzones under a zone).
        Scoped to facilities the requesting user can see.
        """
        if not accessible_facilities(request.user).filter(pk=facility_id).exists():
            return Response([])
        subsystems = self.queryset.filter(facility_id=facility_id)
        serializer = self.get_serializer(subsystems, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        