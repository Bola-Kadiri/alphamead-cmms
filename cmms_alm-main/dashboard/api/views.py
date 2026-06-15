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
        role = getattr(user, 'roles', '').strip().upper()

        # ---- BUILD ROLE-SCOPED BASE QUERYSETS ----
        if role in ['SUPER ADMIN', 'ADMIN']:
            wr_qs = WorkRequest.objects
            wo_qs = WorkOrder.objects
            wcc_qs = WorkOrderCompletion.objects
            inv_qs = Invoice.objects
        elif role == 'PROCUREMENT AND STORE':
            wr_qs = WorkRequest.objects.filter(request_to=user)
            wo_qs = WorkOrder.objects.filter(owner=user)
            wcc_qs = WorkOrderCompletion.objects.filter(owner=user)
            inv_qs = Invoice.objects.filter(owner=user)
        elif role == 'REVIEWER':
            wr_qs = WorkRequest.objects.filter(reviewers=user)
            wo_qs = WorkOrder.objects.filter(reviewers=user)
            wcc_qs = WorkOrderCompletion.objects.filter(reviewers=user)
            inv_qs = Invoice.objects.filter(reviewers=user)
        elif role == 'APPROVER':
            wr_qs = WorkRequest.objects.filter(approver=user)
            wo_qs = WorkOrder.objects.filter(approver=user)
            wcc_qs = WorkOrderCompletion.objects.filter(approver=user)
            inv_qs = Invoice.objects.filter(approver=user)
        else:
            wr_qs = WorkRequest.objects.filter(owner=user)
            wo_qs = WorkOrder.objects.filter(owner=user)
            wcc_qs = WorkOrderCompletion.objects.filter(owner=user)
            inv_qs = Invoice.objects.filter(owner=user)

        # ---- WORK REQUEST COUNTS ----
        wr_pending = wr_qs.filter(
            approval_status__in=["Pending Review", "CP Approved", "Reviewed"]
        ).count()
        wr_approved = wr_qs.filter(approval_status="Fully Approved").count()
        wr_rejected = wr_qs.filter(
            approval_status__in=["Rejected – Vendor Changed", "Reviewer Rejected", "Approver Rejected"]
        ).count()

        # ---- WORK ORDER COUNTS ----
        wo_pending = wo_qs.filter(approval_status="Pending").count()
        wo_approved = wo_qs.filter(approval_status="Approved").count()
        wo_rejected = wo_qs.filter(approval_status="Rejected").count()
        wo_overdue = wo_qs.filter(
            approval_status="Approved",
            expected_start_date__lt=today
        ).count()

        # ---- WORK COMPLETION COUNTS ----
        wcc_pending = wcc_qs.filter(approval_status='Pending').count()
        wcc_reviewed = wcc_qs.filter(approval_status='Reviewed').count()
        wcc_approved = wcc_qs.filter(approval_status='Approved').count()
        wcc_rejected = wcc_qs.filter(
            approval_status__in=['Reviewer Rejected', 'Approver Rejected']
        ).count()

        # ---- INVOICE COUNTS ----
        inv_pending = inv_qs.filter(approval_status='Pending').count()
        inv_reviewed = inv_qs.filter(approval_status='Reviewed').count()
        inv_approved = inv_qs.filter(approval_status='Approved').count()
        inv_rejected = inv_qs.filter(
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
