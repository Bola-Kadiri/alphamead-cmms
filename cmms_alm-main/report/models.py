from django.conf import settings
from django.db import models


class UserLoginLog(models.Model):
    """
    Append-only record of a successful login.

    Populated by ``report.signals`` in response to Django's built-in
    ``user_logged_in`` signal, which fires for both the session-based web
    login (accounts.views.LoginView) and the JWT login endpoint
    (utils.views.CustomTokenObtainPairView emits it manually — see
    utils.serializers.CustomTokenObtainPairSerializer.get_token). This is
    the data source for the "Login count" column on the User Facility
    Report and is intentionally generic enough to back a future User
    Audit Report ("Authentication" module) without another migration.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_logs',
        help_text='The user who logged in.',
    )
    login_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text='Client IP address at login time, when available.',
    )

    class Meta:
        ordering = ['-login_at']
        indexes = [
            models.Index(fields=['user', 'login_at']),
        ]

    def __str__(self):
        return f"{self.user} @ {self.login_at:%Y-%m-%d %H:%M}"
