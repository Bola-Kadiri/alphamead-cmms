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
from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from work.models.work_request import WorkRequest
from work.models.work_order import WorkOrder
from work.models.work_order_completion import WorkOrderCompletion
from work.models.payment_requisition import PaymentRequisition
from work.utils.email_service import send_notification_email, create_in_app_notifications

logger = logging.getLogger(__name__)

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

    def _notify():
        try:
            fresh = WorkRequest.objects.get(pk=instance.pk)
            ctx = {'instance': fresh}

            if created:
                # Notify Procurement & Store + Reviewers
                recipients = list(fresh.request_to.all()) + list(fresh.reviewers.all())
                emails = _emails(fresh.request_to) + _emails(fresh.reviewers)
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


# ===========================================================================
# WORK ORDER
# ===========================================================================

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

    def _notify():
        try:
            fresh = WorkOrder.objects.get(pk=instance.pk)
            ctx = {'instance': fresh}

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

            elif current in ('Reviewer Rejected', 'Approver Rejected', 'Rejected'):
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

        except Exception as exc:
            logger.error('PaymentRequisition notification error (pk=%s): %s', instance.pk, exc)

    transaction.on_commit(_notify)
