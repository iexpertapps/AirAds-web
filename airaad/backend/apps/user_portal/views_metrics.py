from django.http import HttpResponse
from django.views import View
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
import logging

from .prometheus_metrics import prometheus_metrics
from .replication_monitor import ReplicationMonitor
from .logging import structured_logger

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MetricsView(View):
    """
    Prometheus metrics endpoint.
    Exposes metrics in Prometheus format for scraping.
    """
    
    def get(self, request):
        """Return Prometheus metrics."""
        try:
            metrics_data = prometheus_metrics.get_metrics()
            
            response = HttpResponse(
                metrics_data,
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
            
            # Add cache control headers
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response
            
        except Exception as e:
            structured_logger.error("Failed to generate metrics", error=str(e))
            return HttpResponse(
                "Error generating metrics",
                status=500,
                content_type='text/plain'
            )


class HealthMetricsView(View):
    """
    Health metrics endpoint.
    Provides health status with detailed metrics.
    """
    
    def get(self, request):
        """Return health status with metrics."""
        try:
            from .replication_monitor import ReplicationMonitor
            
            monitor = ReplicationMonitor()
            health_data = monitor.monitor_replication()
            
            # Add application info
            health_data['application'] = {
                'name': 'user-portal',
                'version': getattr(settings, 'APP_VERSION', '1.0.0'),
                'environment': getattr(settings, 'ENVIRONMENT', 'production'),
                'status': 'healthy' if health_data['alerts'] == [] else 'degraded'
            }
            
            import json
            return HttpResponse(
                json.dumps(health_data, indent=2, default=str),
                content_type='application/json'
            )
            
        except Exception as e:
            structured_logger.error("Failed to generate health metrics", error=str(e))
            return HttpResponse(
                json.dumps({'status': 'error', 'message': str(e)}),
                status=500,
                content_type='application/json'
            )


class BusinessMetricsView(LoginRequiredMixin, View):
    """
    Business metrics endpoint.
    Provides business-specific metrics and KPIs.
    """
    
    def get(self, request):
        """Return business metrics."""
        try:
            from django.utils import timezone
            from datetime import timedelta
            from apps.customer_auth.models import CustomerUser
            from apps.user_preferences.models import UserVendorInteraction, UserSearchHistory
            from apps.user_portal.models import Vendor, Promotion
            
            # Time ranges
            now = timezone.now()
            last_24h = now - timedelta(days=1)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            metrics = {
                'user_metrics': self._get_user_metrics(last_24h, last_7d, last_30d),
                'vendor_metrics': self._get_vendor_metrics(last_24h, last_7d, last_30d),
                'engagement_metrics': self._get_engagement_metrics(last_24h, last_7d, last_30d),
                'search_metrics': self._get_search_metrics(last_24h, last_7d, last_30d),
                'promotion_metrics': self._get_promotion_metrics(last_24h, last_7d, last_30d),
            }
            
            import json
            return HttpResponse(
                json.dumps(metrics, indent=2, default=str),
                content_type='application/json'
            )
            
        except Exception as e:
            structured_logger.error("Failed to generate business metrics", error=str(e))
            return HttpResponse(
                json.dumps({'status': 'error', 'message': str(e)}),
                status=500,
                content_type='application/json'
            )
    
    def _get_user_metrics(self, last_24h, last_7d, last_30d):
        """Get user-related metrics."""
        metrics = {}
        
        # Total users
        metrics['total_registered_users'] = CustomerUser.objects.count()
        
        # Active users
        metrics['active_users_24h'] = CustomerUser.objects.filter(
            user__last_login__gte=last_24h
        ).count()
        
        metrics['active_users_7d'] = CustomerUser.objects.filter(
            user__last_login__gte=last_7d
        ).count()
        
        metrics['active_users_30d'] = CustomerUser.objects.filter(
            user__last_login__gte=last_30d
        ).count()
        
        # New registrations
        metrics['new_registrations_24h'] = CustomerUser.objects.filter(
            created_at__gte=last_24h
        ).count()
        
        metrics['new_registrations_7d'] = CustomerUser.objects.filter(
            created_at__gte=last_7d
        ).count()
        
        metrics['new_registrations_30d'] = CustomerUser.objects.filter(
            created_at__gte=last_30d
        ).count()
        
        return metrics
    
    def _get_vendor_metrics(self, last_24h, last_7d, last_30d):
        """Get vendor-related metrics."""
        metrics = {}
        
        # Total vendors
        metrics['total_vendors'] = Vendor.objects.filter(is_active=True).count()
        
        # Verified vendors
        metrics['verified_vendors'] = Vendor.objects.filter(
            is_active=True,
            is_verified=True
        ).count()
        
        # Vendors by tier
        for tier in ['SILVER', 'GOLD', 'DIAMOND', 'PLATINUM']:
            metrics[f'vendors_{tier.lower()}'] = Vendor.objects.filter(
                is_active=True,
                tier=tier
            ).count()
        
        # New vendors
        metrics['new_vendors_24h'] = Vendor.objects.filter(
            created_at__gte=last_24h,
            is_active=True
        ).count()
        
        metrics['new_vendors_7d'] = Vendor.objects.filter(
            created_at__gte=last_7d,
            is_active=True
        ).count()
        
        metrics['new_vendors_30d'] = Vendor.objects.filter(
            created_at__gte=last_30d,
            is_active=True
        ).count()
        
        return metrics
    
    def _get_engagement_metrics(self, last_24h, last_7d, last_30d):
        """Get engagement metrics."""
        metrics = {}
        
        # Vendor interactions
        interactions_24h = UserVendorInteraction.objects.filter(interacted_at__gte=last_24h)
        interactions_7d = UserVendorInteraction.objects.filter(interacted_at__gte=last_7d)
        interactions_30d = UserVendorInteraction.objects.filter(interacted_at__gte=last_30d)
        
        metrics['total_interactions_24h'] = interactions_24h.count()
        metrics['total_interactions_7d'] = interactions_7d.count()
        metrics['total_interactions_30d'] = interactions_30d.count()
        
        # Interactions by type
        for period, interactions in [('24h', interactions_24h), ('7d', interactions_7d), ('30d', interactions_30d)]:
            interaction_types = interactions.values('interaction_type').annotate(
                count=models.Count('id')
            )
            
            for interaction in interaction_types:
                metrics[f'interactions_{interaction["interaction_type"].lower()}_{period}'] = interaction['count']
        
        # Unique users engaged
        metrics['unique_users_engaged_24h'] = interactions_24h.values('user_id').distinct().count()
        metrics['unique_users_engaged_7d'] = interactions_7d.values('user_id').distinct().count()
        metrics['unique_users_engaged_30d'] = interactions_30d.values('user_id').distinct().count()
        
        return metrics
    
    def _get_search_metrics(self, last_24h, last_7d, last_30d):
        """Get search metrics."""
        from django.db import models
        
        metrics = {}
        
        # Search queries
        searches_24h = UserSearchHistory.objects.filter(searched_at__gte=last_24h)
        searches_7d = UserSearchHistory.objects.filter(searched_at__gte=last_7d)
        searches_30d = UserSearchHistory.objects.filter(searched_at__gte=last_30d)
        
        metrics['total_searches_24h'] = searches_24h.count()
        metrics['total_searches_7d'] = searches_7d.count()
        metrics['total_searches_30d'] = searches_30d.count()
        
        # Search types
        for period, searches in [('24h', searches_24h), ('7d', searches_7d), ('30d', searches_30d)]:
            search_types = searches.values('search_type').annotate(
                count=models.Count('id')
            )
            
            for search in search_types:
                metrics[f'searches_{search["search_type"].lower()}_{period}'] = search['count']
        
        # Top search terms
        top_terms_24h = searches_24h.values('query').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        metrics['top_search_terms_24h'] = [
            {'term': term['query'], 'count': term['count']}
            for term in top_terms_24h
        ]
        
        return metrics
    
    def _get_promotion_metrics(self, last_24h, last_7d, last_30d):
        """Get promotion metrics."""
        metrics = {}
        
        # Active promotions
        now = timezone.now()
        metrics['active_promotions'] = Promotion.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).count()
        
        # Flash deals
        metrics['active_flash_deals'] = Promotion.objects.filter(
            is_active=True,
            is_flash_deal=True,
            start_time__lte=now,
            end_time__gte=now
        ).count()
        
        # Promotions by discount range
        discount_ranges = [
            ('0_10', 0, 10),
            ('10_25', 10, 25),
            ('25_50', 25, 50),
            ('50_plus', 50, 100)
        ]
        
        for range_name, min_discount, max_discount in discount_ranges:
            if max_discount == 100:
                count = Promotion.objects.filter(
                    is_active=True,
                    discount_percent__gte=min_discount
                ).count()
            else:
                count = Promotion.objects.filter(
                    is_active=True,
                    discount_percent__gte=min_discount,
                    discount_percent__lt=max_discount
                ).count()
            
            metrics[f'promotions_discount_{range_name}'] = count
        
        return metrics
