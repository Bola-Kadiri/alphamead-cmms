from rest_framework import serializers
from work.models.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'object_id', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'object_id', 'created_at']
