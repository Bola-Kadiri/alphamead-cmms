"""
Action rules: the one check every stage runs before an action is accepted.

  1. The person may act on this step (named signer, their stand-in, or a team member in scope).
  2. Nobody reviews, approves, sends back or rejects work they raised or already reviewed.
  3. Send back and reject need a written reason; review and approve need a typed signature
     matching the person's own name.
  4. Only the client's rejection ends a job; every other checker sends back to be fixed.
  5. An approver's own approval limit applies where an amount is involved.
Then the action is time stamped ("on behalf of" when a stand-in acts). A job sent back
three times or more alerts the Super Admin.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from work.models.action_log import history, record_action
from work.models.approval_matrix import acting_for

DECIDING_ACTIONS = {'reviewed', 'approved', 'sent_back', 'rejected'}
NEEDS_REASON = {'sent_back', 'rejected'}
NEEDS_SIGNATURE = {'reviewed', 'approved'}
SEND_BACK_ALERT_AT = 3

NOTIFICATION_TYPE = {
    'work_request': 'WORK_REQUEST',
    'work_order': 'WORK_ORDER',
    'wcc': 'WCC',
    'vendor_invoice': 'WORK_ORDER',
    'payment': 'PAYMENT_REQUISITION',
}


class ActionRefused(Exception):
    """The action breaks a rule; the message says which and how to fix it."""


def _same_name(signature, user):
    def norm(text):
        return ' '.join((text or '').split()).casefold()
    return norm(signature) in {norm(user.name), norm(user.email)}


def check_action(document, stage, slot, action, user, *, facility, vendor=None, amount=None, reason='', signature=''):
    """Raise ActionRefused if `user` may not take `action` on step `slot`. Returns the signer acted for, if any."""
    allowed, on_behalf_of = acting_for(user, slot, facility, vendor=vendor, amount=amount)
    if not allowed:
        raise ActionRefused("You are not the person for this step, or your cover does not include it.")

    if action == 'rejected' and slot != 'client_rep':
        raise ActionRefused("Only the client can reject a job. Send it back with your reason instead.")

    if action in DECIDING_ACTIONS:
        involved = {'raised', 'resubmitted', 'reviewed'}
        acted_before = history(document).filter(action__in=involved).filter(actor=user).exists()
        if acted_before:
            raise ActionRefused("You cannot review, approve, send back or reject work you raised or reviewed.")

    if action in NEEDS_REASON and not (reason or '').strip():
        raise ActionRefused("Give a reason so the next person knows what to do.")
    if action in NEEDS_SIGNATURE:
        if not (signature or '').strip():
            raise ActionRefused("Type your full name to sign.")
        if not _same_name(signature, user):
            raise ActionRefused("The signature must be your own full name as it appears on your account.")

    limit = getattr(user, 'approval_limit', None)
    if action == 'approved' and amount is not None and limit and amount > limit:
        raise ActionRefused(f"This amount is above your approval limit of NGN {limit:,.2f}.")

    return on_behalf_of


def perform_action(document, stage, slot, action, user, *, facility, vendor=None, amount=None, reason='', signature=''):
    """Check the rules, then stamp the action. Call inside the stage's own save so both commit together."""
    on_behalf_of = check_action(document, stage, slot, action, user, facility=facility, vendor=vendor,
                                amount=amount, reason=reason, signature=signature)
    with transaction.atomic():
        stamp = record_action(document, stage, action, user, reason=(reason or '').strip(),
                              signature=(signature or '').strip(), on_behalf_of=on_behalf_of, facility=facility)
        if action == 'sent_back':
            _alert_if_bouncing(document, stage, facility)
    return stamp


def _alert_if_bouncing(document, stage, facility):
    count = history(document).filter(action='sent_back').count()
    if count < SEND_BACK_ALERT_AT:
        return
    from work.utils.email_service import create_in_app_notifications

    admins = get_user_model().objects.filter(roles='SUPER ADMIN', is_active=True)
    where = f" at {facility.name}" if facility else ''
    create_in_app_notifications(
        admins,
        title=f"Sent back {count} times",
        message=f"A {stage.replace('_', ' ')}{where} has been sent back {count} times. Please check what is blocking it.",
        notification_type=NOTIFICATION_TYPE.get(stage, 'WORK_ORDER'),
        object_id=document.pk,
    )
