from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from .alert_service import alert_service, Alert, AlertSeverity, AlertStatus
from .logging import structured_logger


@method_decorator(csrf_exempt, name='dispatch')
class AlertTriggerView(View):
    """
    Manual alert trigger endpoint.
    Allows manual triggering of alerts for testing.
    """
    
    def post(self, request):
        """Manually trigger an alert."""
        try:
            import json
            data = json.loads(request.body)
            
            alert = Alert(
                id=data.get('id', f"manual_{int(timezone.now().timestamp())}"),
                title=data.get('title', 'Manual Alert'),
                message=data.get('message', 'Manually triggered alert'),
                severity=AlertSeverity(data.get('severity', 'MEDIUM')),
                component=data.get('component', 'manual'),
                timestamp=timezone.now(),
                metadata=data.get('metadata', {}),
                tags=data.get('tags', [])
            )
            
            # Send alert
            alert_service._send_alert(alert)
            
            return JsonResponse({
                'success': True,
                'alert_id': alert.id,
                'message': 'Alert triggered successfully'
            })
            
        except Exception as e:
            structured_logger.error("Failed to trigger manual alert", error=str(e))
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500
            )


class ActiveAlertsView(View):
    """
    Active alerts endpoint.
    Returns all currently active alerts.
    """
    
    def get(self, request):
        """Get all active alerts."""
        try:
            active_alerts = alert_service.get_active_alerts()
            
            alerts_data = []
            for alert in active_alerts:
                alerts_data.append({
                    'id': alert.id,
                    'title': alert.title,
                    'message': alert.message,
                    'severity': alert.severity.value,
                    'component': alert.component,
                    'timestamp': alert.timestamp.isoformat(),
                    'status': alert.status.value,
                    'acknowledged_by': alert.acknowledged_by,
                    'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'metadata': alert.metadata,
                    'tags': alert.tags
                })
            
            return JsonResponse({
                'alerts': alerts_data,
                'count': len(alerts_data)
            })
            
        except Exception as e:
            structured_logger.error("Failed to get active alerts", error=str(e))
            return JsonResponse(
                {'error': str(e)},
                status=500
            )


class AlertAcknowledgeView(View):
    """
    Alert acknowledgment endpoint.
    Allows acknowledging alerts.
    """
    
    def post(self, request, alert_id):
        """Acknowledge an alert."""
        try:
            import json
            data = json.loads(request.body)
            acknowledged_by = data.get('acknowledged_by', 'unknown')
            
            success = alert_service.acknowledge_alert(alert_id, acknowledged_by)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'Alert {alert_id} acknowledged by {acknowledged_by}'
                })
            else:
                return JsonResponse(
                    {'success': False, 'error': 'Alert not found'},
                    status=404
                )
            
        except Exception as e:
            structured_logger.error("Failed to acknowledge alert", error=str(e))
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500
            )


class AlertResolveView(View):
    """
    Alert resolution endpoint.
    Allows resolving alerts.
    """
    
    def post(self, request, alert_id):
        """Resolve an alert."""
        try:
            success = alert_service.resolve_alert(alert_id)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'Alert {alert_id} resolved'
                })
            else:
                return JsonResponse(
                    {'success': False, 'error': 'Alert not found'},
                    status=404
                )
            
        except Exception as e:
            structured_logger.error("Failed to resolve alert", error=str(e))
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500
            )


class AlertCheckView(View):
    """
    Alert check endpoint.
    Triggers alert rule checking.
    """
    
    def post(self, request):
        """Check all alert rules."""
        try:
            generated_alerts = alert_service.check_alerts()
            
            alerts_data = []
            for alert in generated_alerts:
                alerts_data.append({
                    'id': alert.id,
                    'title': alert.title,
                    'severity': alert.severity.value,
                    'component': alert.component,
                    'timestamp': alert.timestamp.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'alerts_generated': len(generated_alerts),
                'alerts': alerts_data
            })
            
        except Exception as e:
            structured_logger.error("Failed to check alerts", error=str(e))
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=500
            )
