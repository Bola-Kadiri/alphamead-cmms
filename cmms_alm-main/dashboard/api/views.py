from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from dashboard.services import get_dashboard_data


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_dashboard_data(request.user)
        return Response({
            'workspace_title': data['workspace_title'],
            'current_date': data['current_date'],
            'user_info': data['user_info'],
            'navigation_tabs': data['navigation_tabs'],
            'summary_cards': data['summary_cards'],
            'chart_data': data['chart_data'],
        }, status=status.HTTP_200_OK)
