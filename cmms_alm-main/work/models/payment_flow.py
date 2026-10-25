"""
Stage 5 (Payment) of the five-stage flow:

  AP Officers (team) raise the payment voucher against the approved invoice and pick the
  withholding tax rate → REVIEWER (Internal Control, team) checks the full trail, or returns
  it → Head of Finance & Treasury (named) approves, pays in the bank and confirms Paid
  (one voucher or a batch). AP may attach the bank receipt but never confirms Paid.

Confirming Paid closes the job and sends the vendor a remittance advice. A payment that
does not go through is marked failed with a reason and can be paid again.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from utils.models import FileAttachment
from work.models import work_request_flow as stage1
from work.models.action_log import history
from work.models.approval_matrix import acting_for, team_members
from work.models.flow_rules import ActionRefused, perform_action
from work.models.invoice import Invoice
from work.models.payment_voucher import PaymentVoucher, WithholdingTaxRate
from work.models.time_limits import step_timing

STAGE = 'payment'
CENTS = Decimal('0.01')

STEP_LABELS = {
    'ap_officer': 'AP Officer',
    'reviewer': 'REVIEWER (Internal Control)',
    'head_of_finance': 'Head of Finance & Treasury',
}


def waiting_on(v):
    return {
        'Draft': 'ap_officer', 'Returned': 'ap_officer',
        'Awaiting Review': 'reviewer',
        'Awaiting Approval': 'head_of_finance',
        'Approved': 'head_of_finance', 'Payment Failed': 'head_of_finance',
    }.get(v.status)


def _require(v, *statuses):
    if v.status not in statuses:
        raise ActionRefused(f"This voucher is {v.get_status_display()}; that action is not available now.")


def _set_status(v, status, **extra):
    v.status = status
    for name, value in extra.items():
        setattr(v, name, value)
    v.save(update_fields=['status', 'updated_at', *extra])


def _attach(v, upload):
    FileAttachment.objects.create(content_type=ContentType.objects.get_for_model(v), object_id=v.pk, file=upload)


# ── raising ──────────────────────────────────────────────────────────────────

def payable_invoices():
    """Approved five-stage invoices that have no voucher yet."""
    return (Invoice.objects.filter(flow=Invoice.FIVE_STAGE, approval_status='Approved', payment_voucher__isnull=True)
            .select_related('vendor', 'facility', 'work_order').order_by('updated_at'))


def to_raise(user):
    if not user.is_active or user.roles != 'AP OFFICER':
        return []
    return list(payable_invoices())


@transaction.atomic
def start(inv, user):
    """Open the voucher for an approved invoice. Amounts are copied from the invoice and locked."""
    if inv.flow != Invoice.FIVE_STAGE or inv.approval_status != 'Approved':
        raise ActionRefused("A payment voucher can only be raised for an approved invoice.")
    if PaymentVoucher.objects.filter(invoice=inv).exists():
        raise ActionRefused("This invoice already has a payment voucher.")
    if not acting_for(user, 'ap_officer', inv.facility)[0]:
        raise ActionRefused("Only an AP Officer can raise the payment voucher.")
    v = PaymentVoucher(invoice=inv, work_order=inv.work_order, facility=inv.facility, vendor=inv.vendor,
                       amount=inv.subtotal, vat=inv.tax_amount, raised_by=user)
    _recalculate(v)
    v.save()
    return v


def _recalculate(v):
    v.wht_amount = (v.amount * v.wht_percent / 100).quantize(CENTS, ROUND_HALF_UP)
    v.net_amount = v.amount + v.vat - v.wht_amount


@transaction.atomic
def save_details(v, user, *, wht_rate=None, payment_method=None):
    _require(v, 'Draft', 'Returned')
    if not acting_for(user, 'ap_officer', v.facility)[0]:
        raise ActionRefused("Only an AP Officer can prepare the payment voucher.")
    if wht_rate not in (None, ''):
        rate = WithholdingTaxRate.objects.filter(pk=wht_rate, is_active=True).first()
        if rate is None:
            raise ActionRefused("Choose a withholding tax rate from the list.")
        v.wht_rate, v.wht_percent = rate, rate.rate
    if payment_method not in (None, ''):
        if payment_method not in dict(PaymentVoucher.METHODS):
            raise ActionRefused("Choose bank transfer or cheque.")
        v.payment_method = payment_method
    _recalculate(v)
    v.save()


# ── the trail and the checks ─────────────────────────────────────────────────

def _documents(v):
    """(stage, document, its label, the status that means it is finally approved)."""
    wo, inv = v.work_order, v.invoice
    return [
        ('1 · Work Request', wo.source_work_request, lambda d: f"WR {d.work_request_number}", 'Fully Approved'),
        ('2 · Work Order', wo, lambda d: f"WO {d.work_order_number}", 'Approved'),
        ('3 · Completion', inv.work_completion, lambda d: f"WCC-{d.wcc_number}", 'Approved'),
        ('4 · Vendor Invoice', inv, lambda d: d.vendor_invoice_number or d.invoice_number, 'Approved'),
    ]


def trail(v):
    """Stages 1–4: who raised, checked and approved each document, and when."""
    rows = []
    for stage, doc, label, final in _documents(v):
        if doc is None:
            rows.append({'stage': stage, 'document': '—', 'raised': None, 'reviewed': None, 'approved': None, 'ok': False})
            continue
        stamps = history(doc)

        def last(*actions):
            a = stamps.filter(action__in=actions).order_by('-at', '-id').first()
            return {'by': a.actor_name, 'at': a.at, 'on_behalf_of': a.on_behalf_of_name or None} if a else None

        # A Work Request the client does not sign off is finally approved by the Approver's check.
        approved = last('approved') or (last('reviewed') if final == 'Fully Approved' else None)
        rows.append({'stage': stage, 'document': label(doc), 'raised': last('raised'), 'reviewed': last('reviewed'),
                     'approved': approved, 'ok': doc.approval_status == final and approved is not None})
    return rows


def _nobody_approved_own_work(v):
    for _, doc, _, _ in _documents(v):
        if doc is None:
            return False
        stamps = history(doc)
        raisers = set(stamps.filter(action__in=['raised', 'resubmitted']).values_list('actor_id', flat=True))
        approvers = set(stamps.filter(action__in=['reviewed', 'approved']).values_list('actor_id', flat=True))
        if raisers & approvers:
            return False
    return True


def checks(v):
    """Internal Control's checks. Every row must pass before the voucher goes to the Head of Finance."""
    inv = v.invoice
    expected_wht = (v.amount * v.wht_percent / 100).quantize(CENTS, ROUND_HALF_UP)
    paid_before = PaymentVoucher.objects.filter(
        vendor=v.vendor, invoice__vendor_invoice_number__iexact=inv.vendor_invoice_number,
    ).exclude(pk=v.pk).exists() if inv.vendor_invoice_number else False
    rows = [
        ('All four earlier stages approved, with names and time stamps', all(r['ok'] for r in trail(v))),
        ('Nobody approved their own work', _nobody_approved_own_work(v)),
        ('Voucher amount matches the approved invoice', v.amount == inv.subtotal and v.vat == inv.tax_amount),
        (f"No other voucher exists for {inv.vendor_invoice_number or inv.invoice_number}", not paid_before),
        ('VAT and withholding tax calculated correctly',
         v.wht_rate_id is not None and v.wht_amount == expected_wht and v.net_amount == v.amount + v.vat - v.wht_amount),
        ('Vendor bank details on file', v.vendor.has_bank_details),
    ]
    return [{'check': check, 'ok': ok} for check, ok in rows]


def problems(v):
    found = []
    if v.wht_rate_id is None:
        found.append("Choose the withholding tax rate, or None.")
    if not v.payment_method:
        found.append("Choose how it will be paid.")
    if not all(r['ok'] for r in trail(v)):
        found.append("Every earlier stage must be approved before the voucher can be raised.")
    if not v.vendor.has_bank_details:
        found.append("The vendor has no bank details on file. Ask the Super Admin to add them.")
    return found


# ── actions ──────────────────────────────────────────────────────────────────

@transaction.atomic
def submit(v, user):
    _require(v, 'Draft', 'Returned')
    found = problems(v)
    if found:
        raise ActionRefused(' '.join(found))
    action = 'raised' if v.status == 'Draft' else 'resubmitted'
    perform_action(v, STAGE, 'ap_officer', action, user, facility=v.facility)
    _set_status(v, 'Awaiting Review')
    _tell_next(v)


@transaction.atomic
def review(v, user, signature, note=''):
    _require(v, 'Awaiting Review')
    failed = [row['check'] for row in checks(v) if not row['ok']]
    if failed:
        raise ActionRefused("Not every check passes: " + '; '.join(failed) + ". Return it to AP instead.")
    perform_action(v, STAGE, 'reviewer', 'reviewed', user, facility=v.facility, signature=signature, reason=note)
    _set_status(v, 'Awaiting Approval')
    _tell_next(v)


@transaction.atomic
def return_voucher(v, user, reason):
    _require(v, 'Awaiting Review', 'Awaiting Approval')
    perform_action(v, STAGE, waiting_on(v), 'sent_back', user, facility=v.facility, reason=reason)
    _set_status(v, 'Returned')
    _tell_next(v, reason=reason)


@transaction.atomic
def approve(v, user, signature):
    _require(v, 'Awaiting Approval')
    perform_action(v, STAGE, 'head_of_finance', 'approved', user, facility=v.facility, signature=signature,
                   amount=v.net_amount)
    _set_status(v, 'Approved')
    _tell_next(v)


def _can_pay(user, v):
    if user.roles == 'AP OFFICER':
        raise ActionRefused("AP Officers can attach the bank receipt but cannot confirm Paid.")
    if not acting_for(user, 'head_of_finance', v.facility)[0]:
        raise ActionRefused("Only the Head of Finance & Treasury confirms payments.")


@transaction.atomic
def attach_receipt(vouchers, user, upload):
    """AP or the Head of Finance attaches the bank receipt / batch report to vouchers waiting to be paid."""
    if upload is None:
        raise ActionRefused("Choose the bank receipt or batch report to attach.")
    for v in vouchers:
        _require(v, 'Approved', 'Payment Failed')
        if not (acting_for(user, 'ap_officer', v.facility)[0] or acting_for(user, 'head_of_finance', v.facility)[0]):
            raise ActionRefused("Only AP Officers or the Head of Finance & Treasury can attach the bank receipt.")
    for v in vouchers:
        upload.seek(0)
        _attach(v, upload)


@transaction.atomic
def confirm_paid(vouchers, user, *, payment_date, bank_reference):
    """The Head of Finance & Treasury confirms one voucher or a batch as paid. Each gets its own time stamp."""
    if not vouchers:
        raise ActionRefused("Select at least one voucher.")
    parsed = parse_date(payment_date) if isinstance(payment_date, str) else payment_date
    if parsed is None:
        raise ActionRefused("Enter the payment date.")
    if parsed > timezone.localdate():
        raise ActionRefused("The payment date cannot be in the future.")
    if not (bank_reference or '').strip():
        raise ActionRefused("Enter the bank reference.")
    for v in vouchers:
        _require(v, 'Approved', 'Payment Failed')
        _can_pay(user, v)
        if not v.attachments.exists():
            raise ActionRefused(f"{v.voucher_number}: attach the bank receipt or batch report first.")
    now = timezone.now()
    for v in vouchers:
        perform_action(v, STAGE, 'head_of_finance', 'paid', user, facility=v.facility)
        _set_status(v, 'Paid', payment_date=parsed, bank_reference=bank_reference.strip(), paid_at=now, paid_by=user,
                    failure_reason='')
        _close_job(v)
        _tell_next(v)


def _close_job(v):
    """Payment confirmed: the invoice is paid and the job is closed."""
    Invoice.objects.filter(pk=v.invoice_id).update(status='Paid')
    v.work_order.__class__.objects.filter(pk=v.work_order_id).update(work_status='closed')


@transaction.atomic
def payment_failed(v, user, reason):
    _require(v, 'Approved')
    _can_pay(user, v)
    if not (reason or '').strip():
        raise ActionRefused("Say why the payment failed so AP can fix it.")
    perform_action(v, STAGE, 'head_of_finance', 'payment_failed', user, facility=v.facility, reason=reason)
    _set_status(v, 'Payment Failed', failure_reason=reason.strip())
    _tell_next(v, reason=reason)


# ── who sees and acts ────────────────────────────────────────────────────────

def people_for(v, slot):
    if slot in ('ap_officer', 'reviewer'):
        return list(team_members(slot))
    if slot == 'contractor':
        return list(get_user_model().objects.filter(roles='CONTRACTOR', vendor=v.vendor, is_active=True))
    return stage1.people_for(v.work_order, slot)


def available_actions(v, user):
    slot = waiting_on(v)
    if slot is None:
        return []
    if v.status in ('Approved', 'Payment Failed'):
        if user.roles != 'AP OFFICER' and acting_for(user, 'head_of_finance', v.facility)[0]:
            return ['pay', 'payment_failed'] if v.status == 'Approved' else ['pay']
        if acting_for(user, 'ap_officer', v.facility)[0]:
            return ['attach_receipt']
        return []
    if not acting_for(user, slot, v.facility)[0]:
        return []
    if v.status in ('Draft', 'Returned'):
        return ['edit', 'submit']
    if history(v).filter(actor=user, action__in=['raised', 'resubmitted', 'reviewed']).exists():
        return []
    return ['review', 'return'] if slot == 'reviewer' else ['approve', 'return']


def timing(v):
    if v.status not in ('Awaiting Review', 'Returned', 'Awaiting Approval'):
        return None
    first = history(v).filter(action='raised').first()
    if first is None:
        return None
    client = v.facility.client if v.facility_id else None
    return {**step_timing(STAGE, first.at, client), 'started_at': first.at}


def to_pay(user):
    """Approved vouchers waiting to be paid: for the Head of Finance & Treasury (and AP, to attach receipts)."""
    vouchers = (PaymentVoucher.objects.filter(status__in=['Approved', 'Payment Failed'])
                .select_related('vendor', 'invoice', 'facility', 'work_order').order_by('updated_at'))
    return [v for v in vouchers if available_actions(v, user)]


def my_tasks(user):
    tasks = [{'kind': 'voucher_to_raise', 'invoice': inv, 'step': 'ap_officer'} for inv in to_raise(user)]
    candidates = (PaymentVoucher.objects.exclude(status='Paid')
                  .select_related('facility', 'facility__client', 'vendor', 'invoice', 'work_order').order_by('updated_at'))
    for v in candidates:
        actions = available_actions(v, user)
        if not actions or actions == ['attach_receipt']:
            continue
        slot = waiting_on(v)
        on_behalf_of = acting_for(user, slot, v.facility)[1]
        tasks.append({'kind': 'voucher', 'voucher': v, 'step': slot, 'on_behalf_of': on_behalf_of, 'timing': timing(v)})
    return tasks


def remittance(v):
    """What the vendor sees once paid."""
    return {
        'voucher_number': v.voucher_number, 'paid_at': v.paid_at, 'payment_date': v.payment_date,
        'bank_reference': v.bank_reference, 'bank': v.vendor.bank,
        'account_last4': (v.vendor.account_number or '')[-4:],
        'invoice': v.invoice.vendor_invoice_number or v.invoice.invoice_number,
        'amount': str(v.amount), 'vat': str(v.vat), 'wht_percent': str(v.wht_percent),
        'wht_amount': str(v.wht_amount), 'net_amount': str(v.net_amount),
    }


# ── telling people ───────────────────────────────────────────────────────────

MESSAGES = {
    'Awaiting Review': ("Payment voucher to check", "AP raised a payment voucher. It is waiting for your control check."),
    'Awaiting Approval': ("Payment to approve", "Internal Control checked a payment voucher. It is waiting for your approval."),
    'Returned': ("Payment voucher returned", "A payment voucher was returned. Please correct it and resubmit."),
    'Approved': ("Payment to make", "A payment is approved. Pay it in the bank, then confirm Paid."),
    'Payment Failed': ("Payment failed", "A payment did not go through. Please check the vendor's details."),
    'Paid': ("Payment made", "The payment has been made. The remittance advice is attached to the job."),
}


def _recipients(v):
    if v.status == 'Paid':
        return people_for(v, 'contractor') + people_for(v, 'ap_officer')
    if v.status == 'Payment Failed':
        return people_for(v, 'ap_officer')
    return people_for(v, waiting_on(v))


def _tell_next(v, reason=''):
    from work.utils.email_service import create_in_app_notifications, send_notification_email

    headline, message = MESSAGES[v.status]
    recipients = list({u.pk: u for u in _recipients(v) if u.is_active}.values())

    def _go():
        create_in_app_notifications(recipients, title=f"{headline} · {v.voucher_number}",
                                    message=message, notification_type='PAYMENT_REQUISITION', object_id=v.pk)
        send_notification_email(
            subject=f"[AlphaCMMS] {headline} · {v.voucher_number}",
            template='emails/payment_flow.html',
            context={'instance': v, 'headline': headline, 'message': message, 'reason': reason},
            recipient_list=[u.email for u in recipients if u.email],
        )

    transaction.on_commit(_go)
