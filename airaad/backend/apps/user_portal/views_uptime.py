from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from .uptime_monitoring import uptime_monitor
from .logging import structured_logger


@method_decorator(csrf_exempt, name='dispatch')
class UptimeCheckView(View):
    """
    Uptime check endpoint.
    Performs comprehensive uptime monitoring check.
    """
    
    def get(self, request):
        """Perform uptime check."""
        try:
            uptime_data = uptime_monitor.check_uptime()
            
            return JsonResponse(uptime_data)
            
        except Exception as e:
            structured_logger.error("Failed to perform uptime check", error=str(e))
            return JsonResponse(
                {
                    'timestamp': '2024-01-01T00:00:00Z',
                    'overall_status': 'ERROR',
                    'checks': {},
                    'external_services': {},
                    'statistics': {},
                    'alerts': [{
                        'type': 'uptime_error',
                        'message': 'Uptime check failed',
                        'details': {'error': str(e)}
                    }]
                },
                status=500
            )


class UptimeStatisticsView(View):
    """
    Uptime statistics endpoint.
    Returns uptime statistics for different time periods.
    """
    
    def get(self, request):
        """Get uptime statistics."""
        try:
            stats = uptime_monitor.get_uptime_statistics()
            
            return JsonResponse(stats)
            
        except Exception as e:
            structured_logger.error("Failed to get uptime statistics", error=str(e))
            return JsonResponse(
                {
                    'uptime_24h': {'uptime_percentage': 0.0},
                    'uptime_7d': {'uptime_percentage': 0.0},
                    'uptime_30d': {'uptime_percentage': 0.0},
                    'error': str(e)
                },
                status=500
            )


class UptimeHistoryView(View):
    """
    Uptime history endpoint.
    Returns recent uptime check history.
    """
    
    def get(self, request):
        """Get uptime check history."""
        try:
            # Get limit from query parameter (default: 100)
            limit = int(request.GET.get('limit', 100))
            
            # Get recent checks
            recent_checks = uptime_monitor.check_history[-limit:] if uptime_monitor.check_history else []
            
            return JsonResponse({
                'checks': recent_checks,
                'count': len(recent_checks),
                'total_checks': len(uptime_monitor.check_history)
            })
            
        except Exception as e:
            structured_logger.error("Failed to get uptime history", error=str(e))
            return JsonResponse(
                {
                    'checks': [],
                    'count': 0,
                    'total_checks': 0,
                    'error': str(e)
                },
                status=500
            )


class UptimeStatusView(View):
    """
    Simple uptime status endpoint.
    Returns basic uptime status for load balancers.
    """
    
    def get(self, request):
        """Get simple uptime status."""
        try:
            # Quick health check
            from django.db import connection
            
            # Test database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Return simple status
            return JsonResponse({
                'status': 'UP',
                'timestamp': timezone.now().isoformat(),
                'version': getattr(settings, 'APP_VERSION', '1.0.0')
            })
            
        except Exception as e:
            structured_logger.error("Uptime status check failed", error=str(e))
            return JsonResponse(
                {
                    'status': 'DOWN',
                    'timestamp': timezone.now().isoformat(),
                    'error': str(e)
                },
                status=503
            )
