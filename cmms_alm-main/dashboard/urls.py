from django.urls import path, include
from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path('api/', include('dashboard.api.urls')),
  
]