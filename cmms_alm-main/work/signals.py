"""
Email & in-app notification signals for all work modules.

Strategy
--------
- pre_save  → capture the previous approval_status so we can detect changes.
- post_save → after the save commits (transaction.on_commit), query M2M fields
              (which are now guaranteed to be written by DRF) and dispatch.
- All email sends are fire-and-forget daemon threads; failures are logged only.
- Nothing in this file touches existing model / view / serializer logic.
"""

import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver

from work.models.work_request import WorkRequest
from work.models.work_order import WorkOrder
from work.models.work_order_completion import WorkOrderCompletion
from work.models.payment_requisition import PaymentRequisition
from work.utils.email_service import send_notification_email, create_in_app_notifications

logger = logging.getLogger(__name__)
User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_prev_status: dict = {}


def _cache_key(model_name, pk):
    return f'{model_name}_{pk}'


def _emails(queryset_or_user):
    """Return a list of non-empty email addresses from a queryset or single user."""
    if queryset_or_user is None:
        return []
    if hasattr(queryset_or_user, 'values_list'):
        return list(queryset_or_user.values_list('email', flat=True).exclude(email=''))
    email = getattr(queryset_or_user, 'email', None)
    return [email] if email else []


def _users(queryset_or_user):
    """Return a list of user instances."""
    if queryset_or_user is None:
        return []
    if hasattr(queryset_or_user, 'all'):
        return list(queryset_or_user.all())
    return [queryset_or_user] if queryset_or_user else []


# ===========================================================================
# WORK REQUEST
# ===========================================================================

@receiver(pre_save, sender=WorkRequest)
def cache_work_request_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('approval_status', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('wr', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=WorkRequest)
def on_work_request_saved(sender, instance, created, **kwargs):
    key = _cache_key('wr', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.approval_status
    # Five-stage requests tell people themselves (work.models.work_request_flow).
    if instance.flow == WorkRequest.FIVE_STAGE:
        return

    def _notify():
        try:
            fresh = WorkRequest.objects.get(pk=instance.pk)
            ctx = {'instance': fresh}

            if created:
                # Nobody is routed at creation any more, so route the
                # notification instead: if no Procurement & Store handler
                # was set, broadcast to every PROCUREMENT AND STORE user —
                # whoever picks it up first claims it (see save_quotation /
                # cp_approve). Reviewers aren't chosen until after
                # Procurement & Store has priced it, so there's normally
                # none to notify yet.
                procurement_recipients = list(fresh.request_to.all())
                if not procurement_recipients:
                    procurement_recipients = list(User.objects.filter(roles='PROCUREMENT AND STORE'))
                recipients = procurement_recipients + list(fresh.reviewers.all())
                emails = [u.email for u in procurement_recipients if u.email] + _emails(fresh.reviewers)
                if emails:
                    send_notification_email(
                        subject=f'[AlphaCMMS] New Work Request {fresh.work_request_number} — Action Required',
                        template='emails/work_request_pending_review.html',
                        context=ctx,
                        recipient_list=emails,
                    )
                create_in_app_notifications(
                    recipients=recipients,
                    title=f'New Work Request: {fresh.work_request_number}',
                    message='A new work request is pending your review.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )
                return

            if previous == current:
                return

            if current == 'CP Approved':
                emails = _emails(fresh.reviewers)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Ready for Review',
                    template='emails/work_request_cp_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.reviewers),
                    title=f'Work Request {fresh.work_request_number} Ready for Review',
                    message='Procurement & Store has processed a work request awaiting your review.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )
                # Also tell the Requester their cost has been imputed —
                # separate from the Reviewer notification above.
                requester_emails = _emails(fresh.requester)
                if requester_emails:
                    send_notification_email(
                        subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Cost Imputed',
                        template='emails/work_request_cost_imputed.html',
                        context=ctx,
                        recipient_list=requester_emails,
                    )
                create_in_app_notifications(
                    recipients=_users(fresh.requester),
                    title=f'Work Request {fresh.work_request_number} — Cost Imputed',
                    message='Procurement & Store has priced your work request.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )

            elif current == 'Reviewed':
                emails = _emails(fresh.approver)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Awaiting Your Approval',
                    template='emails/work_request_reviewed.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.approver),
                    title=f'Work Request {fresh.work_request_number} Awaiting Approval',
                    message='A work request has been reviewed and needs your approval.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )

            elif current == 'Fully Approved':
                emails = _emails(fresh.requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Approved',
                    template='emails/work_request_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.requester),
                    title=f'Work Request {fresh.work_request_number} Approved',
                    message='Your work request has been fully approved.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )

            elif current in ('Reviewer Rejected', 'Approver Rejected', 'Rejected – Vendor Changed'):
                emails = _emails(fresh.requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Rejected',
                    template='emails/work_request_rejected.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.requester),
                    title=f'Work Request {fresh.work_request_number} Rejected',
                    message=f'Your work request has been rejected ({current}).',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )

            elif (
                current == 'Pending Review'
                and previous in ('Reviewer Rejected', 'Approver Rejected', 'Rejected – Vendor Changed')
            ):
                # Requester edited and resubmitted after rejection — notify Procurement & Store
                recipients = list(fresh.request_to.all())
                emails = _emails(fresh.request_to)
                if emails:
                    send_notification_email(
                        subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Updated & Awaiting Your Review',
                        template='emails/work_request_pending_review.html',
                        context=ctx,
                        recipient_list=emails,
                    )
                create_in_app_notifications(
                    recipients=recipients,
                    title=f'Work Request {fresh.work_request_number} Updated & Resubmitted',
                    message='The requester has updated this work request and it is awaiting your review.',
                    notification_type='WORK_REQUEST',
                    object_id=fresh.pk,
                )

        except Exception as exc:
            logger.error('WorkRequest notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


@receiver(m2m_changed, sender=WorkRequest.reviewers.through)
def on_work_request_reviewers_changed(sender, instance, action, pk_set, **kwargs):
    """
    Reviewer + Approver aren't chosen at creation any more — the Requester
    adds them later, via Edit, once Procurement & Store has priced the
    request (status stays 'CP Approved' throughout that edit, so the
    status-transition notification above never fires for it). This fires
    on that specific M2M write instead, which post_save can't observe
    reliably since DRF's serializer.update() calls reviewers.set() after
    instance.save() already ran.
    """
    if action != 'post_add' or not pk_set:
        return
    if instance.approval_status != 'CP Approved':
        return

    def _notify():
        try:
            fresh = WorkRequest.objects.get(pk=instance.pk)
            new_reviewers = list(User.objects.filter(pk__in=pk_set))
            emails = [u.email for u in new_reviewers if u.email]
            ctx = {'instance': fresh}
            if emails:
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Request {fresh.work_request_number} — Ready for Review',
                    template='emails/work_request_cp_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
            create_in_app_notifications(
                recipients=new_reviewers,
                title=f'Work Request {fresh.work_request_number} Ready for Review',
                message='A work request has been routed to you for review.',
                notification_type='WORK_REQUEST',
                object_id=fresh.pk,
            )
        except Exception as exc:
            logger.error('WorkRequest reviewer-assignment notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


# ===========================================================================
# WORK ORDER
# ===========================================================================

def _procurement_team():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(roles='PROCUREMENT AND STORE', is_active=True)


def _raise_payment_action(work_order, recipients, headline, message):
    """Raise Payment approver-first route: tell whoever acts next that it's their turn."""
    users = _users(recipients)
    send_notification_email(
        subject=f'[AlphaCMMS] Raise Payment {work_order.work_order_number} — {headline}',
        template='emails/raise_payment_action_required.html',
        context={'instance': work_order, 'headline': headline, 'message': message},
        recipient_list=[u.email for u in users if u.email],
    )
    create_in_app_notifications(
        recipients=users,
        title=f'Raise Payment {work_order.work_order_number}: {headline}',
        message=message,
        notification_type='WORK_ORDER',
        object_id=work_order.pk,
    )


@receiver(pre_save, sender=WorkOrder)
def cache_work_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('approval_status', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('wo', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=WorkOrder)
def on_work_order_saved(sender, instance, created, **kwargs):
    key = _cache_key('wo', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.approval_status
    # Five-stage work orders tell people themselves (work.models.work_order_flow).
    if instance.flow == WorkOrder.FIVE_STAGE:
        return

    def _notify():
        try:
            fresh = WorkOrder.objects.get(pk=instance.pk)
            ctx = {'instance': fresh}

            if fresh.is_approver_first and current == 'Awaiting Procurement' and (created or previous != current):
                _raise_payment_action(
                    fresh, _procurement_team(), 'PO and Quotation Needed',
                    'A Raise Payment bill needs its PO number and quotation before the Approver can act.',
                )
                return

            if created and fresh.is_approver_first:
                _raise_payment_action(
                    fresh, fresh.approver, 'Awaiting Your Approval',
                    'A Raise Payment bill has been raised and needs your approval. The Reviewer acts after you.',
                )
                return

            if created:
                emails = _emails(fresh.reviewers)
                send_notification_email(
                    subject=f'[AlphaCMMS] New Work Order {fresh.work_order_number} — Review Required',
                    template='emails/work_order_created.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.reviewers),
                    title=f'New Work Order: {fresh.work_order_number}',
                    message='A new work order is pending your review.',
                    notification_type='WORK_ORDER',
                    object_id=fresh.pk,
                )
                return

            if previous == current:
                return

            if fresh.is_approver_first and current == 'Pending' and previous in ('Awaiting Procurement', 'Procurement Returned'):
                _raise_payment_action(
                    fresh, fresh.approver, 'Awaiting Your Approval',
                    'A Raise Payment bill is ready for your approval. The Reviewer acts after you.',
                )
                return

            if fresh.is_approver_first and current == 'Procurement Returned':
                _raise_payment_action(
                    fresh, fresh.owner or fresh.requester, 'Returned by Procurement',
                    f'Procurement & Store returned this Raise Payment bill: {fresh.procurement_reason}. '
                    'Please fix it and resubmit.',
                )
                return

            if fresh.is_approver_first and current == 'Approver Approved':
                _raise_payment_action(
                    fresh, fresh.reviewers, 'Awaiting Your Review',
                    'The Approver has approved this Raise Payment bill. It now needs your review.',
                )
                return

            if fresh.is_approver_first and current == 'Awaiting Final Approval':
                _raise_payment_action(
                    fresh, fresh.final_approver, 'Awaiting Your Final Approval',
                    'This Raise Payment bill has been approved and reviewed. Because of its amount it needs '
                    'your final approval before the payment is raised.',
                )
                return

            if current == 'Reviewed':
                emails = _emails(fresh.approver)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Order {fresh.work_order_number} — Awaiting Your Approval',
                    template='emails/work_order_reviewed.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.approver),
                    title=f'Work Order {fresh.work_order_number} Awaiting Approval',
                    message='A work order has been reviewed and needs your approval.',
                    notification_type='WORK_ORDER',
                    object_id=fresh.pk,
                )

            elif current == 'Approved':
                emails = _emails(fresh.requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Order {fresh.work_order_number} — Approved',
                    template='emails/work_order_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.requester),
                    title=f'Work Order {fresh.work_order_number} Approved',
                    message='A work order has been approved.',
                    notification_type='WORK_ORDER',
                    object_id=fresh.pk,
                )

            elif current in ('Reviewer Rejected', 'Approver Rejected', 'Rejected', 'Final Approver Rejected'):
                emails = _emails(fresh.requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Order {fresh.work_order_number} — Rejected',
                    template='emails/work_order_rejected.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.requester),
                    title=f'Work Order {fresh.work_order_number} Rejected',
                    message=f'A work order has been rejected ({current}).',
                    notification_type='WORK_ORDER',
                    object_id=fresh.pk,
                )

        except Exception as exc:
            logger.error('WorkOrder notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


# work_status (Closed/Pending/Rejected) is tracked separately from
# approval_status — see WorkOrderViewSet.set_status — so it needs its own
# change-detection cache to notify on closing.

@receiver(pre_save, sender=WorkOrder)
def cache_work_order_work_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('work_status', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('wo_work_status', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=WorkOrder)
def on_work_order_work_status_saved(sender, instance, created, **kwargs):
    key = _cache_key('wo_work_status', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.work_status

    if created or previous == current or current != 'closed':
        return

    def _notify():
        try:
            fresh = WorkOrder.objects.select_related('requester').get(pk=instance.pk)
            ctx = {'instance': fresh}
            emails = _emails(fresh.requester)
            if emails:
                send_notification_email(
                    subject=f'[AlphaCMMS] Work Order {fresh.work_order_number} — Closed',
                    template='emails/work_order_closed.html',
                    context=ctx,
                    recipient_list=emails,
                )
            create_in_app_notifications(
                recipients=_users(fresh.requester),
                title=f'Work Order {fresh.work_order_number} Closed',
                message='The work order has been closed and a payment requisition has been raised.',
                notification_type='WORK_ORDER',
                object_id=fresh.pk,
            )
        except Exception as exc:
            logger.error('WorkOrder closure notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


# ===========================================================================
# WORK ORDER COMPLETION (WCC)
# ===========================================================================

@receiver(pre_save, sender=WorkOrderCompletion)
def cache_wcc_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('approval_status', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('wcc', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=WorkOrderCompletion)
def on_wcc_saved(sender, instance, created, **kwargs):
    key = _cache_key('wcc', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.approval_status
    # Five-stage certificates tell people themselves (work.models.completion_flow).
    if instance.flow == WorkOrderCompletion.FIVE_STAGE:
        return

    def _notify():
        try:
            fresh = WorkOrderCompletion.objects.select_related('work_order__requester').get(pk=instance.pk)
            ctx = {'instance': fresh}
            requester = fresh.work_order.requester

            if created:
                emails = _emails(fresh.reviewers)
                send_notification_email(
                    subject=f'[AlphaCMMS] WCC for Work Order {fresh.work_order.work_order_number} — Review Required',
                    template='emails/wcc_created.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.reviewers),
                    title=f'WCC Pending Review: WO {fresh.work_order.work_order_number}',
                    message='A Work Completion Certificate is pending your review.',
                    notification_type='WCC',
                    object_id=fresh.pk,
                )
                return

            if previous == current:
                return

            if current == 'Reviewed':
                emails = _emails(fresh.approver)
                send_notification_email(
                    subject=f'[AlphaCMMS] WCC for Work Order {fresh.work_order.work_order_number} — Awaiting Approval',
                    template='emails/wcc_reviewed.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.approver),
                    title=f'WCC Awaiting Approval: WO {fresh.work_order.work_order_number}',
                    message='A WCC has been reviewed and needs your approval.',
                    notification_type='WCC',
                    object_id=fresh.pk,
                )

            elif current == 'Approved':
                emails = _emails(requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] WCC Approved — Work Order {fresh.work_order.work_order_number}',
                    template='emails/wcc_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(requester),
                    title=f'WCC Approved: WO {fresh.work_order.work_order_number}',
                    message='The Work Completion Certificate has been approved.',
                    notification_type='WCC',
                    object_id=fresh.pk,
                )

            elif current in ('Reviewer Rejected', 'Approver Rejected'):
                emails = _emails(requester)
                send_notification_email(
                    subject=f'[AlphaCMMS] WCC Rejected — Work Order {fresh.work_order.work_order_number}',
                    template='emails/wcc_rejected.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(requester),
                    title=f'WCC Rejected: WO {fresh.work_order.work_order_number}',
                    message=f'The Work Completion Certificate has been rejected ({current}).',
                    notification_type='WCC',
                    object_id=fresh.pk,
                )

        except Exception as exc:
            logger.error('WCC notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


# ===========================================================================
# PAYMENT REQUISITION
# ===========================================================================

@receiver(pre_save, sender=PaymentRequisition)
def cache_payment_requisition_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('approval_status', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('pr', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=PaymentRequisition)
def on_payment_requisition_saved(sender, instance, created, **kwargs):
    key = _cache_key('pr', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.approval_status

    def _notify():
        try:
            fresh = PaymentRequisition.objects.select_related('owner').get(pk=instance.pk)
            ctx = {'instance': fresh}

            if created:
                emails = _emails(fresh.request_to)
                send_notification_email(
                    subject=f'[AlphaCMMS] Payment Requisition {fresh.requisition_number or fresh.pk} — Approval Required',
                    template='emails/payment_requisition_submitted.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.request_to),
                    title=f'Payment Requisition Pending Approval: {fresh.requisition_number or fresh.pk}',
                    message='A payment requisition requires your approval.',
                    notification_type='PAYMENT_REQUISITION',
                    object_id=fresh.pk,
                )
                return

            if previous == current:
                return

            if current == 'approve':
                emails = _emails(fresh.owner)
                send_notification_email(
                    subject=f'[AlphaCMMS] Payment Requisition {fresh.requisition_number or fresh.pk} — Approved',
                    template='emails/payment_requisition_approved.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.owner),
                    title=f'Payment Requisition Approved: {fresh.requisition_number or fresh.pk}',
                    message='Your payment requisition has been approved.',
                    notification_type='PAYMENT_REQUISITION',
                    object_id=fresh.pk,
                )

            elif current == 'reject':
                emails = _emails(fresh.owner)
                send_notification_email(
                    subject=f'[AlphaCMMS] Payment Requisition {fresh.requisition_number or fresh.pk} — Rejected',
                    template='emails/payment_requisition_rejected.html',
                    context=ctx,
                    recipient_list=emails,
                )
                create_in_app_notifications(
                    recipients=_users(fresh.owner),
                    title=f'Payment Requisition Rejected: {fresh.requisition_number or fresh.pk}',
                    message='Your payment requisition has been rejected.',
                    notification_type='PAYMENT_REQUISITION',
                    object_id=fresh.pk,
                )

        except Exception as exc:
            logger.error('PaymentRequisition notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)


# is_disbursed is a separate boolean, not part of approval_status — see
# PaymentRequisitionViewSet.disburse — so it needs its own change-detection
# cache to notify once Finance disburses.

@receiver(pre_save, sender=PaymentRequisition)
def cache_payment_requisition_disbursed(sender, instance, **kwargs):
    if instance.pk:
        try:
            prev = sender.objects.values_list('is_disbursed', flat=True).get(pk=instance.pk)
            _prev_status[_cache_key('pr_disbursed', instance.pk)] = prev
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=PaymentRequisition)
def on_payment_requisition_disbursed(sender, instance, created, **kwargs):
    key = _cache_key('pr_disbursed', instance.pk)
    previous = _prev_status.pop(key, None)
    current = instance.is_disbursed

    if created or previous == current or not current:
        return

    def _notify():
        try:
            fresh = PaymentRequisition.objects.select_related('owner').get(pk=instance.pk)
            ctx = {'instance': fresh}
            emails = _emails(fresh.owner)
            if emails:
                send_notification_email(
                    subject=f'[AlphaCMMS] Payment Requisition {fresh.requisition_number or fresh.pk} — Disbursed',
                    template='emails/payment_requisition_disbursed.html',
                    context=ctx,
                    recipient_list=emails,
                )
            create_in_app_notifications(
                recipients=_users(fresh.owner),
                title=f'Payment Requisition Disbursed: {fresh.requisition_number or fresh.pk}',
                message='Finance has disbursed this payment. The record is now locked.',
                notification_type='PAYMENT_REQUISITION',
                object_id=fresh.pk,
            )
        except Exception as exc:
            logger.error('PaymentRequisition disbursement notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)
