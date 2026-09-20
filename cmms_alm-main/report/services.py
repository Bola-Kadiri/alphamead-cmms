from django.contrib.auth import get_user_model
from django.db.models import Count, Q

User = get_user_model()


def get_user_facility_report_queryset(facility_id=None, search=None):
    """
    Build the annotated User queryset backing the User Facility Report.

    Each count is annotated with ``distinct=True``. Combining several
    reverse-relation Count() aggregates on one queryset otherwise inflates
    every figure through JOIN fan-out (Django's well-documented
    multi-aggregate pitfall) — distinct=True on each Count is the
    documented fix.

    ``visitor_pass_count`` is deliberately absent: there is no visitor
    pass feature anywhere in this codebase yet, so nothing to count.
    The serializer surfaces that column as null ("N/A"), not a fabricated
    zero, until that feature exists.
    """
    queryset = User.objects.all()

    if facility_id:
        queryset = queryset.filter(facility__id=facility_id)

    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    return queryset.annotate(
        login_count=Count('login_logs', distinct=True),
        work_request_count=Count('work_requests', distinct=True),
        item_request_count=Count('requested_items', distinct=True),
    ).order_by('-login_count', 'first_name', 'last_name')
