from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum, F

from cmms_instanta.permissions import RoleBasedPermissionMixin

from work.models import WorkRequest, WorkOrder, PaymentRequisition, PPM


class DashboardAPIView(RoleBasedPermissionMixin, APIView):
    """
    API view that returns dashboard data for Work Requests, Work Orders, Payment Requisitions, and PPMs.
    """
    # permission_classes = [IsAuthenticated]
    feature = "work_request"
    
    def get(self, request):
        """
        Get dashboard data for the authenticated user.
        """
        user = request.user
        today = timezone.now().date()
        
        # Get counts from database
        # ESCALATED TO ME section
        work_requests_escalated = WorkRequest.objects.filter(
            request_to=user, 
            approval_status="Pending",
            status="Active"
        ).count()
        
        work_orders_escalated = WorkOrder.objects.filter(
            request_to=user, 
            approval_status="Pending",
            status="Active"
        ).count()
        
        payment_requests_escalated = PaymentRequisition.objects.filter(
            request_to=user, 
            approval_status="request",
            status="Active"
        ).count()
        
        # PPM DUE section
        # Calculate PPMs due from database
        today = timezone.now().date()
        
        # Almost due - PPMs where due date is approaching within notification period
        ppms = PPM.objects.filter(status="Active")
        almost_due_count = 0
        over_due_count = 0
        due_today_count = 0
        
        for ppm in ppms:
            # For a real implementation, you'd need to track the last completion date
            # and calculate due dates based on that
            last_completed = getattr(ppm, 'last_completed_date', ppm.created_at.date())
            
            # Calculate due date based on frequency settings
            if ppm.frequency_unit == 'Days':
                due_date = last_completed + timedelta(days=ppm.frequency)
            elif ppm.frequency_unit == 'Weeks':
                due_date = last_completed + timedelta(weeks=ppm.frequency)
            elif ppm.frequency_unit == 'Months':
                due_date = last_completed + timedelta(days=ppm.frequency * 30)
            else:  # Hours
                due_date = last_completed + timedelta(hours=ppm.frequency)
            
            # Calculate notification threshold
            notify_days = 0
            if ppm.notify_before_due:
                if ppm.notify_unit == 'Days':
                    notify_days = ppm.notify_before_due
                elif ppm.notify_unit == 'Weeks':
                    notify_days = ppm.notify_before_due * 7
                elif ppm.notify_unit == 'Months':
                    notify_days = ppm.notify_before_due * 30
                elif ppm.notify_unit == 'Hours':
                    notify_days = ppm.notify_before_due / 24
            
            # Check due status
            if due_date < today:
                over_due_count += 1
            elif due_date == today:
                due_today_count += 1
            elif today >= due_date - timedelta(days=notify_days):
                almost_due_count += 1
        
        # WORK REQUEST section
        new_work_requests = WorkRequest.objects.filter(
            status="Active"
        ).filter(
            Q(created_at__date=today) | 
            Q(approval_status="Pending", type="Unplanned")
        ).count()
        
        open_work_requests = WorkRequest.objects.filter(
            status="Active",
            approval_status="Approved"
        ).exclude(
            created_at__date=today
        ).count()
        
        quotation_work_requests = WorkRequest.objects.filter(
            status="Active",
            require_quotation=True,
            approval_status="Approved"
        ).count()
        
        awaiting_work_requests = WorkRequest.objects.filter(
            status="Active",
            approval_status="Pending",
            type="Planned"
        ).count()
        
        # WORK ORDER section
        new_work_orders = WorkOrder.objects.filter(
            status="Active"
        ).filter(
            Q(created_at__date=today) | 
            Q(approval_status="Pending", type="Unplanned")
        ).count()
        
        open_work_orders = WorkOrder.objects.filter(
            status="Active",
            approval_status="Approved",
            expected_start_date__gt=today
        ).count()
        
        started_work_orders = WorkOrder.objects.filter(
            status="Active",
            approval_status="Approved"
        ).filter(
            Q(expected_start_date=today)
        ).count()
        
        overdue_work_orders = WorkOrder.objects.filter(
            status="Active",
            expected_start_date__lt=today,
            approval_status="Approved"
        ).count()
        
        awaiting_work_orders = WorkOrder.objects.filter(
            status="Active",
            approval_status="Pending",
            type="Planned"
        ).count()
        
        pending_work_orders = WorkOrder.objects.filter(
            status="Active",
            approval_status="Approved",
            expected_start_date__gt=today
        ).count()
        
        # PAYMENT REQUISITION section
        new_payment_reqs = PaymentRequisition.objects.filter(
            status="Active",
            created_at__date=today
        ).count()
        
        awaiting_payment_reqs = PaymentRequisition.objects.filter(
            status="Active",
            approval_status="request"
        ).count()
        
        pending_payment_reqs = PaymentRequisition.objects.filter(
            status="Active"
        ).filter(
            Q(approval_status="approve") &
            ~Q(expected_payment_date=today)
        ).count()
        
        part_paid_payment_reqs = PaymentRequisition.objects.filter(
            status="Active"
        ).annotate(
            total_items=Sum('items__amount')
        ).filter(
            expected_payment_amount__lt=F('total_items')
        ).count()
        
        # Build the response data structure
        dashboard_data = {
            "escalated_to_me": [
                {
                    "label": "Work Request",
                    "count": work_requests_escalated
                },
                {
                    "label": "Work Order",
                    "count": work_orders_escalated
                },
                {
                    "label": "Payment Request",
                    "count": payment_requests_escalated
                }
            ],
            "ppm_due": [
                {
                    "label": "Almost Due",
                    "count": almost_due_count
                },
                {
                    "label": "Over Due",
                    "count": over_due_count
                },
                {
                    "label": "Due Today",
                    "count": due_today_count
                }
            ],
            "work_request": [
                {
                    "label": "New",
                    "count": new_work_requests
                },
                {
                    "label": "Open",
                    "count": open_work_requests
                },
                {
                    "label": "Quotation",
                    "count": quotation_work_requests
                },
                {
                    "label": "Awaiting",
                    "count": awaiting_work_requests
                }
            ],
            "work_order": [
                {
                    "label": "New",
                    "count": new_work_orders
                },
                {
                    "label": "Open",
                    "count": open_work_orders
                },
                {
                    "label": "Started",
                    "count": started_work_orders
                },
                {
                    "label": "Over-Due",
                    "count": overdue_work_orders
                },
                {
                    "label": "Awaiting",
                    "count": awaiting_work_orders
                },
                {
                    "label": "Pending",
                    "count": pending_work_orders
                }
            ],
            "payment_requisition": [
                {
                    "label": "New Payment",
                    "count": new_payment_reqs
                },
                {
                    "label": "Awaiting Approval",
                    "count": awaiting_payment_reqs
                },
                {
                    "label": "Payment Pending",
                    "count": pending_payment_reqs
                },
                {
                    "label": "Part Paid",
                    "count": part_paid_payment_reqs
                }
            ]
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)