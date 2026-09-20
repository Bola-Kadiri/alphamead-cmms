"""
Report module analytics engine.

Unlike report.services (which backs the row-level User Facility Report),
this module produces aggregate, org-wide CMMS reporting: status
breakdowns, backlog/aging, cycle times, financial totals, trends, and a
generated list of plain-language insights — the kind of reporting a
standard CMMS analytics dashboard ships, as opposed to a flat table dump.

Every number here is computed from fields that actually exist on the
models today. Nothing is fabricated or estimated from a field the system
doesn't track (e.g. there is no SLA-breach flag anywhere in this codebase,
so this module reports backlog age and approval cycle time instead of a
"SLA compliance %" it has no data to back up).
"""
from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from asset_inventory.models import Asset, Inventory, ItemRequest
from procurement.models import (
    GoodsReceivedNote,
    PurchaseOrder,
    RequestForQuotation,
    VendorContract,
)
from work.models import PPM, Invoice, PaymentRequisition, WorkOrder, WorkOrderCompletion, WorkRequest

WORK_REQUEST_REJECTED = ['Rejected – Vendor Changed', 'Reviewer Rejected', 'Approver Rejected']
WORK_REQUEST_OPEN = ['Pending Review', 'CP Approved', 'Reviewed']
WORK_ORDER_REJECTED = ['Rejected']
WCC_REJECTED = ['Reviewer Rejected', 'Approver Rejected']
INVOICE_REJECTED = ['Reviewer Rejected', 'Approver Rejected']

STALE_THRESHOLD_DAYS = 7
CONTRACT_EXPIRING_SOON_DAYS = 30


def _status_breakdown(qs, field):
    """{status_value: count} for every distinct value present, in one query."""
    rows = qs.values(field).annotate(count=Count('id')).order_by('-count')
    return {(row[field] or 'Unspecified'): row['count'] for row in rows}


def _weekly_trend(qs, date_field='created_at', weeks=8):
    since = timezone.now() - timedelta(weeks=weeks)
    rows = (
        qs.filter(**{f'{date_field}__gte': since})
        .annotate(week=TruncWeek(date_field))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )
    return [{'week': row['week'].date().isoformat(), 'count': row['count']} for row in rows if row['week']]


def _avg_duration_days(qs, start_field, end_field):
    """Average calendar days between two datetime/date fields, or None if no rows qualify."""
    result = (
        qs.exclude(**{f'{end_field}__isnull': True})
        .exclude(**{f'{start_field}__isnull': True})
        .annotate(_span=ExpressionWrapper(F(end_field) - F(start_field), output_field=DurationField()))
        .aggregate(avg=Avg('_span'))
    )
    avg = result['avg']
    return round(avg.total_seconds() / 86400, 1) if avg else None


def _backlog_aging(qs, open_statuses, status_field='approval_status'):
    """Open-record count, average age in days, and count stale beyond the threshold."""
    now = timezone.now()
    open_qs = qs.filter(**{f'{status_field}__in': open_statuses})
    aged = open_qs.annotate(_age=ExpressionWrapper(now - F('created_at'), output_field=DurationField()))
    avg_age = aged.aggregate(avg=Avg('_age'))['avg']
    return {
        'backlog': open_qs.count(),
        'avg_backlog_age_days': round(avg_age.total_seconds() / 86400, 1) if avg_age else None,
        'stale_backlog_count': aged.filter(_age__gte=timedelta(days=STALE_THRESHOLD_DAYS)).count(),
    }


def get_work_request_analytics():
    qs = WorkRequest.objects.all()
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'approval_status'),
        'by_priority': _status_breakdown(qs, 'priority'),
        **_backlog_aging(qs, WORK_REQUEST_OPEN),
        'avg_approval_cycle_days': _avg_duration_days(
            qs.filter(approval_status='Fully Approved'), 'created_at', 'fully_approved_at'
        ),
        'rejected': qs.filter(approval_status__in=WORK_REQUEST_REJECTED).count(),
        'top_facilities': list(
            qs.exclude(facility__isnull=True)
            .values('facility__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        ),
        'trend': _weekly_trend(qs),
    }


def get_work_order_analytics():
    qs = WorkOrder.objects.all()
    today = timezone.now().date()
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'approval_status'),
        'by_priority': _status_breakdown(qs, 'priority'),
        **_backlog_aging(qs, ['Pending', 'Reviewed']),
        'rejected': qs.filter(approval_status__in=WORK_ORDER_REJECTED).count(),
        'overdue': qs.filter(approval_status='Approved', expected_start_date__lt=today).count(),
        'trend': _weekly_trend(qs),
    }


def get_completion_analytics():
    qs = WorkOrderCompletion.objects.all()
    work_orders_total = WorkOrder.objects.count()
    completed_work_order_ids = qs.filter(approval_status='Approved').values('work_order_id').distinct().count()
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'approval_status'),
        'rejected': qs.filter(approval_status__in=WCC_REJECTED).count(),
        # Of all work orders raised, how many have an approved completion
        # certificate on file — a real, standard CMMS "completion rate".
        'completion_rate_pct': (
            round(completed_work_order_ids / work_orders_total * 100, 1) if work_orders_total else None
        ),
    }


def get_invoice_analytics():
    qs = Invoice.objects.all()
    today = timezone.now().date()
    # Invoice.status is free text with no fixed "Paid" value anywhere in
    # this codebase, and there's no payment-linkage field on Invoice
    # itself (settlement lives on the separate PaymentRequisition model).
    # "Overdue" here means: due date has passed and the invoice hasn't
    # even reached Approved yet — the honest signal this field set gives.
    overdue_qs = qs.filter(due_date__lt=today).exclude(approval_status='Approved')
    totals = qs.aggregate(total_amount=Sum('total_amount'))
    overdue_totals = overdue_qs.aggregate(total_amount=Sum('total_amount'))
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'status'),
        'by_approval_status': _status_breakdown(qs, 'approval_status'),
        'rejected': qs.filter(approval_status__in=INVOICE_REJECTED).count(),
        'total_amount': totals['total_amount'] or 0,
        'overdue_count': overdue_qs.count(),
        'overdue_amount': overdue_totals['total_amount'] or 0,
        'trend': _weekly_trend(qs, date_field='created_at'),
    }


def get_payment_requisition_analytics():
    qs = PaymentRequisition.objects.all()
    totals = qs.aggregate(total_amount=Sum('expected_payment_amount'))
    pending_qs = qs.exclude(approval_status='approve')
    pending_totals = pending_qs.aggregate(total_amount=Sum('expected_payment_amount'))
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'approval_status'),
        'total_amount': totals['total_amount'] or 0,
        'pending_count': pending_qs.count(),
        'pending_amount': pending_totals['total_amount'] or 0,
    }


def get_ppm_analytics():
    qs = PPM.objects.all()
    return {
        'total': qs.count(),
        'by_status': _status_breakdown(qs, 'approval_status'),
        'by_frequency_unit': _status_breakdown(qs, 'frequency_unit'),
        'assets_covered': Asset.objects.filter(ppms__isnull=False).distinct().count(),
        'facilities_covered': (
            qs.values('facilities__id').exclude(facilities__isnull=True).distinct().count()
        ),
    }


def get_procurement_analytics():
    rfq_qs = RequestForQuotation.objects.all()
    po_qs = PurchaseOrder.objects.all()
    grn_qs = GoodsReceivedNote.objects.all()
    contract_qs = VendorContract.objects.all()
    today = timezone.now().date()

    pos_with_grn = grn_qs.values('purchase_order_id').distinct().count()
    po_total = po_qs.count()

    expiring_soon = contract_qs.filter(
        end_date__gte=today, end_date__lte=today + timedelta(days=CONTRACT_EXPIRING_SOON_DAYS)
    ).count()
    expired = contract_qs.filter(end_date__lt=today).count()
    active = contract_qs.filter(start_date__lte=today, end_date__gte=today).count()
    contract_value = contract_qs.aggregate(total=Sum('proposed_value'))['total'] or 0

    return {
        'rfq': {'total': rfq_qs.count(), 'by_type': _status_breakdown(rfq_qs, 'type')},
        'purchase_orders': {
            'total': po_total,
            'by_status': _status_breakdown(po_qs, 'status'),
            # % of POs that have at least one Goods Received Note logged
            # against them — a standard procurement "fulfillment rate".
            'fulfillment_rate_pct': round(pos_with_grn / po_total * 100, 1) if po_total else None,
        },
        'goods_received_notes': {'total': grn_qs.count()},
        'vendor_contracts': {
            'total': contract_qs.count(),
            'active': active,
            'expired': expired,
            'expiring_within_30_days': expiring_soon,
            'total_contract_value': contract_value,
        },
    }


def get_asset_analytics():
    asset_qs = Asset.objects.all()
    inventory_qs = Inventory.objects.all()
    item_request_qs = ItemRequest.objects.all()

    low_stock = inventory_qs.filter(quantity__lte=F('reorder_level'))

    return {
        'assets': {
            'total': asset_qs.count(),
            'by_condition': _status_breakdown(asset_qs, 'condition'),
        },
        'inventory': {
            'total': inventory_qs.count(),
            'by_status': _status_breakdown(inventory_qs, 'status'),
            'low_stock_count': low_stock.count(),
            'low_stock_items': list(
                low_stock.values('tag', 'part_no', 'quantity', 'reorder_level')[:10]
            ),
        },
        'item_requests': {
            'total': item_request_qs.count(),
            'by_status': _status_breakdown(item_request_qs, 'status'),
        },
    }


def generate_insights(sections):
    """
    Turn the raw aggregates into a short, prioritised list of
    plain-language observations — the part that makes this a reporting
    *dashboard* rather than a set of tables someone still has to read
    and interpret themselves.
    """
    insights = []
    wr, wo, wcc, inv, ppm, proc, assets = (
        sections['work_requests'], sections['work_orders'], sections['completions'],
        sections['invoices'], sections['ppm'], sections['procurement'], sections['assets'],
    )

    if wr['stale_backlog_count']:
        insights.append({
            'level': 'warning',
            'message': (
                f"{wr['stale_backlog_count']} work request(s) have sat unapproved for over "
                f"{STALE_THRESHOLD_DAYS} days (avg backlog age: {wr['avg_backlog_age_days']} days)."
            ),
        })

    if wo['overdue']:
        insights.append({
            'level': 'critical',
            'message': f"{wo['overdue']} approved work order(s) are past their expected start date.",
        })

    if inv['overdue_count']:
        insights.append({
            'level': 'critical',
            'message': (
                f"{inv['overdue_count']} invoice(s) are overdue, totaling "
                f"{inv['overdue_amount']:,.2f}."
            ),
        })

    if sections['payment_requisitions']['pending_count']:
        pr = sections['payment_requisitions']
        insights.append({
            'level': 'info',
            'message': f"{pr['pending_count']} payment requisition(s) awaiting approval, totaling {pr['pending_amount']:,.2f}.",
        })

    if proc['vendor_contracts']['expiring_within_30_days']:
        insights.append({
            'level': 'warning',
            'message': f"{proc['vendor_contracts']['expiring_within_30_days']} vendor contract(s) expire within {CONTRACT_EXPIRING_SOON_DAYS} days.",
        })

    if proc['vendor_contracts']['expired']:
        insights.append({
            'level': 'warning',
            'message': f"{proc['vendor_contracts']['expired']} vendor contract(s) are past their end date and still on file as active.",
        })

    if proc['purchase_orders']['fulfillment_rate_pct'] is not None and proc['purchase_orders']['fulfillment_rate_pct'] < 50:
        insights.append({
            'level': 'info',
            'message': f"Only {proc['purchase_orders']['fulfillment_rate_pct']}% of purchase orders have a goods received note logged against them.",
        })

    if assets['inventory']['low_stock_count']:
        insights.append({
            'level': 'warning',
            'message': f"{assets['inventory']['low_stock_count']} inventory item(s) are at or below their reorder level.",
        })

    if wcc['completion_rate_pct'] is not None and wcc['completion_rate_pct'] < 50:
        insights.append({
            'level': 'info',
            'message': f"Only {wcc['completion_rate_pct']}% of work orders have an approved completion certificate.",
        })

    if wr['avg_approval_cycle_days'] is not None:
        insights.append({
            'level': 'info',
            'message': f"Work requests take an average of {wr['avg_approval_cycle_days']} days from raised to fully approved.",
        })

    if not insights:
        insights.append({'level': 'info', 'message': 'No urgent issues detected across the system right now.'})

    severity_rank = {'critical': 0, 'warning': 1, 'info': 2}
    insights.sort(key=lambda i: severity_rank.get(i['level'], 3))
    return insights


def get_dashboard_analytics():
    sections = {
        'work_requests': get_work_request_analytics(),
        'work_orders': get_work_order_analytics(),
        'completions': get_completion_analytics(),
        'invoices': get_invoice_analytics(),
        'payment_requisitions': get_payment_requisition_analytics(),
        'ppm': get_ppm_analytics(),
        'procurement': get_procurement_analytics(),
        'assets': get_asset_analytics(),
    }
    sections['generated_at'] = timezone.now().isoformat()
    sections['insights'] = generate_insights(sections)
    return sections
