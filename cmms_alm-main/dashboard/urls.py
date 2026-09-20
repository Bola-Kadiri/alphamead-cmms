from django.urls import path, include
from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path('', views.index, name='dashboard-home'),
    # Alias expected by templates/partials/sidebar.html ({% url 'dashboard:dashboard' %}),
    # which every page using partials/base.html renders — without it the sidebar
    # (and therefore every page in the app) fails with NoReverseMatch.
    path('', views.index, name='dashboard'),
    path('calendar/', views.calendar, name='calendar'),
    path('api/', include('dashboard.api.urls')),
]
