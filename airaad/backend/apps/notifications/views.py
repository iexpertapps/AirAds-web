"""
Notifications App Views
Templates and delivery history for admin portal
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from apps.notifications.models import NotificationTemplate, NotificationLog
from apps.notifications.serializers import (
    NotificationTemplateSerializer,
    NotificationLogSerializer,
)
from core.exceptions import success_response


class NotificationTemplateListView(APIView):
    """
    GET /api/v1/notifications/templates/
    List all notification templates
    """
    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.OPERATIONS_MANAGER,
        )
    ]

    def get(self, request):
        templates = NotificationTemplate.objects.all().order_by('slug')
        serializer = NotificationTemplateSerializer(templates, many=True)
        return success_response(data=serializer.data)


class NotificationLogListView(APIView):
    """
    GET /api/v1/notifications/logs/
    List notification delivery history
    """
    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.OPERATIONS_MANAGER,
        )
    ]

    def get(self, request):
        logs = NotificationLog.objects.select_related(
            'template'
        ).order_by('-created_at')[:100]
        serializer = NotificationLogSerializer(logs, many=True)
        return success_response(data={"results": serializer.data, "count": len(serializer.data)})
