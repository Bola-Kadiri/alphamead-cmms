from django.urls import path

from .views import ReportDashboardAnalyticsView, UserFacilityReportView

app_name = "report_api"

urlpatterns = [
    path('user-facility/', UserFacilityReportView.as_view(), name='user-facility-report'),
    path('dashboard/', ReportDashboardAnalyticsView.as_view(), name='dashboard-analytics'),
]
