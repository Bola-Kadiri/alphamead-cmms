from work.models.notification import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {'navbar_notifications': [], 'navbar_unread_count': 0}

    qs = Notification.objects.filter(recipient=request.user)
    unread_count = qs.filter(is_read=False).count()
    recent = qs.filter(is_read=False)[:5]

    return {
        'navbar_notifications': recent,
        'navbar_unread_count': unread_count,
    }
