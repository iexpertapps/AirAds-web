from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin

from .system_health import system_health_monitor
from .logging import structured_logger


@method_decorator(csrf_exempt, name='dispatch')
class SystemHealthView(View):
    """
    System health endpoint.
    Provides comprehensive system health status.
    """
    
    def get(self, request):
        """Return system health status."""
        try:
            health_data = system_health_monitor.get_system_health()
            
            return JsonResponse(health_data)
            
        except Exception as e:
            structured_logger.error("Failed to get system health", error=str(e))
            return JsonResponse(
                {
                    'timestamp': '2024-01-01T00:00:00Z',
                    'overall_status': 'ERROR',
                    'components': {},
                    'alerts': [{
                        'component': 'system_health',
                        'severity': 'CRITICAL',
                        'message': 'System health check failed',
                        'details': {'error': str(e)}
                    }],
                    'metrics': {}
                },
                status=500
            )


class HealthSummaryView(View):
    """
    Health summary endpoint.
    Provides simplified health status for quick checks.
    """
    
    def get(self, request):
        """Return health summary."""
        try:
            summary = system_health_monitor.get_health_summary()
            
            return JsonResponse(summary)
            
        except Exception as e:
            structured_logger.error("Failed to get health summary", error=str(e))
            return JsonResponse(
                {
                    'timestamp': '2024-01-01T00:00:00Z',
                    'overall_status': 'ERROR',
                    'component_count': 0,
                    'healthy_components': 0,
                    'alert_count': 1,
                    'critical_alerts': 1,
                    'warning_alerts': 0
                },
                status=500
            )


class ComponentHealthView(View):
    """
    Component-specific health endpoint.
    Allows checking individual components.
    """
    
    def get(self, request, component):
        """Return specific component health."""
        try:
            health_data = system_health_monitor.get_system_health()
            
            if component in health_data['components']:
                component_health = health_data['components'][component]
                component_health['timestamp'] = health_data['timestamp']
                
                return JsonResponse(component_health)
            else:
                return JsonResponse(
                    {
                        'error': f'Component "{component}" not found',
                        'available_components': list(health_data['components'].keys())
                    },
                    status=404
                )
            
        except Exception as e:
            structured_logger.error("Failed to get component health", error=str(e))
            return JsonResponse(
                {
                    'component': component,
                    'status': 'ERROR',
                    'message': 'Component health check failed',
                    'details': {'error': str(e)}
                },
                status=500
            )
