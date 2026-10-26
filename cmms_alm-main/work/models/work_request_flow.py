"""
Stage 1 (Work Request) of the five-stage flow, for facilities switched on in the
Approval Matrix:

  Site Managers (team) raise → Category Manager (named) reviews or sends back →
  Client rep (named) approves, or rejects and the job ends.

If the facility's client approves the price only (Client.approves_work_requests is
off), the Category Manager's review completes the stage. Every action runs the
action rules and is time stamped; the people who must act next are told.

The current signer is always read from the Approval Matrix, so replacing a signer
moves their waiting requests to the new person.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from work.models.action_log import history
from work.models.approval_matrix import COMPANY_SLOTS, ApprovalMatrix, CompanyApprovers, acting_for, team_members
from work.models.delegation import Delegation
from work.models.flow_rules import ActionRefused, perform_action
from work.models.time_limits import step_timing
from work.models.work_request import WorkRequest

STAGE = 'work_request'

# Status → the step whose people act next.
WAITING_ON = {
    'Awaiting Review': 'approver',
    'Sent Back': 'requester',
    'Awaiting Client': 'client_rep',
}
STEP_LABELS = {
    'requester': 'Site Manager',
    'approver': 'Category Manager',
    'client_rep': 'Client',
}


def facility_is_live(facility):
    return bool(facility) and ApprovalMatrix.objects.filter(facility=facility, is_live=True).exists()


def client_approves(wr):
    client = wr.facility.client if wr.facility_id else None
    return client is None or client.approves_work_requests


def _require(wr, *statuses):
    if wr.flow != WorkRequest.FIVE_STAGE:
        raise ActionRefused("This request follows the original flow.")
    if wr.approval_status not in statuses:
        raise ActionRefused(f"This request is {wr.approval_status}; that action is not available now.")


def _set_status(wr, status, **extra):
    wr.approval_status = status
    fields = ['approval_status', 'updated_at']
    for name, value in extra.items():
        setattr(wr, name, value)
        fields.append(name)
    wr.save(update_fields=fields)


# ── actions ──────────────────────────────────────────────────────────────────

@transaction.atomic
def raise_request(wr, user):
    """Stamp a newly created five-stage request as raised and send it to the Category Manager."""
    perform_action(wr, STAGE, 'requester', 'raised', user, facility=wr.facility)
    _set_status(wr, 'Awaiting Review', is_locked=True)
    _tell_next(wr)


@transaction.atomic
def review(wr, user, signature, note=''):
    _require(wr, 'Awaiting Review')
    perform_action(wr, STAGE, 'approver', 'reviewed', user, facility=wr.facility, signature=signature, reason=note)
    if client_approves(wr):
        _set_status(wr, 'Awaiting Client')
    else:
        _set_status(wr, 'Fully Approved', fully_approved_at=timezone.now())
    _tell_next(wr)


@transaction.atomic
def send_back(wr, user, reason):
    _require(wr, 'Awaiting Review')
    perform_action(wr, STAGE, 'approver', 'sent_back', user, facility=wr.facility, reason=reason)
    _set_status(wr, 'Sent Back', is_locked=False)
    _tell_next(wr, reason=reason)


@transaction.atomic
def resubmit(wr, user):
    _require(wr, 'Sent Back')
    perform_action(wr, STAGE, 'requester', 'resubmitted', user, facility=wr.facility)
    _set_status(wr, 'Awaiting Review', is_locked=True)
    _tell_next(wr)


@transaction.atomic
def client_approve(wr, user, signature):
    _require(wr, 'Awaiting Client')
    perform_action(wr, STAGE, 'client_rep', 'approved', user, facility=wr.facility, signature=signature)
    _set_status(wr, 'Fully Approved', fully_approved_at=timezone.now(), digital_signature=signature.strip())
    _tell_next(wr)


@transaction.atomic
def client_reject(wr, user, reason):
    _require(wr, 'Awaiting Client')
    perform_action(wr, STAGE, 'client_rep', 'rejected', user, facility=wr.facility, reason=reason)
    _set_status(wr, 'Client Rejected', is_locked=True)
    _tell_next(wr, reason=reason)


# ── who sees and acts ────────────────────────────────────────────────────────

def people_for(wr, slot):
    """Everyone who may act on `slot` for `wr` now: the team, or the named signer and any active stand-in."""
    if slot == 'requester':
        return list(team_members('requester', wr.facility))
    if slot in COMPANY_SLOTS:
        signer = getattr(CompanyApprovers.current(), slot, None)
    else:
        matrix = ApprovalMatrix.objects.filter(facility=wr.facility).first()
        signer = getattr(matrix, slot, None) if matrix else None
    if signer is None:
        return []
    stand_ins = [d.stand_in for d in Delegation.objects.active().filter(person=signer).select_related('stand_in')]
    return [signer] + stand_ins


def available_actions(wr, user):
    """The actions `user` may take on `wr` right now (for the screen's buttons)."""
    if wr.flow != WorkRequest.FIVE_STAGE:
        return []
    slot = WAITING_ON.get(wr.approval_status)
    if slot is None or not acting_for(user, slot, wr.facility)[0]:
        return []
    if slot == 'requester':
        return ['resubmit']
    decided_before = history(wr).filter(actor=user, action__in=['raised', 'resubmitted', 'reviewed']).exists()
    if decided_before:
        return []
    if slot == 'approver':
        return ['review', 'send_back']
    return ['approve', 'reject']


def my_tasks(user):
    """Five-stage requests waiting on `user`, oldest first."""
    candidates = (WorkRequest.objects.filter(flow=WorkRequest.FIVE_STAGE, approval_status__in=WAITING_ON)
                  .select_related('facility', 'facility__client', 'asset').order_by('updated_at'))
    tasks = []
    for wr in candidates:
        slot = WAITING_ON[wr.approval_status]
        allowed, on_behalf_of = acting_for(user, slot, wr.facility)
        if not allowed or not available_actions(wr, user):
            continue
        tasks.append({'request': wr, 'step': slot, 'on_behalf_of': on_behalf_of, 'timing': timing(wr)})
    return tasks


def timing(wr):
    if wr.pk is None:
        return None
    first = history(wr).filter(action='raised').first()
    if first is None:
        return None
    client = wr.facility.client if wr.facility_id else None
    if wr.approval_status in ('Fully Approved', 'Client Rejected'):
        return None
    result = step_timing(STAGE, first.at, client)
    return {**result, 'started_at': first.at}


# ── telling people ───────────────────────────────────────────────────────────

MESSAGES = {
    'Awaiting Review': ("Work Request to review", "A Work Request is waiting for your review."),
    'Sent Back': ("Work Request sent back", "Your Work Request was sent back. Please fix it and resubmit."),
    'Awaiting Client': ("Work Request awaiting your approval", "A Work Request is waiting for your approval."),
    'Fully Approved': ("Work Request approved", "This Work Request is approved. Procurement & Store can now price it."),
    'Client Rejected': ("Work Request rejected by the client", "The client rejected this Work Request. The job has ended."),
}


def _recipients(wr):
    status = wr.approval_status
    if status in WAITING_ON:
        return people_for(wr, WAITING_ON[status])
    if status == 'Fully Approved':
        procurement = list(get_user_model().objects.filter(roles='PROCUREMENT AND STORE', is_active=True))
        return procurement + people_for(wr, 'requester')
    if status == 'Client Rejected':
        return people_for(wr, 'requester') + people_for(wr, 'approver')
    return []


def _tell_next(wr, reason=''):
    from work.utils.email_service import create_in_app_notifications, send_notification_email

    status = wr.approval_status
    headline, message = MESSAGES[status]
    recipients = {u.pk: u for u in _recipients(wr) if u.is_active}.values()

    def _send():
        create_in_app_notifications(list(recipients), title=f"{headline} · {wr.work_request_number}",
                                    message=message, notification_type='WORK_REQUEST', object_id=wr.pk)
        send_notification_email(
            subject=f"[AlphaCMMS] {headline} · {wr.work_request_number}",
            template='emails/work_request_flow.html',
            context={'instance': wr, 'headline': headline, 'message': message, 'reason': reason},
            recipient_list=[u.email for u in recipients if u.email],
        )

    transaction.on_commit(_send)
