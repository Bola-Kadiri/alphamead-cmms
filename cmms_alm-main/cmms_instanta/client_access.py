"""
Read-only, default-deny access for users with the CLIENT role.

A CLIENT may only reach the endpoints named in CLIENT_ALLOWED (by URL name), and
only with the methods listed there — everything else (every create, edit,
approve, reject, delete, upload, and every list/lookup not explicitly allowed)
gets 403. What they see on the allowed endpoints is further scoped to their
client's facilities inside each viewset (see cmms_instanta.permissions.
accessible_facilities), and costs are masked in the serializers.

Works for both JWT (React app) and session (Django pages) logins. Users with
any other role are untouched.
"""
from django.conf import settings
from django.http import JsonResponse
from django.urls import Resolver404, resolve

SAFE = frozenset({'GET', 'HEAD', 'OPTIONS'})
ANY = frozenset({'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE'})

CLIENT_ALLOWED = {
    # Log in, refresh, password reset.
    'token_obtain_pair': ANY,
    'token_refresh': ANY,
    'token_verify': ANY,
    'password_reset': ANY,
    'password_reset_confirm': ANY,
    # Their facilities' work — read only.
    'work-request-list': SAFE,
    'work-request-detail': SAFE,
    'workorder-list': SAFE,
    'workorder-detail': SAFE,
    'workordercompletion-list': SAFE,
    'workordercompletion-detail': SAFE,
    # Their facilities and the category names shown on records.
    'facility-list': SAFE,
    'facility-detail': SAFE,
    'asset-category-list': SAFE,
    'asset-category-detail': SAFE,
    'asset-subcategory-list': SAFE,
    'asset-subcategory-detail': SAFE,
    # Their own notifications (marking read only changes their own records).
    'notification-list': SAFE,
    'notification-detail': SAFE,
    'notification-unread-count': SAFE,
    'notification-mark-read': ANY,
    'notification-mark-all-read': ANY,
    # Client dashboard (Phase 2).
    'client-dashboard': SAFE,
    # Cover while away: a Client Contract Rep names a stand-in for their sign-offs.
    'delegation-list': ANY,
    'delegation-detail': SAFE,
    'delegation-end': ANY,
    'delegation-stand-ins': SAFE,
    # Five-stage flow: the client approves or rejects Work Requests and sees what waits on them.
    'work-request-flow': SAFE,
    'work-request-flow-approve': ANY,
    'work-request-flow-reject': ANY,
    'my-tasks': SAFE,
}

DENIED_MESSAGE = "Client accounts have view-only access to their own facilities."


def _jwt_user(request):
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        result = JWTAuthentication().authenticate(request)
    except Exception:  # invalid/expired token — let the view return its normal 401
        return None
    return result[0] if result else None


def client_request_allowed(path, method):
    media_url = getattr(settings, 'MEDIA_URL', '/media/') or '/media/'
    if path.startswith(media_url):
        return method in SAFE  # uploaded files, e.g. WCC photos
    try:
        match = resolve(path)
    except Resolver404:
        return True  # unknown URL: the normal 404 applies
    allowed_methods = CLIENT_ALLOWED.get(match.url_name)
    return bool(allowed_methods) and method in allowed_methods


class ClientAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            user = _jwt_user(request)
        if user is not None and getattr(user, 'roles', None) == 'CLIENT':
            if not client_request_allowed(request.path_info, request.method):
                return JsonResponse({'detail': DENIED_MESSAGE}, status=403)
        return self.get_response(request)
