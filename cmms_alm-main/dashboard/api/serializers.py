# serializers.py
from rest_framework import serializers
from work.models import WorkRequest, WorkOrder, PaymentRequisition, PPM


class DashboardCardSerializer(serializers.Serializer):
    """
    Serializer for dashboard card items which include a count and associated metadata.
    """
    count = serializers.IntegerField()
    label = serializers.CharField()
    subtitle = serializers.CharField(required=False)
    icon = serializers.CharField(required=False)
    color = serializers.CharField(required=False)


class DashboardSectionSerializer(serializers.Serializer):
    """
    Serializer for dashboard sections which contain multiple cards.
    """
    title = serializers.CharField()
    cards = DashboardCardSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    """
    Main dashboard serializer containing all sections.
    """
    escalated_to_me = DashboardCardSerializer(many=True)
    ppm_due = DashboardCardSerializer(many=True)
    work_request = DashboardCardSerializer(many=True)
    work_order = DashboardCardSerializer(many=True)
    payment_requisition = DashboardCardSerializer(many=True)