"""
Stage 4 (Vendor Invoice) of the five-stage flow:

  The contractor (the vendor's staff) submits the invoice against the approved WCC —
  or an AP Officer enters it for a vendor without a login → AP Officers (team) check
  it against the Work Order and the WCC, or return it → Head of Finance & Treasury
  (named) approves it, or returns it.

The amount cannot be more than the Work Order amount (the vendor cost), VAT at 7.5% is
optional, and a Work Order is invoiced only once. Approving it lets AP raise the payment.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from work.models import work_request_flow as stage1
from work.models.action_log import history
from work.models.approval_matrix import acting_for, team_members
from work.models.flow_rules import ActionRefused, perform_action
from work.models.invoice import Invoice
from work.models.time_limits import step_timing
from work.models.work_order_completion import WorkOrderCompletion

STAGE = 'vendor_invoice'
ACTIVE_STATUSES = {'Draft', 'Awaiting Review', 'Returned', 'Awaiting Approval', 'Approved'}

STEP_LABELS = {
    'contractor': 'Contractor',
    'ap_officer': 'AP Officer',
    'head_of_finance': 'Head of Finance & Treasury',
}


def raiser_slot(inv):
    return 'ap_officer' if inv.entered_for_vendor else 'contractor'


def waiting_on(inv):
    status = inv.approval_status
    if status in ('Draft', 'Returned'):
        return raiser_slot(inv)
    return {'Awaiting Review': 'ap_officer', 'Awaiting Approval': 'head_of_finance'}.get(status)


def _require(inv, *statuses):
    if inv.flow != Invoice.FIVE_STAGE:
        raise ActionRefused("This invoice follows the original flow.")
    if inv.approval_status not in statuses:
        raise ActionRefused(f"This invoice is {inv.approval_status}; that action is not available now.")


def _set_status(inv, status, **extra):
    inv.approval_status = status
    fields = ['approval_status', 'updated_at']
    for name, value in extra.items():
        setattr(inv, name, value)
        fields.append(name)
    inv.save(update_fields=fields)


def _raiser_check(inv, user):
    if not acting_for(user, raiser_slot(inv), inv.facility, vendor=inv.vendor)[0]:
        raise ActionRefused("Only the vendor's own staff, or an AP Officer entering it for them, can prepare this invoice.")


def _money(value, label):
    try:
        amount = Decimal(str(value)).quantize(Decimal('0.01'))
    except Exception:
        raise ActionRefused(f"{label} must be a number.")
    return amount


# ── raising ──────────────────────────────────────────────────────────────────

def invoiceable(wcc):
    """Whether this approved five-stage WCC's Work Order still needs its invoice."""
    return (wcc.flow == WorkOrderCompletion.FIVE_STAGE and wcc.approval_status == 'Approved'
            and not Invoice.objects.filter(flow=Invoice.FIVE_STAGE, work_order=wcc.work_order,
                                           approval_status__in=ACTIVE_STATUSES).exists())


@transaction.atomic
def start(wcc, user):
    """Open an invoice for an approved certificate — by the vendor's staff, or by AP for them."""
    if wcc.flow != WorkOrderCompletion.FIVE_STAGE or wcc.approval_status != 'Approved':
        raise ActionRefused("An invoice can only be raised against an approved completion certificate.")
    wo = wcc.work_order
    if not invoiceable(wcc):
        raise ActionRefused("This job has already been invoiced.")
    if acting_for(user, 'contractor', wo.facility, vendor=wo.vendor)[0]:
        on_behalf = False
    elif acting_for(user, 'ap_officer', wo.facility)[0]:
        on_behalf = True
    else:
        raise ActionRefused("Only the vendor's own staff, or an AP Officer entering it for them, can raise this invoice.")
    today = timezone.localdate()
    return Invoice.objects.create(
        flow=Invoice.FIVE_STAGE, approval_status='Draft', work_order=wo, work_completion=wcc, facility=wo.facility,
        vendor=wo.vendor, currency='NGN', invoice_date=today, due_date=today + timedelta(days=30),
        raised_by=user, owner=user, entered_for_vendor=on_behalf,
    )


@transaction.atomic
def save_details(inv, user, *, vendor_invoice_number=None, invoice_date=None, amount=None, vat_charged=None, files=()):
    _require(inv, 'Draft', 'Returned')
    _raiser_check(inv, user)
    if vendor_invoice_number is not None:
        inv.vendor_invoice_number = vendor_invoice_number.strip()
    if invoice_date not in (None, ''):
        parsed = parse_date(invoice_date) if isinstance(invoice_date, str) else invoice_date
        if parsed is None:
            raise ActionRefused("Enter the invoice date as a date, e.g. 2026-10-30.")
        inv.invoice_date = parsed
        inv.due_date = parsed + timedelta(days=30)
    if amount not in (None, ''):
        inv.subtotal = _money(amount, 'The amount')
    if vat_charged is not None:
        inv.vat_charged = bool(vat_charged)
    inv.tax_amount = (inv.subtotal * Invoice.VAT_RATE).quantize(Decimal('0.01'), ROUND_HALF_UP) if inv.vat_charged else Decimal('0')
    inv.total_amount = inv.subtotal + inv.tax_amount
    inv.save()
    if files:
        from django.contrib.contenttypes.models import ContentType
        from utils.models import FileAttachment
        content_type = ContentType.objects.get_for_model(inv)
        for upload in files:
            FileAttachment.objects.create(content_type=content_type, object_id=inv.pk, file=upload)


def match(inv):
    """Three-way match: the invoice against the Work Order and the WCC. Every row must pass."""
    wo, wcc = inv.work_order, inv.work_completion
    wo_amount = wo.cost or Decimal('0')
    duplicate_number = bool(inv.vendor_invoice_number) and Invoice.objects.filter(
        flow=Invoice.FIVE_STAGE, vendor=inv.vendor, vendor_invoice_number__iexact=inv.vendor_invoice_number,
    ).exclude(pk=inv.pk).exists()
    expected_vat = (inv.subtotal * Invoice.VAT_RATE).quantize(Decimal('0.01'), ROUND_HALF_UP) if inv.vat_charged else Decimal('0')
    rows = [
        ('Vendor matches the Work Order', wo.vendor.name if wo.vendor_id else '—',
         inv.vendor.name if inv.vendor_id else '—', inv.vendor_id is not None and inv.vendor_id == wo.vendor_id),
        ('Amount within the Work Order amount', f"≤ NGN {wo_amount:,.2f}", f"NGN {inv.subtotal:,.2f}",
         Decimal('0') < inv.subtotal <= wo_amount),
        ('Completion certificate approved', f"WCC-{wcc.wcc_number}" if wcc else '—', wcc.approval_status if wcc else '—',
         bool(wcc) and wcc.approval_status == 'Approved'),
        ('Not invoiced before', 'No other invoice with this number',
         'Duplicate number' if duplicate_number else (inv.vendor_invoice_number or '—'),
         bool(inv.vendor_invoice_number) and not duplicate_number),
        ('VAT (optional, 7.5%)', f"NGN {expected_vat:,.2f}" if inv.vat_charged else 'Not charged',
         f"NGN {inv.tax_amount:,.2f}", inv.tax_amount == expected_vat),
        ('Vendor can be paid', 'Bank details on file',
         'On file' if inv.vendor_id and inv.vendor.has_bank_details else 'Missing',
         bool(inv.vendor_id) and inv.vendor.has_bank_details),
    ]
    return [{'check': check, 'expected': expected, 'actual': actual, 'ok': ok} for check, expected, actual, ok in rows]


def problems(inv):
    found = []
    if not inv.vendor_invoice_number:
        found.append("Enter your invoice number.")
    if inv.invoice_date and inv.invoice_date > timezone.localdate():
        found.append("The invoice date cannot be in the future.")
    wo_amount = inv.work_order.cost or Decimal('0')
    if inv.subtotal <= 0:
        found.append("Enter the invoice amount.")
    elif inv.subtotal > wo_amount:
        found.append(f"The amount cannot be more than the Work Order amount of NGN {wo_amount:,.2f}.")
    if not (inv.attachments.exists() or inv.pdf_file):
        found.append("Attach the invoice (PDF).")
    failed = {row['check'] for row in match(inv) if not row['ok']}
    if inv.vendor_invoice_number and 'Not invoiced before' in failed:
        found.append("This invoice number has already been used for this vendor.")
    if 'Vendor matches the Work Order' in failed:
        found.append("The invoice vendor does not match the Work Order.")
    if 'Vendor can be paid' in failed:
        found.append("The vendor has no bank details on file. Ask the Super Admin to add them.")
    return found


# ── actions ──────────────────────────────────────────────────────────────────

@transaction.atomic
def submit(inv, user):
    _require(inv, 'Draft', 'Returned')
    found = problems(inv)
    if found:
        raise ActionRefused(' '.join(found))
    action = 'raised' if inv.approval_status == 'Draft' else 'resubmitted'
    perform_action(inv, STAGE, raiser_slot(inv), action, user, facility=inv.facility, vendor=inv.vendor)
    _set_status(inv, 'Awaiting Review')
    _tell_next(inv)


@transaction.atomic
def review(inv, user, signature, note=''):
    _require(inv, 'Awaiting Review')
    failed = [row['check'] for row in match(inv) if not row['ok']]
    if failed:
        raise ActionRefused("The three-way match does not pass: " + '; '.join(failed) + ". Return it to the contractor instead.")
    perform_action(inv, STAGE, 'ap_officer', 'reviewed', user, facility=inv.facility, signature=signature, reason=note)
    _set_status(inv, 'Awaiting Approval', is_reviewed=True)
    _tell_next(inv)


@transaction.atomic
def return_invoice(inv, user, reason):
    _require(inv, 'Awaiting Review', 'Awaiting Approval')
    slot = waiting_on(inv)
    perform_action(inv, STAGE, slot, 'sent_back', user, facility=inv.facility, reason=reason)
    _set_status(inv, 'Returned', is_reviewed=False)
    _tell_next(inv, reason=reason)


@transaction.atomic
def approve(inv, user, signature):
    _require(inv, 'Awaiting Approval')
    perform_action(inv, STAGE, 'head_of_finance', 'approved', user, facility=inv.facility, signature=signature,
                   amount=inv.total_amount)
    _set_status(inv, 'Approved', is_approved=True)
    _tell_next(inv)


# ── who sees and acts ────────────────────────────────────────────────────────

def people_for(inv, slot):
    if slot == 'contractor':
        if inv.vendor_id is None:
            return []
        return list(get_user_model().objects.filter(roles='CONTRACTOR', vendor=inv.vendor, is_active=True))
    if slot == 'ap_officer':
        return list(team_members('ap_officer'))
    return stage1.people_for(inv.work_order, slot)


def available_actions(inv, user):
    if inv.flow != Invoice.FIVE_STAGE:
        return []
    slot = waiting_on(inv)
    if slot is None or not acting_for(user, slot, inv.facility, vendor=inv.vendor)[0]:
        return []
    if inv.approval_status in ('Draft', 'Returned'):
        return ['edit', 'submit']
    if history(inv).filter(actor=user, action__in=['raised', 'resubmitted', 'reviewed']).exists():
        return []
    return ['review', 'return'] if slot == 'ap_officer' else ['approve', 'return']


def timing(inv):
    if inv.approval_status in ('Approved', 'Draft'):
        return None
    first = history(inv).filter(action='raised').first()
    if first is None:
        return None
    client = inv.facility.client if inv.facility_id else None
    return {**step_timing(STAGE, first.at, client), 'started_at': first.at}


def to_invoice(user):
    """Approved certificates whose job this user may invoice (contractor's own, or any for AP)."""
    if user.roles not in ('CONTRACTOR', 'AP OFFICER') or not user.is_active:
        return []
    wccs = (WorkOrderCompletion.objects.filter(flow=WorkOrderCompletion.FIVE_STAGE, approval_status='Approved')
            .select_related('work_order', 'work_order__facility', 'work_order__vendor').order_by('updated_at'))
    if user.roles == 'CONTRACTOR':
        wccs = wccs.filter(work_order__vendor_id=user.vendor_id) if user.vendor_id else wccs.none()
    rows = [wcc for wcc in wccs if invoiceable(wcc)]
    if user.roles == 'AP OFFICER':
        # AP enters invoices only for vendors who have nobody to do it themselves.
        rows = [wcc for wcc in rows if not get_user_model().objects.filter(
            roles='CONTRACTOR', vendor=wcc.work_order.vendor, is_active=True).exists()]
    return rows


def my_tasks(user):
    tasks = [{'kind': 'invoice_to_raise', 'completion': wcc, 'step': 'contractor' if user.roles == 'CONTRACTOR' else 'ap_officer'}
             for wcc in to_invoice(user)]
    candidates = (Invoice.objects.filter(flow=Invoice.FIVE_STAGE, approval_status__in=['Draft', 'Returned', 'Awaiting Review', 'Awaiting Approval'])
                  .select_related('facility', 'facility__client', 'vendor', 'work_order').order_by('updated_at'))
    for inv in candidates:
        if not available_actions(inv, user):
            continue
        slot = waiting_on(inv)
        on_behalf_of = acting_for(user, slot, inv.facility, vendor=inv.vendor)[1]
        tasks.append({'kind': 'invoice', 'invoice': inv, 'step': slot, 'on_behalf_of': on_behalf_of, 'timing': timing(inv)})
    return tasks


# ── telling people ───────────────────────────────────────────────────────────

MESSAGES = {
    'Awaiting Review': ("Invoice to check", "A vendor invoice is waiting for your three-way check."),
    'Awaiting Approval': ("Invoice to approve", "AP checked a vendor invoice. It is waiting for your approval."),
    'Returned': ("Invoice returned", "Your invoice was returned. Please correct it and resubmit."),
    'Approved': ("Invoice approved", "The invoice is approved. AP can now raise the payment voucher."),
}


def _recipients(inv):
    status = inv.approval_status
    if status in ('Awaiting Review', 'Awaiting Approval', 'Returned'):
        return people_for(inv, waiting_on(inv))
    if status == 'Approved':
        return people_for(inv, 'ap_officer') + people_for(inv, 'contractor')
    return []


def _tell_next(inv, reason=''):
    from work.utils.email_service import create_in_app_notifications, send_notification_email

    headline, message = MESSAGES[inv.approval_status]
    recipients = list({u.pk: u for u in _recipients(inv) if u.is_active}.values())

    def _go():
        create_in_app_notifications(recipients, title=f"{headline} · {inv.invoice_number}",
                                    message=message, notification_type='WORK_ORDER', object_id=inv.pk)
        send_notification_email(
            subject=f"[AlphaCMMS] {headline} · {inv.invoice_number}",
            template='emails/invoice_flow.html',
            context={'instance': inv, 'headline': headline, 'message': message, 'reason': reason},
            recipient_list=[u.email for u in recipients if u.email],
        )

    transaction.on_commit(_go)
