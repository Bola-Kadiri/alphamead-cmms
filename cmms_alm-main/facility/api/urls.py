from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
     FacilityViewSet,  BuildingViewSet, 
    RegionViewSet, ClusterViewSet, ZoneViewSet, SubsystemViewSet
)

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'clusters', ClusterViewSet, basename='cluster')
router.register(r'facilities', FacilityViewSet, basename='facility')
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'buildings', BuildingViewSet, basename='building')
router.register(r'subsystems', SubsystemViewSet, basename='subsystem')

urlpatterns = [
    path('api/', include(router.urls)),
]
