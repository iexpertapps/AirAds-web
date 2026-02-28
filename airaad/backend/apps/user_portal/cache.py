"""
Advanced caching layer for User Portal performance optimization.
Implements Redis-based caching with intelligent invalidation.
"""

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Advanced cache manager with intelligent invalidation strategies.
    """
    
    # Cache timeout configurations (in seconds)
    TIMEOUTS = {
        'nearby_vendors': 300,      # 5 minutes
        'ar_markers': 30,           # 30 seconds (real-time AR)
        'vendor_detail': 600,       # 10 minutes
        'promotions': 180,          # 3 minutes
        'flash_deals': 60,          # 1 minute (time-sensitive)
        'search_results': 300,      # 5 minutes
        'tags': 3600,               # 1 hour
        'cities': 86400,            # 24 hours
        'user_preferences': 3600,    # 1 hour
        'vendor_analytics': 300,    # 5 minutes
        'ranking_scores': 1800,      # 30 minutes
    }
    
    # Cache key patterns
    PATTERNS = {
        'nearby_vendors': 'user_portal:nearby:{lat:.4f}:{lng:.4f}:{radius}:{tier}:{category}:{limit}',
        'ar_markers': 'user_portal:ar:{lat:.4f}:{lng:.4f}:{radius}:{tier}',
        'vendor_detail': 'user_portal:vendor:{vendor_id}:{user_lat}:{user_lng}',
        'promotions_strip': 'user_portal:promotions:{lat:.4f}:{lng:.4f}:{radius}:{limit}',
        'flash_deals': 'user_portal:flash:{lat:.4f}:{lng:.4f}:{radius}',
        'search': 'user_portal:search:{query_hash}:{lat:.4f}:{lng:.4f}:{radius}:{tier}:{limit}',
        'tags': 'user_portal:tags:{category}',
        'cities': 'user_portal:cities',
        'user_preferences': 'user_portal:prefs:{user_id}',
        'guest_preferences': 'user_portal:prefs:guest:{guest_token}',
        'vendor_ranking': 'user_portal:ranking:{vendor_id}:{user_lat}:{user_lng}',
        'vendor_analytics': 'user_portal:analytics:{vendor_id}:{period}',
    }
    
    @classmethod
    def get_key(cls, pattern_type, **kwargs):
        """
        Generate cache key for given pattern type.
        """
        pattern = cls.PATTERNS.get(pattern_type)
        if not pattern:
            raise ValueError(f"Unknown cache pattern type: {pattern_type}")
        
        try:
            return pattern.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing cache key parameter: {e}")
            raise ValueError(f"Missing required parameter for {pattern_type}: {e}")
    
    @classmethod
    def get(cls, pattern_type, default=None, **kwargs):
        """
        Get cached value.
        """
        key = cls.get_key(pattern_type, **kwargs)
        return cache.get(key, default)
    
    @classmethod
    def set(cls, pattern_type, value, timeout=None, **kwargs):
        """
        Set cached value.
        """
        key = cls.get_key(pattern_type, **kwargs)
        timeout = timeout or cls.TIMEOUTS.get(pattern_type, 300)
        return cache.set(key, value, timeout)
    
    @classmethod
    def delete(cls, pattern_type, **kwargs):
        """
        Delete cached value.
        """
        key = cls.get_key(pattern_type, **kwargs)
        return cache.delete(key)
    
    @classmethod
    def delete_pattern(cls, pattern):
        """
        Delete all keys matching pattern.
        Note: This requires Redis with pattern matching support.
        """
        if hasattr(cache, 'delete_pattern'):
            return cache.delete_pattern(pattern)
        
        # Fallback for non-Redis backends
        logger.warning("Pattern deletion not supported by current cache backend")
        return False
    
    @classmethod
    def invalidate_location_based(cls, lat, lng, radius=5000):
        """
        Invalidate all location-based caches for given area.
        """
        lat_lng_pattern = f"*:{lat:.4f}:{lng:.4f}:*"
        
        patterns_to_invalidate = [
            'user_portal:nearby:*',
            'user_portal:ar:*',
            'user_portal:promotions:*',
            'user_portal:flash:*',
        ]
        
        invalidated_count = 0
        for pattern in patterns_to_invalidate:
            if cls.delete_pattern(pattern):
                invalidated_count += 1
        
        return invalidated_count
    
    @classmethod
    def invalidate_vendor_related(cls, vendor_id):
        """
        Invalidate all caches related to a specific vendor.
        """
        patterns_to_invalidate = [
            f'user_portal:vendor:{vendor_id}:*',
            f'user_portal:ranking:{vendor_id}:*',
            f'user_portal:analytics:{vendor_id}:*',
        ]
        
        invalidated_count = 0
        for pattern in patterns_to_invalidate:
            if cls.delete_pattern(pattern):
                invalidated_count += 1
        
        return invalidated_count
    
    @classmethod
    def invalidate_user_related(cls, user_id=None, guest_token=None):
        """
        Invalidate all caches related to a specific user.
        """
        if user_id:
            patterns = [f'user_portal:prefs:{user_id}']
        elif guest_token:
            patterns = [f'user_portal:prefs:guest:{guest_token}']
        else:
            return 0
        
        invalidated_count = 0
        for pattern in patterns:
            if cls.delete(pattern):
                invalidated_count += 1
        
        return invalidated_count
    
    @classmethod
    def warm_cache(cls, lat, lng, radius=1000, user_tier='SILVER'):
        """
        Warm up commonly accessed cache keys.
        """
        from .services import DiscoveryService
        
        warmed_count = 0
        
        try:
            # Warm nearby vendors
            vendors = DiscoveryService.get_nearby_vendors(
                lat=lat, lng=lng, radius_m=radius, user_tier=user_tier
            )
            warmed_count += 1
            
            # Warm AR markers
            markers = DiscoveryService.get_ar_markers(
                lat=lat, lng=lng, radius_m=radius, user_tier=user_tier
            )
            warmed_count += 1
            
            # Warm promotions
            promotions = DiscoveryService.get_promotions_strip(
                lat=lat, lng=lng, radius_m=radius
            )
            warmed_count += 1
            
            # Warm tags
            tags = DiscoveryService.get_tags()
            warmed_count += 1
            
            logger.info(f"Cache warming completed: {warmed_count} keys warmed")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
        
        return warmed_count


class QueryOptimizer:
    """
    Database query optimization utilities.
    """
    
    @staticmethod
    def optimize_nearby_vendors_query(queryset, user_point, radius_m):
        """
        Optimize nearby vendors query with spatial indexing.
        """
        # Use spatial index for distance filtering
        queryset = queryset.filter(
            location__distance_lte=(user_point, radius_m)
        ).annotate(
            distance_m=Distance('location', user_point) * 111320
        )
        
        # Select related data to avoid N+1 queries
        queryset = queryset.select_related().prefetch_related(
            'promotions',
            'reels'
        )
        
        return queryset
    
    @staticmethod
    def optimize_vendor_detail_query(vendor_id):
        """
        Optimize vendor detail query with all related data.
        """
        from .models import Vendor
        
        try:
            vendor = Vendor.objects.filter(
                id=vendor_id,
                is_active=True
            ).select_related().prefetch_related(
                'promotions',
                'reels'
            ).get()
            
            return vendor
            
        except Vendor.DoesNotExist:
            return None
    
    @staticmethod
    def optimize_search_query(queryset, user_point=None, radius_m=None):
        """
        Optimize search query with spatial filtering if location provided.
        """
        if user_point and radius_m:
            queryset = queryset.filter(
                location__distance_lte=(user_point, radius_m)
            ).annotate(
                distance_m=Distance('location', user_point) * 111320
            )
        
        # Use full-text search if available
        # This would be implemented with PostgreSQL full-text search
        
        return queryset


class PerformanceMonitor:
    """
    Performance monitoring and metrics collection.
    """
    
    @classmethod
    def record_query_performance(cls, query_type, duration_ms, result_count):
        """
        Record query performance metrics.
        """
        metrics = {
            'query_type': query_type,
            'duration_ms': duration_ms,
            'result_count': result_count,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Store in analytics cache
        cache_key = f"user_portal:performance:{query_type}:{timezone.now().strftime('%Y%m%d_%H%M')}"
        cache.set(cache_key, metrics, timeout=3600)  # Keep for 1 hour
        
        # Log slow queries
        if duration_ms > 200:  # 200ms threshold
            logger.warning(f"Slow query detected: {query_type} took {duration_ms}ms")
    
    @classmethod
    def get_performance_stats(cls, query_type=None, hours=24):
        """
        Get performance statistics for analysis.
        """
        from datetime import datetime, timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # This would typically query a time-series database
        # For now, we'll return basic stats from cache
        
        return {
            'query_type': query_type,
            'period_hours': hours,
            'avg_duration_ms': 0,
            'max_duration_ms': 0,
            'min_duration_ms': 0,
            'query_count': 0,
        }


class CacheWarmer:
    """
    Background cache warming for optimal performance.
    """
    
    @staticmethod
    def warm_popular_locations():
        """
        Warm cache for popular locations (major cities, business districts).
        """
        from .models import City
        
        popular_locations = [
            # Karachi
            (24.8607, 67.0011, 2000),
            # Lahore  
            (31.5497, 74.3436, 2000),
            # Islamabad
            (33.6844, 73.0479, 2000),
        ]
        
        warmed_count = 0
        for lat, lng, radius in popular_locations:
            try:
                CacheManager.warm_cache(lat, lng, radius)
                warmed_count += 1
            except Exception as e:
                logger.error(f"Failed to warm cache for {lat},{lng}: {e}")
        
        return warmed_count
    
    @staticmethod
    def warm_vendor_details(limit=100):
        """
        Warm cache for popular vendor details.
        """
        from .models import Vendor
        
        # Get most popular vendors
        vendors = Vendor.objects.filter(
            is_active=True
        ).order_by('-popularity_score')[:limit]
        
        warmed_count = 0
        for vendor in vendors:
            try:
                # Warm vendor detail cache
                from .services import DiscoveryService
                DiscoveryService.get_vendor_detail(str(vendor.id))
                warmed_count += 1
            except Exception as e:
                logger.error(f"Failed to warm vendor detail cache for {vendor.id}: {e}")
        
        return warmed_count


# Cache invalidation signal handlers
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Vendor, Promotion, VendorReel

@receiver(post_save, sender=Vendor)
@receiver(post_delete, sender=Vendor)
def invalidate_vendor_cache(sender, instance, **kwargs):
    """Invalidate cache when vendor changes."""
    CacheManager.invalidate_vendor_related(str(instance.id))
    
    # Invalidate location-based caches if vendor has location
    if instance.lat and instance.lng:
        CacheManager.invalidate_location_based(instance.lat, instance.lng)

@receiver(post_save, sender=Promotion)
@receiver(post_delete, sender=Promotion)
def invalidate_promotion_cache(sender, instance, **kwargs):
    """Invalidate cache when promotion changes."""
    # Invalidate vendor-related caches
    CacheManager.invalidate_vendor_related(str(instance.vendor.id))
    
    # Invalidate promotion-specific caches
    CacheManager.delete_pattern('user_portal:promotions:*')
    CacheManager.delete_pattern('user_portal:flash:*')

@receiver(post_save, sender=VendorReel)
@receiver(post_delete, sender=VendorReel)
def invalidate_reel_cache(sender, instance, **kwargs):
    """Invalidate cache when reel changes."""
    # Invalidate vendor-related caches
    CacheManager.invalidate_vendor_related(str(instance.vendor.id))
    
    # Invalidate reel-specific caches
    CacheManager.delete_pattern('user_portal:nearby_reels:*')
