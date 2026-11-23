"""
Super Admin override: the Super Admin may do someone else's *maker* step (edit and submit)
when that person is stuck or away, but never a *checker* step (review, approve, reject, pay).

Every override needs a written reason, is stamped in the record's history as
"Super Admin, on behalf of <step>", and the people whose step it was are told.
Only the SUPER ADMIN role has it; ADMIN does not.
"""
from work.models.action_log import record_action
from work.models.flow_rules import ActionRefused, NOTIFICATION_TYPE

PREFIX = "Super Admin override: "


def is_super_admin(user):
    return bool(user and user.is_active and getattr(user, 'roles', '') == 'SUPER ADMIN')


def clean_reason(reason):
    """The Super Admin's reason, required for every override."""
    text = (reason or '').strip()
    if not text:
        raise ActionRefused("You are acting as Super Admin for someone else. Give a reason so the history shows why.")
    return text


def record_override(document, stage, action, user, reason, on_behalf_of, facility=None):
    """Stamp the override in the history: the Super Admin, the step acted for, and why."""
    return record_action(document, stage, action, user, reason=PREFIX + reason,
                         on_behalf_of_name=on_behalf_of, facility=facility)


def tell(people, user, document, stage, what, reason):
    """Let the people whose step it was know the Super Admin acted for them."""
    from django.db import transaction
    from work.utils.email_service import create_in_app_notifications

    recipients = list({p.pk: p for p in people if p and p.is_active and p.pk != user.pk}.values())
    if not recipients:
        return
    who = (user.name or '').strip() or user.email
    transaction.on_commit(lambda: create_in_app_notifications(
        recipients,
        title="Super Admin acted on your work",
        message=f"{who} (Super Admin) {what}. Reason: {reason}",
        notification_type=NOTIFICATION_TYPE.get(stage, 'WORK_ORDER'),
        object_id=document.pk,
    ))
