from django.urls import path, include
from . import views
from .api import views as api_views
from rest_framework.routers import DefaultRouter

app_name = "asset_inventory"



urlpatterns = [
    path('api/', include('asset_inventory.api.urls')),
    # path('api/assets/<int:asset_id>/', views.get_asset_details, name='get_asset_details'),
]