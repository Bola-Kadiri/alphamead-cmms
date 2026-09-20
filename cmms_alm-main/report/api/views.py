from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from cmms_instanta.permissions import RoleBasedPermissionMixin
from report.analytics import get_dashboard_analytics
from report.services import get_user_facility_report_queryset

from .response import APIResponse
from .serializers import UserFacilityReportSerializer


class UserFacilityReportView(RoleBasedPermissionMixin, generics.ListAPIView):
    """
    GET /report/api/user-facility/?facility=<id>&search=<text>&page=<n>&page_size=<n>

    Per-user activity summary for the User Facility Report page. See
    report.services.get_user_facility_report_queryset for the aggregation.

    authentication_classes is set explicitly (rather than relying on the
    project-wide JWTAuthentication-only default) so the browser page —
    which is reached through the ordinary session-based web login — can
    call this endpoint with its session cookie, the same way JWT API
    clients can with a bearer token.
    """
    serializer_class = UserFacilityReportSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    feature = "report"

    def get_queryset(self):
        return get_user_facility_report_queryset(
            facility_id=self.request.query_params.get('facility'),
            search=self.request.query_params.get('search'),
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return APIResponse.success(
                    data=paginated_response.data,
                    message="User facility report retrieved successfully"
                )
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="User facility report retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving user facility report: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportDashboardAnalyticsView(RoleBasedPermissionMixin, APIView):
    """
    GET /report/api/dashboard/

    Org-wide CMMS analytics: status breakdowns, backlog/aging, cycle
    times, financial totals, trends, and a generated list of
    plain-language insights across work requests, work orders,
    completions, invoices, payment requisitions, PPM, procurement, and
    assets/inventory. See report.analytics for the aggregation logic.
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    feature = "report"

    def get(self, request, *args, **kwargs):
        try:
            data = get_dashboard_analytics()
            return APIResponse.success(
                data=data,
                message="Dashboard analytics retrieved successfully"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error retrieving dashboard analytics: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
