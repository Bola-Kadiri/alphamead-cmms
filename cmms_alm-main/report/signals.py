from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import UserLoginLog


def _client_ip(request):
    if request is None:
        return None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    """
    Record every successful login so the User Facility Report's login
    count stays accurate. ``request`` is None for the JWT login path
    (see utils.serializers.CustomTokenObtainPairSerializer), so the IP
    is simply omitted there.
    """
    UserLoginLog.objects.create(user=user, ip_address=_client_ip(request))
