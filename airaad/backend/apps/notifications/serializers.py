"""
Notifications App Serializers
"""

from rest_framework import serializers
from .models import NotificationTemplate, NotificationLog


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'slug', 'title_template', 'body_template', 'notification_type',
            'is_active', 'created_at'
        ]


class NotificationLogSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.slug', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'template', 'template_name', 'recipient_type', 'recipient_id',
            'title', 'body', 'channel', 'status', 'error_message', 'sent_at', 'created_at'
        ]
