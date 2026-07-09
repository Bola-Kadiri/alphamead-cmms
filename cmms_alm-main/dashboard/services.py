from datetime import timedelta
from django.utils import timezone
from work.models import WorkRequest, WorkOrder, WorkOrderCompletion, Invoice, PaymentRequisition


def get_dashboard_data(user):
    today = timezone.now().date()
    role = getattr(user, 'roles', '').strip().upper()

    # ---- ROLE-SCOPED BASE QUERYSETS (each user sees only their own data) ----
    if role in ('SUPER ADMIN', 'ADMIN', 'FINANCE'):
        wr_qs = WorkRequest.objects
        wo_qs = WorkOrder.objects
        wcc_qs = WorkOrderCompletion.objects
        inv_qs = Invoice.objects
        pr_qs = PaymentRequisition.objects
    elif role == 'PROCUREMENT AND STORE':
        wr_qs = WorkRequest.objects.filter(request_to=user)
        wo_qs = WorkOrder.objects.filter(owner=user)
        wcc_qs = WorkOrderCompletion.objects.filter(owner=user)
        inv_qs = Invoice.objects.filter(owner=user)
        pr_qs = PaymentRequisition.objects.filter(owner=user)
    elif role == 'REVIEWER':
        wr_qs = WorkRequest.objects.filter(reviewers=user)
        wo_qs = WorkOrder.objects.filter(reviewers=user)
        wcc_qs = WorkOrderCompletion.objects.filter(reviewers=user)
        inv_qs = Invoice.objects.filter(reviewers=user)
        pr_qs = PaymentRequisition.objects.filter(owner=user)
    elif role == 'APPROVER':
        wr_qs = WorkRequest.objects.filter(approver=user)
        wo_qs = WorkOrder.objects.filter(approver=user)
        wcc_qs = WorkOrderCompletion.objects.filter(approver=user)
        inv_qs = Invoice.objects.filter(approver=user)
        pr_qs = PaymentRequisition.objects.filter(request_to=user)
    else:
        wr_qs = WorkRequest.objects.filter(owner=user)
        wo_qs = WorkOrder.objects.filter(owner=user)
        wcc_qs = WorkOrderCompletion.objects.filter(owner=user)
        inv_qs = Invoice.objects.filter(owner=user)
        pr_qs = PaymentRequisition.objects.filter(owner=user)

    # ---- WORK REQUEST: only show what is waiting for THIS role's action ----
    if role in ('SUPER ADMIN', 'ADMIN', 'FINANCE'):
        wr_pending = wr_qs.filter(
            approval_status__in=['Pending Review', 'CP Approved', 'Reviewed']
        ).count()
        wr_pending_label = 'All Active'
    elif role == 'PROCUREMENT AND STORE':
        wr_pending = wr_qs.filter(approval_status='Pending Review').count()
        wr_pending_label = 'Awaiting My Action'
    elif role == 'REVIEWER':
        wr_pending = wr_qs.filter(approval_status='CP Approved').count()
        wr_pending_label = 'Awaiting My Review'
    elif role == 'APPROVER':
        wr_pending = wr_qs.filter(approval_status='Reviewed').count()
        wr_pending_label = 'Awaiting My Approval'
    else:
        wr_pending = wr_qs.filter(
            approval_status__in=['Pending Review', 'CP Approved', 'Reviewed']
        ).count()
        wr_pending_label = 'In Progress'

    wr_approved = wr_qs.filter(approval_status='Fully Approved').count()
    wr_rejected = wr_qs.filter(
        approval_status__in=['Rejected – Vendor Changed', 'Reviewer Rejected', 'Approver Rejected']
    ).count()

    # ---- WORK ORDER ----
    wo_pending = wo_qs.filter(approval_status='Pending').count()
    wo_reviewed = wo_qs.filter(approval_status='Reviewed').count()
    wo_approved = wo_qs.filter(approval_status='Approved').count()
    wo_rejected = wo_qs.filter(approval_status='Rejected').count()
    wo_overdue = wo_qs.filter(
        approval_status='Approved',
        expected_start_date__lt=today,
    ).count()

    if role == 'APPROVER':
        wo_action_count = wo_reviewed
        wo_action_label = 'Awaiting My Approval'
    elif role == 'REVIEWER':
        wo_action_count = wo_pending
        wo_action_label = 'Awaiting My Review'
    else:
        wo_action_count = wo_pending
        wo_action_label = 'New / Pending'

    # ---- WORK COMPLETION CERTIFICATE ----
    wcc_pending = wcc_qs.filter(approval_status='Pending').count()
    wcc_reviewed = wcc_qs.filter(approval_status='Reviewed').count()
    wcc_approved = wcc_qs.filter(approval_status='Approved').count()
    wcc_rejected = wcc_qs.filter(
        approval_status__in=['Reviewer Rejected', 'Approver Rejected']
    ).count()

    if role == 'APPROVER':
        wcc_action_count = wcc_reviewed
        wcc_action_label = 'Awaiting My Approval'
    elif role == 'REVIEWER':
        wcc_action_count = wcc_pending
        wcc_action_label = 'Awaiting My Review'
    else:
        wcc_action_count = wcc_pending
        wcc_action_label = 'New / Pending'

    # ---- INVOICE ----
    inv_pending = inv_qs.filter(approval_status='Pending').count()
    inv_reviewed = inv_qs.filter(approval_status='Reviewed').count()
    inv_approved = inv_qs.filter(approval_status='Approved').count()
    inv_rejected = inv_qs.filter(
        approval_status__in=['Reviewer Rejected', 'Approver Rejected']
    ).count()

    if role == 'APPROVER':
        inv_action_count = inv_reviewed
        inv_action_label = 'Awaiting My Approval'
    elif role == 'REVIEWER':
        inv_action_count = inv_pending
        inv_action_label = 'Awaiting My Review'
    else:
        inv_action_count = inv_pending
        inv_action_label = 'New / Pending'

    # ---- PAYMENT REQUISITION ----
    pr_pending = pr_qs.filter(approval_status='request').count()
    pr_approved = pr_qs.filter(approval_status='approve').count()

    # ---- CHART DATA (last 6 months, global counts) ----
    labels, wr_counts, wo_counts = [], [], []
    for i in range(5, -1, -1):
        year, month = today.year, today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = today.replace(year=year, month=month, day=1)
        month_end = (
            today.replace(year=year + 1, month=1, day=1) - timedelta(days=1)
            if month == 12
            else today.replace(year=year, month=month + 1, day=1) - timedelta(days=1)
        )
        labels.append(month_start.strftime('%b %Y'))
        wr_counts.append(
            WorkRequest.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end,
            ).count()
        )
        wo_counts.append(
            WorkOrder.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end,
            ).count()
        )

    # ---- USER INFO ----
    user_name = (
        getattr(user, 'name', None)
        or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        or user.email
    )
    user_role_display = getattr(user, 'roles', 'User') or 'User'

    return {
        # API-shaped payload (used by DashboardAPIView)
        'workspace_title': 'Alpha CMMS Dashboard',
        'current_date': today.strftime('%A, %B %d, %Y'),
        'user_info': {'name': user_name, 'role': user_role_display},
        'navigation_tabs': [
            'WORK REQUEST', 'WORK ORDER', 'WORK COMPLETION', 'INVOICES', 'PAYMENT REQUISITION',
        ],
        'summary_cards': {
            'work_request': [
                {'label': wr_pending_label, 'count': wr_pending, 'icon': 'file-plus', 'color': 'blue'},
                {'label': 'Approved', 'count': wr_approved, 'icon': 'check-circle', 'color': 'green'},
                {'label': 'Rejected', 'count': wr_rejected, 'icon': 'x-circle', 'color': 'red'},
            ],
            'work_order': [
                {'label': wo_action_label, 'count': wo_action_count, 'icon': 'file-plus', 'color': 'blue'},
                {'label': 'Reviewed', 'count': wo_reviewed, 'icon': 'check-circle', 'color': 'teal'},
                {'label': 'Approved', 'count': wo_approved, 'icon': 'check-circle', 'color': 'green'},
                {'label': 'Rejected', 'count': wo_rejected, 'icon': 'x-circle', 'color': 'red'},
                {'label': 'Overdue', 'count': wo_overdue, 'icon': 'alert-triangle', 'color': 'orange'},
            ],
            'work_completion': [
                {'label': wcc_action_label, 'count': wcc_action_count, 'icon': 'file-plus', 'color': 'blue'},
                {'label': 'Reviewed', 'count': wcc_reviewed, 'icon': 'check-circle', 'color': 'teal'},
                {'label': 'Approved', 'count': wcc_approved, 'icon': 'check-circle', 'color': 'green'},
                {'label': 'Rejected', 'count': wcc_rejected, 'icon': 'x-circle', 'color': 'red'},
            ],
            'invoices': [
                {'label': inv_action_label, 'count': inv_action_count, 'icon': 'file-plus', 'color': 'blue'},
                {'label': 'Reviewed', 'count': inv_reviewed, 'icon': 'check-circle', 'color': 'teal'},
                {'label': 'Approved', 'count': inv_approved, 'icon': 'check-circle', 'color': 'green'},
                {'label': 'Rejected', 'count': inv_rejected, 'icon': 'x-circle', 'color': 'red'},
            ],
            'payment_requisition': [
                {'label': 'Pending Approval', 'count': pr_pending, 'icon': 'file-plus', 'color': 'blue'},
                {'label': 'Approved', 'count': pr_approved, 'icon': 'check-circle', 'color': 'green'},
            ],
        },
        'chart_data': {
            'labels': labels,
            'datasets': [
                {'label': 'Work Requests', 'data': wr_counts, 'backgroundColor': 'rgba(59,130,246,0.6)'},
                {'label': 'Work Orders', 'data': wo_counts, 'backgroundColor': 'rgba(16,185,129,0.6)'},
            ],
            'current_year': today.year,
            'available_years': [today.year],
        },
        # Flat template variables (used directly in index.html)
        'user_name': user_name,
        'user_role_display': user_role_display,
        'wr_pending': wr_pending,
        'wr_pending_label': wr_pending_label,
        'wr_approved': wr_approved,
        'wr_rejected': wr_rejected,
        'wo_action_count': wo_action_count,
        'wo_action_label': wo_action_label,
        'wo_reviewed': wo_reviewed,
        'wo_approved': wo_approved,
        'wo_rejected': wo_rejected,
        'wo_overdue': wo_overdue,
        'wcc_action_count': wcc_action_count,
        'wcc_action_label': wcc_action_label,
        'wcc_reviewed': wcc_reviewed,
        'wcc_approved': wcc_approved,
        'wcc_rejected': wcc_rejected,
        'inv_action_count': inv_action_count,
        'inv_action_label': inv_action_label,
        'inv_reviewed': inv_reviewed,
        'inv_approved': inv_approved,
        'inv_rejected': inv_rejected,
    }
