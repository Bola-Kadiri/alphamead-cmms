from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from work.models import WorkRequest, WorkOrder, PaymentRequisition, PPM, WorkOrderCompletion, Invoice


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        # ---- WORK REQUEST COUNTS ----
        wr_pending = WorkRequest.objects.filter(
            approval_status__in=["Pending Review", "CP Approved", "Reviewed"]
        ).count()
        wr_approved = WorkRequest.objects.filter(approval_status="Fully Approved").count()
        wr_rejected = WorkRequest.objects.filter(
            approval_status__in=["Rejected – Vendor Changed", "Reviewer Rejected", "Approver Rejected"]
        ).count()

        # ---- WORK ORDER COUNTS ----
        wo_pending = WorkOrder.objects.filter(approval_status="Pending").count()
        wo_approved = WorkOrder.objects.filter(approval_status="Approved").count()
        wo_rejected = WorkOrder.objects.filter(approval_status="Rejected").count()
        wo_overdue = WorkOrder.objects.filter(
            approval_status="Approved",
            expected_start_date__lt=today
        ).count()

        # ---- WORK COMPLETION COUNTS ----
        wcc_pending = WorkOrderCompletion.objects.filter(approval_status='Pending').count()
        wcc_reviewed = WorkOrderCompletion.objects.filter(approval_status='Reviewed').count()
        wcc_approved = WorkOrderCompletion.objects.filter(approval_status='Approved').count()
        wcc_rejected = WorkOrderCompletion.objects.filter(
            approval_status__in=['Reviewer Rejected', 'Approver Rejected']
        ).count()

        # ---- INVOICE COUNTS ----
        inv_pending = Invoice.objects.filter(approval_status='Pending').count()
        inv_reviewed = Invoice.objects.filter(approval_status='Reviewed').count()
        inv_approved = Invoice.objects.filter(approval_status='Approved').count()
        inv_rejected = Invoice.objects.filter(
            approval_status__in=['Reviewer Rejected', 'Approver Rejected']
        ).count()

        # ---- CHART DATA (last 6 months) ----
        labels = []
        wr_counts = []
        wo_counts = []

        for i in range(5, -1, -1):
            # Calculate the first day of each month going back
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = today.replace(year=year, month=month, day=1)
            if month == 12:
                month_end = today.replace(year=year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = today.replace(year=year, month=month + 1, day=1) - timedelta(days=1)

            labels.append(month_start.strftime('%b %Y'))
            wr_counts.append(WorkRequest.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count())
            wo_counts.append(WorkOrder.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count())

        # ---- USER INFO ----
        user_name = (
            getattr(user, 'name', None)
            or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            or user.email
        )
        user_role = getattr(user, 'roles', 'User') or 'User'

        response_data = {
            "workspace_title": "Alpha CMMS Dashboard",
            "current_date": today.strftime('%A, %B %d, %Y'),
            "user_info": {
                "name": user_name,
                "role": user_role,
            },
            "navigation_tabs": [
                "WORK REQUEST",
                "WORK ORDER",
                "WORK COMPLETION",
                "INVOICES",
                "PAYMENT REQUISITION",
            ],
            "summary_cards": {
                "work_request": [
                    {"label": "New-Awaiting Work Request", "count": wr_pending, "amount": "N 0", "icon": "file-plus", "color": "blue"},
                    {"label": "Approved", "count": wr_approved, "amount": "N 0", "icon": "check-circle", "color": "green"},
                    {"label": "Rejected", "count": wr_rejected, "amount": "N 0", "icon": "x-circle", "color": "red"},
                ],
                "work_order": [
                    {"label": "New-Awaiting Review", "count": wo_pending, "amount": "N 0", "icon": "file-plus", "color": "blue"},
                    {"label": "Approved", "count": wo_approved, "amount": "N 0", "icon": "check-circle", "color": "green"},
                    {"label": "Rejected", "count": wo_rejected, "amount": "N 0", "icon": "x-circle", "color": "red"},
                    {"label": "Overdue", "count": wo_overdue, "amount": "N 0", "icon": "alert-triangle", "color": "orange"},
                ],
                "work_completion": [
                    {"label": "New-Awaiting Review", "count": wcc_pending, "amount": "N 0", "icon": "file-plus", "color": "blue"},
                    {"label": "Reviewed", "count": wcc_reviewed, "amount": "N 0", "icon": "check-circle", "color": "blue"},
                    {"label": "Approved", "count": wcc_approved, "amount": "N 0", "icon": "check-circle", "color": "green"},
                    {"label": "Rejected", "count": wcc_rejected, "amount": "N 0", "icon": "x-circle", "color": "red"},
                ],
                "invoices": [
                    {"label": "New-Awaiting Review", "count": inv_pending, "amount": "N 0", "icon": "file-plus", "color": "blue"},
                    {"label": "Reviewed", "count": inv_reviewed, "amount": "N 0", "icon": "check-circle", "color": "blue"},
                    {"label": "Approved", "count": inv_approved, "amount": "N 0", "icon": "check-circle", "color": "green"},
                    {"label": "Rejected", "count": inv_rejected, "amount": "N 0", "icon": "x-circle", "color": "red"},
                ],
                "payment_requisition": [],
            },
            "chart_data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Work Requests",
                        "data": wr_counts,
                        "backgroundColor": "rgba(59, 130, 246, 0.6)",
                    },
                    {
                        "label": "Work Orders",
                        "data": wo_counts,
                        "backgroundColor": "rgba(16, 185, 129, 0.6)",
                    },
                ],
                "current_year": today.year,
                "available_years": [today.year],
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
