from django.urls import path
from report import views

app_name = "report"

urlpatterns = [
    path("user_facility/", views.user_facility, name="user_facility"),
    path("user_audit/", views.user_audit, name="user_audit"),
    path("scheduled/", views.scheduled, name="scheduled"),
    path("usage_report/", views.usage_report, name="usage_report"),

]