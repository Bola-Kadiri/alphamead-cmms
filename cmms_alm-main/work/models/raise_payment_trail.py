"""
Raise Payment approval trail: who is meant to act at each step, who actually did, and when.

`stamp` records an action on a Raise Payment bill (approver-first route) in the append-only
action log; `trail` builds what the bill page shows. Bills approved before recording began
show the assigned person for those steps, marked as not recorded.
"""
from django.contrib.auth import get_user_model

from work.models.action_log import history, record_action

STAGE = 'work_order'

# Action → (label shown on the trail, role of whoever takes it).
ACTIONS = {
    'raised': ('Raised', 'Requester'),
    'resubmitted': ('Resubmitted', 'Requester'),
    'procured': ('PO & quotation', 'Procurement & Store'),
    'sent_back': ('Returned to the Requester', 'Procurement & Store'),
    'approved': ('Approved', 'Approver'),
    'reviewed': ('Reviewed', 'Reviewer'),
    'final_approved': ('Final approval', 'Final approver'),
    'rejected': ('Rejected', ''),
    'paid': ('Paid', 'Head of Finance & Treasury'),
}
STEP_ACTION = {'raised': 'raised', 'procurement': 'procured', 'approver': 'approved', 'reviewer': 'reviewed',
               'final': 'final_approved', 'payment': 'paid'}
STEP_LABEL = {'raised': 'Raised', 'procurement': 'PO & quotation', 'approver': 'Approval', 'reviewer': 'Review',
              'final': 'Final approval', 'payment': 'Payment'}
STEP_ROLE = {'raised': 'Requester', 'procurement': 'Procurement & Store', 'approver': 'Approver',
             'reviewer': 'Reviewer', 'final': 'Final approver', 'payment': 'Head of Finance & Treasury'}
CURRENT_STEP = {'Awaiting Procurement': 'procurement', 'Procurement Returned': 'raised', 'Pending': 'approver',
                'Approver Approved': 'reviewer', 'Awaiting Final Approval': 'final', 'Approved': 'payment'}
REJECTED_AT = {'Approver Rejected': ('approver', 'approver_reason'), 'Reviewer Rejected': ('reviewer', 'reviewer_reason'),
               'Final Approver Rejected': ('final', 'final_approver_reason')}


def _stand_in_for(wo, user):
    """The bill's Approver when `user` is covering for them, else None."""
    from work.models.delegation import Delegation
    if wo.approver_id is None or user.pk == wo.approver_id:
        return None
    covering = Delegation.objects.active().filter(person_id=wo.approver_id, stand_in=user).exists()
    return wo.approver if covering else None


def stamp(wo, action, user, reason=''):
    """Record a Raise Payment action. Only bills on the approver-first route keep a trail."""
    if not wo.is_approver_first or user is None:
        return None
    on_behalf_of = _stand_in_for(wo, user) if action in ('approved', 'rejected') else None
    return record_action(wo, STAGE, action, user, reason=(reason or '').strip(), on_behalf_of=on_behalf_of)


# ── the trail ────────────────────────────────────────────────────────────────

def _person(user, show_email):
    if user is None:
        return None
    return {'id': user.pk, 'name': (user.name or '').strip() or user.email, 'email': user.email if show_email else ''}


def _route(wo, settings):
    final = bool(wo.final_approver_id) or settings.needs_second_approval(wo.cost, wo.currency)
    return (['raised'] + (['procurement'] if wo.needs_procurement else []) + ['approver', 'reviewer']
            + (['final'] if final else []) + ['payment'])


def _people(wo, step, settings):
    User = get_user_model()
    if step == 'raised':
        return [wo.owner or wo.requester]
    if step == 'procurement':
        return list(User.objects.filter(roles='PROCUREMENT AND STORE', is_active=True).order_by('first_name'))
    if step == 'approver':
        from work.models.delegation import Delegation
        stand_ins = [d.stand_in for d in Delegation.objects.active().filter(person_id=wo.approver_id)
                     .select_related('stand_in')] if wo.approver_id else []
        return [wo.approver] + stand_ins if wo.approver_id else []
    if step == 'reviewer':
        return list(wo.reviewers.all())
    if step == 'final':
        return [wo.final_approver or settings.second_approver()]
    return list(User.objects.filter(roles='HEAD OF FINANCE & TREASURY', is_active=True))


def trail(wo, viewer):
    """What the bill page shows: the steps done, who has it now, and who comes next."""
    from work.models.raise_payment_settings import RaisePaymentApprovalSettings
    settings = RaisePaymentApprovalSettings.current()
    show_email = getattr(viewer, 'roles', '') != 'CLIENT'  # staff contacts are not shown to clients
    people = lambda users: [p for p in (_person(u, show_email) for u in users) if p]
    route = _route(wo, settings)
    status = wo.approval_status
    payment = wo.linked_payments.order_by('id').first()
    paid = payment is not None and payment.is_disbursed
    rejected = REJECTED_AT.get(status)

    if rejected:
        current = None
        done_until = route.index(rejected[0]) if rejected[0] in route else len(route)
    elif paid:
        current, done_until = None, len(route)
    else:
        current = CURRENT_STEP.get(status, 'approver')
        done_until = route.index(current) if current in route else 0

    stamps = list(history(wo).select_related('actor', 'on_behalf_of'))
    recorded_actions = {s.action for s in stamps}
    events = []
    # Steps finished before recording began: the assigned person, marked as not recorded.
    for step in route[:done_until]:
        if STEP_ACTION[step] in recorded_actions:
            continue
        if step == 'payment' and paid:
            events.append({'action': 'paid', 'label': 'Paid', 'role': STEP_ROLE['payment'], 'state': 'done',
                           'actor': _person(payment.disbursed_by, show_email), 'on_behalf_of': None,
                           'at': payment.disbursed_at, 'took_seconds': None, 'reason': None, 'recorded': True,
                           'assigned': []})
            continue
        events.append({'action': STEP_ACTION[step], 'label': STEP_LABEL[step], 'role': STEP_ROLE[step], 'state': 'done',
                       'actor': None, 'on_behalf_of': None, 'at': None, 'took_seconds': None, 'reason': None,
                       'recorded': False, 'assigned': people(_people(wo, step, settings))})
    for s in stamps:
        label, role = ACTIONS.get(s.action, (s.get_action_display(), ''))
        state = {'sent_back': 'returned', 'rejected': 'rejected'}.get(s.action, 'done')
        if s.action == 'rejected' and rejected:
            role = STEP_ROLE[rejected[0]]
        events.append({'action': s.action, 'label': label, 'role': role, 'state': state,
                       'actor': _person(s.actor, show_email) or {'id': None, 'name': s.actor_name, 'email': ''},
                       'on_behalf_of': _person(s.on_behalf_of, show_email), 'at': s.at,
                       'took_seconds': s.since_previous.total_seconds() if s.since_previous else None,
                       'reason': s.reason or None, 'recorded': True, 'assigned': []})
    # A rejection from before recording began.
    if rejected and 'rejected' not in recorded_actions:
        events.append({'action': 'rejected', 'label': 'Rejected', 'role': STEP_ROLE[rejected[0]], 'state': 'rejected',
                       'actor': None, 'on_behalf_of': None, 'at': None, 'took_seconds': None,
                       'reason': getattr(wo, rejected[1], None) or None, 'recorded': False,
                       'assigned': people(_people(wo, rejected[0], settings))})

    waiting = None
    if current is not None:
        waiting = {'step': current, 'label': 'Fix and resubmit' if status == 'Procurement Returned' else STEP_LABEL[current],
                   'role': STEP_ROLE[current], 'people': people(_people(wo, current, settings)),
                   'since': stamps[-1].at if stamps else wo.updated_at}
    upcoming = []
    if current is not None and current in route:
        start = route.index(current) + 1 if status != 'Procurement Returned' else route.index('raised') + 1
        upcoming = [{'step': step, 'label': STEP_LABEL[step], 'role': STEP_ROLE[step],
                     'people': people(_people(wo, step, settings))} for step in route[start:]]
    return {
        'route': [STEP_LABEL[step] for step in route],
        'events': events,
        'waiting': waiting,
        'upcoming': upcoming,
        'closed': 'rejected' if rejected else ('paid' if paid else None),
        'po_number': wo.po_number or None,
        'quotation_amount': str(wo.quotation_amount) if wo.quotation_amount is not None else None,
    }
