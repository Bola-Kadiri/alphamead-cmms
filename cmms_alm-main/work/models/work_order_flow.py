"""
Stage 2 (Work Order) of the five-stage flow:

  Procurement & Store (team) prices a client-approved Work Request → Category Manager
  (named) reviews scope and price, or sends back → Client (named) approves the price,
  which commits the spend, or rejects and the job ends → the vendor's staff accept the job.

The client always approves the price; that cannot be switched off. The Stage 2 time
limit runs from the client's approval of the Work Request.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from work.models import work_request_flow as stage1
from work.models.action_log import history
from work.models.approval_matrix import acting_for, team_members
from work.models.flow_rules import ActionRefused, perform_action
from work.models.time_limits import step_timing
from work.models.work_order import WorkOrder, WorkOrderQuoteLine
from work.models.work_request import WorkRequest

STAGE = 'work_order'

WAITING_ON = {
    'Pricing': 'procurement',
    'Sent Back': 'procurement',
    'Awaiting Review': 'approver',
    'Awaiting Client': 'client_rep',
}
STEP_LABELS = {
    'procurement': 'Procurement & Store',
    'approver': 'Category Manager',
    'client_rep': 'Client',
    'contractor': 'Contractor',
}


def _require(wo, *statuses):
    if wo.flow != WorkOrder.FIVE_STAGE:
        raise ActionRefused("This work order follows the original flow.")
    if wo.approval_status not in statuses:
        raise ActionRefused(f"This work order is {wo.approval_status}; that action is not available now.")


def _set_status(wo, status, **extra):
    wo.approval_status = status
    fields = ['approval_status', 'updated_at']
    for name, value in extra.items():
        setattr(wo, name, value)
        fields.append(name)
    wo.save(update_fields=fields)


def _procurement_check(user, facility):
    if not acting_for(user, 'procurement', facility)[0]:
        raise ActionRefused("Only Procurement & Store can price a work order.")


# ── the queue and starting a work order ──────────────────────────────────────

def ready_requests():
    """Client-approved five-stage Work Requests that have no Work Order yet, oldest first."""
    return (WorkRequest.objects.filter(flow=WorkRequest.FIVE_STAGE, approval_status='Fully Approved')
            .exclude(derived_work_orders__flow=WorkOrder.FIVE_STAGE)
            .select_related('facility', 'category').order_by('fully_approved_at'))


@transaction.atomic
def start(wr, user):
    """Open a Work Order for pricing from a client-approved Work Request."""
    if wr.flow != WorkRequest.FIVE_STAGE or wr.approval_status != 'Fully Approved':
        raise ActionRefused("Only a client-approved Work Request can become a Work Order.")
    _procurement_check(user, wr.facility)
    if wr.derived_work_orders.filter(flow=WorkOrder.FIVE_STAGE).exists():
        raise ActionRefused("This Work Request already has a Work Order.")
    return WorkOrder.objects.create(
        flow=WorkOrder.FIVE_STAGE, type='FROM-WORK-REQUEST', source_work_request=wr,
        requester=wr.requester, owner=user, facility=wr.facility, building=wr.building,
        category=wr.category, subcategory=wr.subcategory, department=wr.department, asset=wr.asset,
        description=wr.description, priority=wr.priority or 'Medium', currency='NGN', approval_status='Pricing',
    )


# ── pricing ──────────────────────────────────────────────────────────────────

def _decimal(value, label):
    try:
        number = Decimal(str(value))
    except Exception:
        raise ActionRefused(f"{label} must be a number.")
    if number < 0:
        raise ActionRefused(f"{label} cannot be negative.")
    return number


@transaction.atomic
def save_pricing(wo, user, *, lines=None, vendor=None, quotation_reference=None, po_number=None,
                 expected_start_date=None, files=()):
    """Save what Procurement & Store has so far. Checked for completeness only on submit."""
    _require(wo, 'Pricing', 'Sent Back')
    _procurement_check(user, wo.facility)
    if lines is not None:
        clean = []
        for index, line in enumerate(lines, start=1):
            description = (line.get('description') or '').strip()
            if not description:
                raise ActionRefused(f"Line {index}: enter a description.")
            quantity = _decimal(line.get('quantity', 1), f"Line {index} quantity")
            if quantity <= 0:
                raise ActionRefused(f"Line {index}: quantity must be more than 0.")
            clean.append(WorkOrderQuoteLine(
                work_order=wo, description=description, quantity=quantity,
                unit_cost_vendor=_decimal(line.get('unit_cost_vendor'), f"Line {index} vendor cost"),
                unit_cost_client=_decimal(line.get('unit_cost_client'), f"Line {index} client price"),
            ))
        wo.quote_lines.all().delete()
        WorkOrderQuoteLine.objects.bulk_create(clean)
        wo.cost = sum((l.total_vendor for l in clean), Decimal('0'))
        wo.client_price = sum((l.total_client for l in clean), Decimal('0'))
    if vendor is not None:
        wo.vendor = vendor
    if quotation_reference is not None:
        wo.quotation_reference = quotation_reference.strip()
    if po_number is not None:
        wo.po_number = po_number.strip()
    if expected_start_date is not None:
        wo.expected_start_date = expected_start_date or None
    wo.save()
    if files:
        from django.contrib.contenttypes.models import ContentType
        from utils.models import FileAttachment
        content_type = ContentType.objects.get_for_model(wo)
        for upload in files:
            FileAttachment.objects.create(content_type=content_type, object_id=wo.pk, file=upload)


def pricing_problems(wo):
    problems = []
    if wo.vendor_id is None:
        problems.append("Choose the vendor.")
    elif not wo.vendor.has_bank_details:
        problems.append(f"{wo.vendor.name} has no bank details, so cannot be paid. Ask the Super Admin to add them.")
    if not wo.quote_lines.exists():
        problems.append("Add at least one quote line.")
    elif (wo.client_price or 0) < (wo.cost or 0):
        problems.append("The client price cannot be lower than the vendor cost.")
    if not wo.quotation_reference:
        problems.append("Enter the quotation reference.")
    if not wo.po_number:
        problems.append("Enter the PO number.")
    if not wo.expected_start_date:
        problems.append("Enter the expected start date.")
    if not wo.resources.exists():
        problems.append("Attach the vendor's quotation.")
    return problems


# ── actions ──────────────────────────────────────────────────────────────────

@transaction.atomic
def submit(wo, user):
    _require(wo, 'Pricing', 'Sent Back')
    problems = pricing_problems(wo)
    if problems:
        raise ActionRefused(' '.join(problems))
    action = 'raised' if wo.approval_status == 'Pricing' else 'resubmitted'
    perform_action(wo, STAGE, 'procurement', action, user, facility=wo.facility)
    _set_status(wo, 'Awaiting Review')
    _tell_next(wo)


@transaction.atomic
def review(wo, user, signature, note=''):
    _require(wo, 'Awaiting Review')
    perform_action(wo, STAGE, 'approver', 'reviewed', user, facility=wo.facility, signature=signature, reason=note)
    _set_status(wo, 'Awaiting Client', is_reviewed=True)
    _tell_next(wo)


@transaction.atomic
def send_back(wo, user, reason):
    _require(wo, 'Awaiting Review')
    perform_action(wo, STAGE, 'approver', 'sent_back', user, facility=wo.facility, reason=reason)
    _set_status(wo, 'Sent Back')
    _tell_next(wo, reason=reason)


@transaction.atomic
def client_approve(wo, user, signature, confirmed):
    _require(wo, 'Awaiting Client')
    if not confirmed:
        raise ActionRefused("Tick to confirm the client agrees to pay this price.")
    perform_action(wo, STAGE, 'client_rep', 'approved', user, facility=wo.facility, signature=signature)
    _set_status(wo, 'Approved', is_approved=True, approved=True, digital_signature=signature.strip())
    _tell_next(wo)


@transaction.atomic
def client_reject(wo, user, reason):
    _require(wo, 'Awaiting Client')
    perform_action(wo, STAGE, 'client_rep', 'rejected', user, facility=wo.facility, reason=reason)
    _set_status(wo, 'Client Rejected')
    wr = wo.source_work_request
    if wr is not None:
        wr.approval_status = 'Client Rejected'
        wr.save(update_fields=['approval_status', 'updated_at'])
    _tell_next(wo, reason=reason)


@transaction.atomic
def accept(wo, user, start_date, technician):
    _require(wo, 'Approved')
    if wo.accepted_at:
        raise ActionRefused("This job has already been accepted.")
    if not start_date:
        raise ActionRefused("Confirm the start date.")
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
        if start_date is None:
            raise ActionRefused("Enter the start date as a date, e.g. 2026-10-28.")
    if not (technician or '').strip():
        raise ActionRefused("Name the technician who will do the work.")
    perform_action(wo, STAGE, 'contractor', 'accepted', user, facility=wo.facility, vendor=wo.vendor)
    wo.accepted_at = timezone.now()
    wo.accepted_by = user
    wo.confirmed_start_date = start_date
    wo.contractor_technician = technician.strip()
    wo.save(update_fields=['accepted_at', 'accepted_by', 'confirmed_start_date', 'contractor_technician', 'updated_at'])
    _tell_accepted(wo)


# ── who sees and acts ────────────────────────────────────────────────────────

def people_for(wo, slot):
    if slot == 'procurement':
        return list(team_members('procurement'))
    if slot == 'requester':
        return list(team_members('requester', wo.facility))
    if slot == 'contractor':
        if wo.vendor_id is None:
            return []
        return list(get_user_model().objects.filter(roles='CONTRACTOR', vendor=wo.vendor, is_active=True))
    return stage1.people_for(wo, slot)


def available_actions(wo, user):
    if wo.flow != WorkOrder.FIVE_STAGE:
        return []
    status = wo.approval_status
    if status == 'Approved':
        allowed = not wo.accepted_at and acting_for(user, 'contractor', wo.facility, vendor=wo.vendor)[0]
        return ['accept'] if allowed else []
    slot = WAITING_ON.get(status)
    if slot is None or not acting_for(user, slot, wo.facility)[0]:
        return []
    if slot == 'procurement':
        return ['edit_pricing', 'submit']
    if history(wo).filter(actor=user, action__in=['raised', 'resubmitted', 'reviewed']).exists():
        return []
    return ['review', 'send_back'] if slot == 'approver' else ['approve', 'reject']


def timing(wo):
    if wo.approval_status in ('Approved', 'Client Rejected'):
        return None
    wr = wo.source_work_request
    started = wr.fully_approved_at if wr and wr.fully_approved_at else wo.created_at
    client = wo.facility.client if wo.facility_id else None
    return {**step_timing(STAGE, started, client), 'started_at': started}


def price_check(wo, limit=3):
    """Recent approved jobs of the same kind, so the Category Manager can compare prices."""
    if wo.subcategory_id is None:
        return []
    similar = (WorkOrder.objects.filter(subcategory_id=wo.subcategory_id, approval_status='Approved')
               .exclude(pk=wo.pk).select_related('facility', 'vendor').order_by('-updated_at')[:limit])
    return [{'number': o.work_order_number, 'facility': o.facility.name if o.facility_id else None,
             'vendor': o.vendor.name if o.vendor_id else None,
             'client_price': str(o.client_price) if o.client_price is not None else None,
             'vendor_cost': str(o.cost) if o.cost is not None else None}
            for o in similar]


def my_tasks(user):
    """Five-stage work (Stage 2) waiting on `user`: requests to price, work orders to act on, jobs to accept."""
    tasks = []
    if user.roles == 'PROCUREMENT AND STORE' and user.is_active:
        for wr in ready_requests():
            tasks.append({'kind': 'work_order_to_raise', 'request': wr, 'step': 'procurement',
                          'timing': {**step_timing(STAGE, wr.fully_approved_at, wr.facility.client if wr.facility_id else None)}
                          if wr.fully_approved_at else None})
    candidates = (WorkOrder.objects.filter(flow=WorkOrder.FIVE_STAGE)
                  .filter(approval_status__in=[*WAITING_ON, 'Approved'])
                  .select_related('facility', 'facility__client', 'vendor', 'source_work_request')
                  .order_by('updated_at'))
    for wo in candidates:
        actions = available_actions(wo, user)
        if not actions:
            continue
        slot = 'contractor' if wo.approval_status == 'Approved' else WAITING_ON[wo.approval_status]
        on_behalf_of = acting_for(user, slot, wo.facility, vendor=wo.vendor)[1]
        tasks.append({'kind': 'work_order', 'order': wo, 'step': slot, 'on_behalf_of': on_behalf_of, 'timing': timing(wo)})
    return tasks


# ── telling people ───────────────────────────────────────────────────────────

MESSAGES = {
    'Awaiting Review': ("Work Order to review", "A Work Order is waiting for your review of scope and price."),
    'Sent Back': ("Work Order sent back", "A Work Order was sent back to Procurement & Store. Please re-price it and resubmit."),
    'Awaiting Client': ("Price awaiting your approval", "A Work Order price is waiting for your approval."),
    'Approved': ("Work Order approved", "The client approved the price. The contractor has been asked to accept the job."),
    'Client Rejected': ("Work Order rejected by the client", "The client rejected the price. The job has ended."),
}


def _recipients(wo):
    status = wo.approval_status
    if status in WAITING_ON:
        return people_for(wo, WAITING_ON[status])
    if status == 'Approved':
        return people_for(wo, 'contractor') + people_for(wo, 'requester') + people_for(wo, 'procurement')
    if status == 'Client Rejected':
        return people_for(wo, 'procurement') + people_for(wo, 'requester') + people_for(wo, 'approver')
    return []


def _send(wo, recipients, headline, message, reason=''):
    from work.utils.email_service import create_in_app_notifications, send_notification_email

    recipients = list({u.pk: u for u in recipients if u.is_active}.values())

    def _go():
        create_in_app_notifications(recipients, title=f"{headline} · {wo.work_order_number}",
                                    message=message, notification_type='WORK_ORDER', object_id=wo.pk)
        send_notification_email(
            subject=f"[AlphaCMMS] {headline} · {wo.work_order_number}",
            template='emails/work_order_flow.html',
            context={'instance': wo, 'headline': headline, 'message': message, 'reason': reason},
            recipient_list=[u.email for u in recipients if u.email],
        )

    transaction.on_commit(_go)


def _tell_next(wo, reason=''):
    headline, message = MESSAGES[wo.approval_status]
    _send(wo, _recipients(wo), headline, message, reason)


def _tell_accepted(wo):
    message = f"The contractor accepted the job and will start on {wo.confirmed_start_date:%d %b %Y}."
    _send(wo, people_for(wo, 'requester') + people_for(wo, 'procurement'), "Job accepted by the contractor", message)
