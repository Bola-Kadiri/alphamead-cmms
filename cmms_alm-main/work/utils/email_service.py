import threading
import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_email(subject, html_content, recipient_list):
    """Send an HTML email. Runs in a background thread so it never blocks the API."""
    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        text_content = subject  # plain fallback
        msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.error('Email send failed to %s: %s', recipient_list, exc)


def send_notification_email(subject, template, context, recipient_list):
    """
    Render a template and dispatch the email in a daemon thread.
    Never raises — failures are logged and swallowed.
    """
    if not recipient_list:
        return
    try:
        from django.conf import settings
        login_url = getattr(settings, 'BASE_URL', '').rstrip('/') + '/login#'
        context = {**context, 'login_url': login_url}
        html_content = render_to_string(template, context)
    except Exception as exc:
        logger.error('Email template render failed (%s): %s', template, exc)
        return
    thread = threading.Thread(
        target=_send_email,
        args=(subject, html_content, recipient_list),
        daemon=True,
    )
    thread.start()


def create_in_app_notifications(recipients, title, message, notification_type, object_id=None):
    """
    Bulk-create in-app Notification records for a list of user instances.
    Import is deferred to avoid circular imports at module load time.
    """
    from work.models.notification import Notification
    notifications = [
        Notification(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            object_id=object_id,
        )
        for user in recipients
        if user and getattr(user, 'email', None)
    ]
    if notifications:
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)
