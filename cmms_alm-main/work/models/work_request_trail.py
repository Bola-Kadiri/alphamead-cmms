"""
Five-stage Work Request approval trail and whole-job strip, for the request's page.

The trail has the same shape as the Raise Payment trail (see raise_payment_trail), built
from the action log the five-stage flow already keeps: who did each step, when, on whose
behalf, and who has the request now. The job strip shows the five stages and where the job is.
"""
from work.models import work_request_flow as stage1
from work.models.action_log import history

# Action → (label, role of whoever takes it).
ACTIONS = {
    'raised': ('Raised', 'Site Manager'),
    'resubmitted': ('Resubmitted', 'Site Manager'),
    'reviewed': ('Checked', 'Category Manager'),
    'sent_back': ('Sent back to the Site Managers', 'Category Manager'),
    'approved': ('Client approved', 'Client Contract Rep'),
    'rejected': ('Rejected by the client', 'Client Contract Rep'),
}
STEP_LABEL = {'requester': 'Raised', 'approver': 'Check', 'client_rep': 'Client approval', 'procurement': 'Work Order'}
STEP_ROLE = {'requester': 'Site Managers', 'approver': 'Category Manager', 'client_rep': 'Client Contract Rep',
             'procurement': 'Procurement & Store'}


def _person(user, show_email):
    if user is None:
        return None
    return {'id': user.pk, 'name': (user.name or '').strip() or user.email, 'email': user.email if show_email else ''}


def trail(wr, viewer):
    show_email = getattr(viewer, 'roles', '') != 'CLIENT'  # staff contacts are not shown to clients
    people = lambda users: [p for p in (_person(u, show_email) for u in users) if p]
    client_step = stage1.client_approves(wr)
    route = ['requester', 'approver'] + (['client_rep'] if client_step else []) + ['procurement']

    stamps = list(history(wr).select_related('actor', 'on_behalf_of')) if wr.pk else []
    events = []
    for s in stamps:
        label, role = ACTIONS.get(s.action, (s.get_action_display(), s.actor_role))
        if s.action == 'reviewed' and not client_step:
            label = 'Checked · fully approved'
        state = {'sent_back': 'returned', 'rejected': 'rejected'}.get(s.action, 'done')
        events.append({
            'action': s.action, 'label': label, 'role': role, 'state': state,
            'actor': _person(s.actor, show_email) or {'id': None, 'name': s.actor_name, 'email': ''},
            'on_behalf_of': _person(s.on_behalf_of, show_email), 'at': s.at,
            'took_seconds': s.since_previous.total_seconds() if s.since_previous else None,
            # A reason explains a send-back or rejection; on a check it is the Category Manager's note.
            'reason': (s.reason or None) if s.action in ('sent_back', 'rejected') else None,
            'note': (s.reason or None) if s.action not in ('sent_back', 'rejected') else None,
            'signature': s.signature or None, 'recorded': True, 'assigned': [],
        })

    status = wr.approval_status
    slot = stage1.WAITING_ON.get(status)
    waiting = None
    upcoming = []
    if slot:
        waiting = {'step': slot, 'label': 'Fix and resubmit' if status == 'Sent Back' else STEP_LABEL[slot],
                   'role': STEP_ROLE[slot], 'people': people(stage1.people_for(wr, slot)),
                   'since': stamps[-1].at if stamps else wr.updated_at}
        start = route.index('approver') if slot == 'requester' else route.index(slot) + 1
        upcoming = [{'step': step, 'label': STEP_LABEL[step], 'role': STEP_ROLE[step],
                     'people': [] if step == 'procurement' else people(stage1.people_for(wr, step))}
                    for step in route[start:]]
    return {
        'route': [STEP_LABEL[step] for step in route],
        'events': events,
        'waiting': waiting,
        'upcoming': upcoming,
        'closed': {'Client Rejected': 'rejected', 'Fully Approved': 'approved'}.get(status),
        'po_number': None,
        'quotation_amount': None,
    }


def job(wr):
    """The five stages of the job and where it is: done, current, next or stopped, with a link to each page."""
    from work.models import Invoice, WorkOrder, WorkOrderCompletion
    from work.models.payment_voucher import PaymentVoucher

    def stage(key, label, state, link=None, note=''):
        return {'key': key, 'label': label, 'state': state, 'link': link, 'note': note}

    stages = []
    status = wr.approval_status
    request_state = {'Fully Approved': 'done', 'Client Rejected': 'stopped'}.get(status, 'current')
    stages.append(stage('request', 'Request', request_state, None, {'Sent Back': 'sent back'}.get(status, '')))

    wo = (WorkOrder.objects.filter(source_work_request=wr, flow=WorkOrder.FIVE_STAGE).order_by('-id').first()
          if wr.pk else None)
    previous_done = request_state == 'done'
    if wo is None:
        stages.append(stage('work_order', 'Work Order', 'current' if previous_done else 'next', None,
                            'with Procurement' if previous_done else ''))
        previous_done = False
    else:
        state = {'Approved': 'done', 'Client Rejected': 'stopped'}.get(wo.approval_status, 'current')
        stages.append(stage('work_order', 'Work Order', state, f'/dashboard/work/orders/view/{wo.slug}'))
        previous_done = state == 'done'

    wcc = (wo.completions.filter(flow=WorkOrderCompletion.FIVE_STAGE).order_by('-id').first() if wo else None)
    if wcc is None:
        stages.append(stage('certificate', 'Certificate', 'current' if previous_done else 'next'))
        previous_done = False
    else:
        state = 'done' if wcc.approval_status == 'Approved' else 'current'
        stages.append(stage('certificate', 'Certificate', state, f'/dashboard/work/work-order-completions/{wcc.pk}'))
        previous_done = state == 'done'

    inv = (Invoice.objects.filter(work_order=wo, flow=Invoice.FIVE_STAGE).order_by('-id').first() if wo else None)
    if inv is None:
        stages.append(stage('invoice', 'Invoice', 'current' if previous_done else 'next'))
        previous_done = False
    else:
        state = 'done' if inv.approval_status == 'Approved' else 'current'
        stages.append(stage('invoice', 'Invoice', state, f'/dashboard/work/invoice-items/{inv.pk}'))
        previous_done = state == 'done'

    voucher = PaymentVoucher.objects.filter(invoice=inv).first() if inv else None
    if voucher is None:
        stages.append(stage('payment', 'Payment', 'current' if previous_done else 'next'))
    else:
        stages.append(stage('payment', 'Payment', 'done' if voucher.status == 'Paid' else 'current',
                            f'/dashboard/payments/{voucher.pk}'))
    return stages
