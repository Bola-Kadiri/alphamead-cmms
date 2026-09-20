from rest_framework import serializers

from facility.models import Facility


class UserFacilityReportSerializer(serializers.Serializer):
    """
    One row of the User Facility Report.

    Source is the annotated User queryset from report.services — the
    count fields read straight off the query annotations, not model
    fields, so this is a plain Serializer rather than a ModelSerializer.
    """
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    facilities = serializers.SerializerMethodField()
    facilities_inferred = serializers.SerializerMethodField()
    login_count = serializers.IntegerField()
    work_request_count = serializers.IntegerField()
    item_request_count = serializers.IntegerField()
    visitor_pass_count = serializers.SerializerMethodField()

    def _resolve_facilities(self, obj):
        """
        Cached per-row so get_facilities and get_facilities_inferred (both
        called independently by DRF) don't run the fallback query twice.
        Returns (names, was_inferred).
        """
        if not hasattr(obj, '_report_facilities_cache'):
            names = list(obj.facility.values_list('name', flat=True))
            inferred = False
            if not names:
                # No explicit facility assignment exists for this user —
                # true for every user in this system today (neither
                # User.facility nor accounts.Personnel.facility is
                # populated yet). Fall back to facilities inferred from
                # their own work request history, so the column isn't
                # uniformly empty just because assignment data hasn't
                # been entered anywhere.
                names = list(
                    Facility.objects.filter(work_requests__requester_id=obj.id)
                    .distinct()
                    .values_list('name', flat=True)
                )
                inferred = bool(names)
            obj._report_facilities_cache = (names, inferred)
        return obj._report_facilities_cache

    def get_facilities(self, obj):
        names, _ = self._resolve_facilities(obj)
        return names

    def get_facilities_inferred(self, obj):
        # True when `facilities` came from work-request history rather
        # than an explicit assignment — the frontend uses this to mark
        # those badges distinctly rather than presenting them as fact.
        _, inferred = self._resolve_facilities(obj)
        return inferred

    def get_visitor_pass_count(self, obj):
        # No visitor-pass feature exists in the system yet. Returning
        # null (not 0) lets the frontend show "N/A" instead of implying
        # a real, counted zero.
        return None
