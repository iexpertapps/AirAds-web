"""
Performance optimization tasks for User Portal.
"""

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from .cache import CacheManager, CacheWarmer, PerformanceMonitor
from .models import Vendor, Promotion, VendorReel

logger = logging.getLogger(__name__)


@shared_task(name='user_portal.warm_cache_popular_locations')
def warm_cache_popular_locations():
    """
    Warm cache for popular locations.
    Runs every hour.
    """
    try:
        warmed_count = CacheWarmer.warm_popular_locations()
        
        return {
            'warmed_locations': warmed_count,
            'message': f'Warmed cache for {warmed_count} popular locations'
        }
        
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        return {
            'error': str(e),
            'message': 'Cache warming failed'
        }


@shared_task(name='user_portal.warm_cache_popular_vendors')
def warm_cache_popular_vendors():
    """
    Warm cache for popular vendor details.
    Runs every 30 minutes.
    """
    try:
        warmed_count = CacheWarmer.warm_vendor_details(limit=200)
        
        return {
            'warmed_vendors': warmed_count,
            'message': f'Warmed cache for {warmed_count} popular vendors'
        }
        
    except Exception as e:
        logger.error(f"Vendor cache warming failed: {e}")
        return {
            'error': str(e),
            'message': 'Vendor cache warming failed'
        }


@shared_task(name='user_portal.cleanup_expired_cache')
def cleanup_expired_cache():
    """
    Clean up expired cache entries.
    Runs daily at 3:00 AM.
    """
    try:
        # This would typically be handled by Redis TTL automatically
        # But we can clean up any manually managed cache entries
        
        cleaned_count = 0
        
        # Clean up performance metrics older than 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # This would require iterating through cache keys
        # For Redis, we could use SCAN with pattern matching
        
        return {
            'cleaned_entries': cleaned_count,
            'message': f'Cleaned up {cleaned_count} expired cache entries'
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {
            'error': str(e),
            'message': 'Cache cleanup failed'
        }


@shared_task(name='user_portal.optimize_database_queries')
def optimize_database_queries():
    """
    Optimize database queries and update statistics.
    Runs daily at 4:00 AM.
    """
    try:
        from django.db import connection
        
        optimized_tables = []
        
        # Analyze frequently queried tables
        tables_to_analyze = [
            'user_portal_vendors',
            'user_portal_promotions',
            'user_portal_vendor_reels',
            'user_portal_tags',
            'user_portal_cities',
            'user_portal_areas',
            'customer_users',
            'user_preferences',
            'user_search_history',
            'user_vendor_interactions',
        ]
        
        with connection.cursor() as cursor:
            for table in tables_to_analyze:
                try:
                    cursor.execute(f"ANALYZE {table};")
                    optimized_tables.append(table)
                except Exception as e:
                    logger.warning(f"Failed to analyze table {table}: {e}")
        
        return {
            'optimized_tables': optimized_tables,
            'message': f'Optimized {len(optimized_tables)} database tables'
        }
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return {
            'error': str(e),
            'message': 'Database optimization failed'
        }


@shared_task(name='user_portal.generate_performance_report')
def generate_performance_report():
    """
    Generate daily performance report.
    Runs daily at 5:00 AM.
    """
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Collect performance metrics
        report = {
            'date': yesterday.isoformat(),
            'generated_at': timezone.now().isoformat(),
            'metrics': {
                'nearby_vendors': PerformanceMonitor.get_performance_stats('nearby_vendors', hours=24),
                'ar_markers': PerformanceMonitor.get_performance_stats('ar_markers', hours=24),
                'search': PerformanceMonitor.get_performance_stats('search', hours=24),
                'vendor_detail': PerformanceMonitor.get_performance_stats('vendor_detail', hours=24),
            },
            'cache_stats': {
                'hit_rate': _get_cache_hit_rate(),
                'memory_usage': _get_cache_memory_usage(),
                'key_count': _get_cache_key_count(),
            },
            'database_stats': {
                'vendor_count': Vendor.objects.filter(is_active=True).count(),
                'promotion_count': Promotion.objects.filter(is_active=True).count(),
                'reel_count': VendorReel.objects.filter(is_active=True, is_approved=True).count(),
            }
        }
        
        # Store report in cache
        cache_key = f"user_portal:performance_report:{yesterday.strftime('%Y%m%d')}"
        cache.set(cache_key, report, timeout=86400 * 7)  # Keep for 7 days
        
        return report
        
    except Exception as e:
        logger.error(f"Performance report generation failed: {e}")
        return {
            'error': str(e),
            'message': 'Performance report generation failed'
        }


@shared_task(name='user_portal.precompute_ranking_scores')
def precompute_ranking_scores():
    """
    Precompute ranking scores for popular vendors.
    Runs every 2 hours.
    """
    try:
        from .services import DiscoveryService
        from django.contrib.gis.geos import Point
        
        # Get popular vendors
        popular_vendors = Vendor.objects.filter(
            is_active=True
        ).order_by('-popularity_score')[:100]
        
        precomputed_count = 0
        
        # Precompute scores for major cities
        major_locations = [
            (24.8607, 67.0011, 'Karachi'),
            (31.5497, 74.3436, 'Lahore'),
            (33.6844, 73.0479, 'Islamabad'),
        ]
        
        for vendor in popular_vendors:
            for lat, lng, city_name in major_locations:
                try:
                    user_point = Point(lng, lat, srid=4326)
                    
                    # Calculate and cache ranking score
                    score_data = DiscoveryService._calculate_vendor_score(vendor, user_point)
                    
                    cache_key = f"user_portal:ranking:{vendor.id}:{lat:.4f}:{lng:.4f}"
                    cache.set(cache_key, score_data, timeout=7200)  # 2 hours
                    
                    precomputed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to precompute score for vendor {vendor.id} in {city_name}: {e}")
        
        return {
            'precomputed_scores': precomputed_count,
            'message': f'Precomputed {precomputed_count} ranking scores'
        }
        
    except Exception as e:
        logger.error(f"Ranking score precomputation failed: {e}")
        return {
            'error': str(e),
            'message': 'Ranking score precomputation failed'
        }


@shared_task(name='user_portal.monitor_cache_performance')
def monitor_cache_performance():
    """
    Monitor cache performance and alert on issues.
    Runs every 15 minutes.
    """
    try:
        alerts = []
        
        # Check cache hit rate
        hit_rate = _get_cache_hit_rate()
        if hit_rate < 80:  # Less than 80% hit rate
            alerts.append({
                'type': 'low_hit_rate',
                'message': f'Cache hit rate is low: {hit_rate:.1f}%',
                'severity': 'warning'
            })
        
        # Check cache memory usage
        memory_usage = _get_cache_memory_usage()
        if memory_usage > 90:  # More than 90% memory usage
            alerts.append({
                'type': 'high_memory_usage',
                'message': f'Cache memory usage is high: {memory_usage:.1f}%',
                'severity': 'critical'
            })
        
        # Check slow queries
        slow_queries = _get_slow_query_count()
        if slow_queries > 10:  # More than 10 slow queries in last 15 minutes
            alerts.append({
                'type': 'slow_queries',
                'message': f'High number of slow queries: {slow_queries}',
                'severity': 'warning'
            })
        
        # Store alerts in cache for monitoring
        if alerts:
            cache_key = f"user_portal:alerts:{timezone.now().strftime('%Y%m%d_%H%M')}"
            cache.set(cache_key, alerts, timeout=3600)  # Keep for 1 hour
        
        return {
            'alerts': alerts,
            'hit_rate': hit_rate,
            'memory_usage': memory_usage,
            'slow_queries': slow_queries,
            'message': f'Monitoring completed with {len(alerts)} alerts'
        }
        
    except Exception as e:
        logger.error(f"Cache performance monitoring failed: {e}")
        return {
            'error': str(e),
            'message': 'Cache performance monitoring failed'
        }


# Helper functions for monitoring

def _get_cache_hit_rate():
    """
    Get cache hit rate from Redis.
    """
    try:
        if hasattr(cache, 'client'):  # Redis backend
            info = cache.client.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            
            if total > 0:
                return (hits / total) * 100
    except Exception:
        pass
    
    return 0.0


def _get_cache_memory_usage():
    """
    Get cache memory usage from Redis.
    """
    try:
        if hasattr(cache, 'client'):  # Redis backend
            info = cache.client.info('memory')
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0:
                return (used_memory / max_memory) * 100
    except Exception:
        pass
    
    return 0.0


def _get_cache_key_count():
    """
    Get total number of keys in cache.
    """
    try:
        if hasattr(cache, 'client'):  # Redis backend
            return cache.client.dbsize()
    except Exception:
        pass
    
    return 0


def _get_slow_query_count():
    """
    Get count of slow queries in recent period.
    """
    try:
        # This would typically query a monitoring system
        # For now, return 0 as placeholder
        return 0
    except Exception:
        return 0
