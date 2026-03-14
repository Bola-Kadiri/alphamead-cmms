from django.urls import path, include
from . import views
from .api import views as api_views
from rest_framework.routers import DefaultRouter

app_name = "ppm_calendar"



urlpatterns = [
    path('api/', include('ppm_calendar.api.urls')),
]