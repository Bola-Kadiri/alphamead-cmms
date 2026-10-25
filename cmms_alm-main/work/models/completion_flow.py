"""
Stage 3 (Work Completion Certificate) of the five-stage flow:

  Site Managers (team, at the facility) raise it with the evidence → Central Operations
  (team) verify the work on site, or send back → Category Manager (named) approves, or
  sends back. A send-back returns it to the Site Managers; after they resubmit, the
  check starts again at Central Operations.

Approval is blocked until the before photo, after photo and signed checklist are all
attached. Approving tells the contractor they can invoice.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from work.models import work_request_flow as stage1
from work.models.action_log import history
from work.models.approval_matrix import acting_for, team_members
from work.models.flow_rules import ActionRefused, perform_action
from work.models.time_limits import step_timing
from work.models.work_order import WorkOrder
from work.models.work_order_completion import WccEvidence, WorkOrderCompletion

STAGE = 'wcc'

WAITING_ON = {
    'Draft': 'requester',
    'Sent Back': 'requester',
    'Awaiting Verification': 'central_operation',
    'Awaiting Approval': 'approver',
}
STEP_LABELS = {
    'requester': 'Site Manager',
    'central_operation': 'Central Operations',
    'approver': 'Category Manager',
}
REQUIRED_EVIDENCE = [kind for kind, _ in WccEvidence.KIND_CHOICES]


def _require(wcc, *statuses):
    if wcc.flow != WorkOrderCompletion.FIVE_STAGE:
        raise ActionRefused("This certificate follows the original flow.")
    if wcc.approval_status not in statuses:
        raise ActionRefused(f"This certificate is {wcc.approval_status}; that action is not available now.")


def _set_status(wcc, status, **extra):
    wcc.approval_status = status
    fields = ['approval_status', 'updated_at']
    for name, value in extra.items():
        setattr(wcc, name, value)
        fields.append(name)
    wcc.save(update_fields=fields)


def _site_manager_check(user, facility):
    if not acting_for(user, 'requester', facility)[0]:
        raise ActionRefused("Only a Site Manager at this facility can prepare the certificate.")


def _when(value, label):
    if value in (None, ''):
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else value
    if parsed is None:
        raise ActionRefused(f"Enter the {label} as a date and time.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


# ── raising ──────────────────────────────────────────────────────────────────

@transaction.atomic
def start(wo, user):
    """Open a certificate for a client-approved five-stage Work Order."""
    if wo.flow != WorkOrder.FIVE_STAGE or wo.approval_status != 'Approved':
        raise ActionRefused("A certificate can only be raised for a Work Order whose price the client approved.")
    _site_manager_check(user, wo.facility)
    active = wo.completions.filter(approval_status__in=WorkOrderCompletion.ACTIVE_STATUSES).first()
    if active:
        raise ActionRefused(f"This Work Order already has a certificate (WCC-{active.wcc_number}).")
    return WorkOrderCompletion.objects.create(work_order=wo, owner=user, flow=WorkOrderCompletion.FIVE_STAGE,
                                              approval_status='Draft', technician=wo.contractor_technician or '')


@transaction.atomic
def save_details(wcc, user, *, started_at=None, finished_at=None, technician=None, vendor_rating=None,
                 completion_notes=None):
    _require(wcc, 'Draft', 'Sent Back')
    _site_manager_check(user, wcc.work_order.facility)
    if started_at is not None:
        wcc.started_at = _when(started_at, 'start')
    if finished_at is not None:
        wcc.finished_at = _when(finished_at, 'finish')
    if technician is not None:
        wcc.technician = technician.strip()
    if vendor_rating not in (None, ''):
        try:
            rating = int(vendor_rating)
        except (TypeError, ValueError):
            raise ActionRefused("Rate the vendor from 1 to 5.")
        if not 1 <= rating <= 5:
            raise ActionRefused("Rate the vendor from 1 to 5.")
        wcc.vendor_rating = rating
    if completion_notes is not None:
        wcc.completion_notes = completion_notes.strip()
    wcc.save()


@transaction.atomic
def add_evidence(wcc, user, kind, upload):
    _require(wcc, 'Draft', 'Sent Back')
    _site_manager_check(user, wcc.work_order.facility)
    if kind not in REQUIRED_EVIDENCE:
        raise ActionRefused("Choose what this file is: before photo, after photo or signed checklist.")
    if upload is None:
        raise ActionRefused("Choose a file to upload.")
    WccEvidence.objects.filter(completion=wcc, kind=kind).delete()  # a new upload replaces the old one
    WccEvidence.objects.create(completion=wcc, kind=kind, file=upload, uploaded_by=user)


def problems(wcc):
    found = []
    if not wcc.started_at:
        found.append("Enter when the work started.")
    if not wcc.finished_at:
        found.append("Enter when the work finished.")
    if wcc.started_at and wcc.finished_at:
        if wcc.finished_at <= wcc.started_at:
            found.append("The finish time must be after the start time.")
        if wcc.finished_at > timezone.now():
            found.append("The finish time cannot be in the future.")
    if not wcc.technician:
        found.append("Name the technician.")
    if not wcc.vendor_rating:
        found.append("Rate the vendor.")
    if not wcc.completion_notes:
        found.append("Add completion notes.")
    attached = set(wcc.evidence.values_list('kind', flat=True))
    for kind, label in WccEvidence.KIND_CHOICES:
        if kind not in attached:
            found.append(f"Attach the {label.lower()}.")
    return found


# ── actions ──────────────────────────────────────────────────────────────────

@transaction.atomic
def submit(wcc, user):
    _require(wcc, 'Draft', 'Sent Back')
    found = problems(wcc)
    if found:
        raise ActionRefused(' '.join(found))
    action = 'raised' if wcc.approval_status == 'Draft' else 'resubmitted'
    perform_action(wcc, STAGE, 'requester', action, user, facility=wcc.work_order.facility)
    _set_status(wcc, 'Awaiting Verification')
    _tell_next(wcc)


@transaction.atomic
def verify(wcc, user, signature, site_visit_date, note=''):
    _require(wcc, 'Awaiting Verification')
    visited = parse_date(site_visit_date) if isinstance(site_visit_date, str) else site_visit_date
    if visited is None:
        raise ActionRefused("Enter the date you checked the work on site.")
    if visited > timezone.localdate():
        raise ActionRefused("The site visit date cannot be in the future.")
    perform_action(wcc, STAGE, 'central_operation', 'reviewed', user, facility=wcc.work_order.facility,
                   signature=signature, reason=note)
    _set_status(wcc, 'Awaiting Approval', is_reviewed=True, site_visit_date=visited)
    _tell_next(wcc)


@transaction.atomic
def send_back(wcc, user, reason):
    _require(wcc, 'Awaiting Verification', 'Awaiting Approval')
    slot = WAITING_ON[wcc.approval_status]
    perform_action(wcc, STAGE, slot, 'sent_back', user, facility=wcc.work_order.facility, reason=reason)
    _set_status(wcc, 'Sent Back', is_reviewed=False)
    _tell_next(wcc, reason=reason)


@transaction.atomic
def approve(wcc, user, signature):
    _require(wcc, 'Awaiting Approval')
    found = problems(wcc)
    if found:
        raise ActionRefused("The certificate cannot be approved without its evidence. " + ' '.join(found))
    perform_action(wcc, STAGE, 'approver', 'approved', user, facility=wcc.work_order.facility, signature=signature)
    _set_status(wcc, 'Approved')
    _tell_next(wcc)


# ── who sees and acts ────────────────────────────────────────────────────────

def people_for(wcc, slot):
    facility = wcc.work_order.facility
    if slot == 'requester':
        return list(team_members('requester', facility))
    if slot == 'central_operation':
        return list(team_members('central_operation'))
    if slot == 'contractor':
        vendor = wcc.work_order.vendor
        if vendor is None:
            return []
        return list(get_user_model().objects.filter(roles='CONTRACTOR', vendor=vendor, is_active=True))
    return stage1.people_for(wcc.work_order, slot)


def available_actions(wcc, user):
    if wcc.flow != WorkOrderCompletion.FIVE_STAGE:
        return []
    slot = WAITING_ON.get(wcc.approval_status)
    if slot is None or not acting_for(user, slot, wcc.work_order.facility)[0]:
        return []
    if slot == 'requester':
        return ['edit', 'submit']
    if history(wcc).filter(actor=user, action__in=['raised', 'resubmitted', 'reviewed']).exists():
        return []
    return ['verify', 'send_back'] if slot == 'central_operation' else ['approve', 'send_back']


def timing(wcc):
    if wcc.approval_status in ('Approved', 'Draft'):
        return None
    first = history(wcc).filter(action='raised').first()
    if first is None:
        return None
    facility = wcc.work_order.facility
    return {**step_timing(STAGE, first.at, facility.client if facility else None), 'started_at': first.at}


def ready_work_orders(user):
    """Client-approved five-stage Work Orders at the user's facilities that still need a certificate."""
    if user.roles != 'REQUESTER':
        return []
    orders = (WorkOrder.objects.filter(flow=WorkOrder.FIVE_STAGE, approval_status='Approved')
              .exclude(completions__approval_status__in=WorkOrderCompletion.ACTIVE_STATUSES)
              .select_related('facility').order_by('updated_at'))
    return [wo for wo in orders if acting_for(user, 'requester', wo.facility)[0]]


def my_tasks(user):
    tasks = [{'kind': 'wcc_to_raise', 'order': wo, 'step': 'requester'} for wo in ready_work_orders(user)]
    candidates = (WorkOrderCompletion.objects.filter(flow=WorkOrderCompletion.FIVE_STAGE, approval_status__in=WAITING_ON)
                  .select_related('work_order', 'work_order__facility', 'work_order__facility__client')
                  .order_by('updated_at'))
    for wcc in candidates:
        if not available_actions(wcc, user):
            continue
        slot = WAITING_ON[wcc.approval_status]
        on_behalf_of = acting_for(user, slot, wcc.work_order.facility)[1]
        tasks.append({'kind': 'wcc', 'completion': wcc, 'step': slot, 'on_behalf_of': on_behalf_of, 'timing': timing(wcc)})
    return tasks


# ── telling people ───────────────────────────────────────────────────────────

MESSAGES = {
    'Awaiting Verification': ("Completion to verify on site", "A Work Completion Certificate is waiting for your site check."),
    'Awaiting Approval': ("Completion to approve", "Central Operations verified the work. The certificate is waiting for your approval."),
    'Sent Back': ("Completion sent back", "The certificate was sent back. Please fix it and resubmit."),
    'Approved': ("Completion approved", "The work is approved as complete. The contractor can now submit their invoice."),
}


def _recipients(wcc):
    status = wcc.approval_status
    if status in WAITING_ON:
        return people_for(wcc, WAITING_ON[status])
    if status == 'Approved':
        return people_for(wcc, 'contractor') + people_for(wcc, 'requester')
    return []


def _tell_next(wcc, reason=''):
    from work.utils.email_service import create_in_app_notifications, send_notification_email

    headline, message = MESSAGES[wcc.approval_status]
    recipients = list({u.pk: u for u in _recipients(wcc) if u.is_active}.values())

    def _go():
        create_in_app_notifications(recipients, title=f"{headline} · WCC-{wcc.wcc_number}",
                                    message=message, notification_type='WCC', object_id=wcc.pk)
        send_notification_email(
            subject=f"[AlphaCMMS] {headline} · WCC-{wcc.wcc_number}",
            template='emails/completion_flow.html',
            context={'instance': wcc, 'headline': headline, 'message': message, 'reason': reason},
            recipient_list=[u.email for u in recipients if u.email],
        )

    transaction.on_commit(_go)
