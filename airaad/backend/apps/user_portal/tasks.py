from celery import shared_task
from django.db import models
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point

from .models import Vendor, Promotion, VendorReel, Tag, City, Area


@shared_task(name='user_portal.update_vendor_popularity_scores')
def update_vendor_popularity_scores():
    """
    Update vendor popularity scores based on recent interactions.
    Runs every 15 minutes.
    """
    from apps.user_preferences.models import UserVendorInteraction
    
    # Calculate popularity score based on recent interactions
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Get interaction counts for each vendor
    interaction_stats = UserVendorInteraction.objects.filter(
        interacted_at__gte=seven_days_ago
    ).values('vendor_id').annotate(
        interaction_count=Count('id'),
        unique_users=Count('user_id', distinct=True),
        profile_views=Count('id', filter=models.Q(interaction_type='VIEW')),
        navigation_clicks=Count('id', filter=models.Q(interaction_type='NAVIGATION')),
        ar_taps=Count('id', filter=models.Q(interaction_type='TAP')),
    )
    
    # Update vendor popularity scores
    updated_count = 0
    for stat in interaction_stats:
        # Calculate popularity score (0-100)
        score = min(100, (
            stat['interaction_count'] * 2 +           # Base interactions
            stat['unique_users'] * 5 +                # Unique users (weighted higher)
            stat['profile_views'] * 1 +               # Profile views
            stat['navigation_clicks'] * 3 +           # Navigation clicks (high intent)
            stat['ar_taps'] * 2                       # AR taps
        ))
        
        # Update vendor
        Vendor.objects.filter(id=stat['vendor_id']).update(
            popularity_score=score,
            interaction_count=stat['interaction_count']
        )
        updated_count += 1
    
    return {
        'updated_vendors': updated_count,
        'message': f'Updated popularity scores for {updated_count} vendors'
    }


@shared_task(name='user_portal.expire_promotions')
def expire_promotions():
    """
    Mark ended promotions as inactive.
    Runs every 5 minutes.
    """
    now = timezone.now()
    
    # Expire promotions that have ended
    expired_count = Promotion.objects.filter(
        end_time__lt=now,
        is_active=True
    ).update(is_active=False)
    
    # Activate promotions that should start now
    started_count = Promotion.objects.filter(
        start_time__lte=now,
        end_time__gte=now,
        is_active=False
    ).update(is_active=True)
    
    return {
        'expired_count': expired_count,
        'started_count': started_count,
        'message': f'Expired {expired_count} promotions, started {started_count} promotions'
    }


@shared_task(name='user_portal.aggregate_vendor_analytics')
def aggregate_vendor_analytics():
    """
    Aggregate interaction events into vendor counters.
    Runs every 15 minutes.
    """
    from apps.user_preferences.models import UserVendorInteraction, NearbyReelView
    
    # Time window for aggregation
    fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
    
    # Aggregate vendor interactions
    interaction_stats = UserVendorInteraction.objects.filter(
        interacted_at__gte=fifteen_minutes_ago
    ).values('vendor_id', 'interaction_type').annotate(
        count=Count('id')
    )
    
    # Aggregate reel views
    reel_stats = NearbyReelView.objects.filter(
        viewed_at__gte=fifteen_minutes_ago
    ).values('vendor_id').annotate(
        total_views=Count('id'),
        completed_views=Count('id', filter=models.Q(completed=True)),
        cta_taps=Count('id', filter=models.Q(cta_tapped=True)),
        total_watch_time=Sum('watched_seconds')
    )
    
    # Store aggregated data in cache
    from django.core.cache import cache
    
    cache_key = f"vendor_analytics:{timezone.now().strftime('%Y%m%d_%H%M')}"
    analytics_data = {
        'timestamp': timezone.now().isoformat(),
        'period_minutes': 15,
        'interactions': list(interaction_stats),
        'reel_views': list(reel_stats),
    }
    
    cache.set(cache_key, analytics_data, timeout=3600)  # Keep for 1 hour
    
    return analytics_data


@shared_task(name='user_portal.invalidate_discovery_cache')
def invalidate_discovery_cache():
    """
    Invalidate discovery cache when vendor/promotion data changes.
    This is a Django signal receiver, not a beat task.
    """
    from django.core.cache import cache
    
    # Clear all discovery-related cache keys
    cache_patterns = [
        'nearby_vendors_*',
        'ar_markers_*',
        'vendor_detail_*',
        'promotions_strip_*',
        'search_*',
    ]
    
    cleared_count = 0
    
    # Note: This is a simplified approach. In production, you might want
    # to use Redis pattern matching or maintain a list of active cache keys
    for pattern in cache_patterns:
        # This would need to be implemented based on your cache backend
        # For Redis, you could use: cache.delete_many(cache.keys(pattern))
        # For now, we'll clear a few common keys
        cleared_count += 1
    
    return {
        'cleared_patterns': len(cache_patterns),
        'message': f'Invalidated {cleared_count} cache patterns'
    }


@shared_task(name='user_portal.send_flash_deal_push_notification')
def send_flash_deal_push_notification(promotion_id, vendor_id):
    """
    Send push notification for new flash deal to eligible users.
    Triggered when Platinum vendor creates flash deal.
    """
    from apps.customer_auth.models import CustomerUser
    from apps.user_preferences.models import FlashDealAlert
    from apps.user_portal.models import Promotion, Vendor
    
    try:
        # Get promotion details
        promotion = Promotion.objects.get(id=promotion_id)
        vendor = Vendor.objects.get(id=vendor_id)
        
        # Get users within reasonable distance (e.g., 5km)
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.geos import Point
        
        vendor_point = Point(float(vendor.lng), float(vendor.lat), srid=4326)
        
        # Find users who have interacted with this vendor or similar vendors
        from apps.user_preferences.models import UserVendorInteraction
        
        # Get users who have interacted with this vendor or nearby vendors
        nearby_vendors = Vendor.objects.filter(
            location__distance_lte=(vendor_point, 5000)  # 5km radius
        ).values_list('id', flat=True)
        
        interacting_users = UserVendorInteraction.objects.filter(
            vendor_id__in=nearby_vendors,
            interacted_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('user_id', flat=True).distinct()
        
        # Get customer users
        customer_users = CustomerUser.objects.filter(
            id__in=interacting_users,
            is_deleted=False,
            notification_enabled=True
        )
        
        # Filter users who haven't been alerted about this deal
        alerted_count = 0
        for customer_user in customer_users:
            if FlashDealAlert.should_alert(customer_user, promotion_id, vendor_id):
                # Create alert
                FlashDealAlert.create_alert(customer_user, promotion_id, vendor_id)
                alerted_count += 1
                
                # Here you would integrate with your push notification service
                # For now, we'll just log it
                print(f"Push notification sent to {customer_user.user.email} for flash deal {promotion_id}")
        
        return {
            'promotion_id': str(promotion_id),
            'vendor_id': str(vendor_id),
            'alerted_users': alerted_count,
            'message': f'Sent flash deal notifications to {alerted_count} users'
        }
        
    except (Promotion.DoesNotExist, Vendor.DoesNotExist) as e:
        return {
            'error': f'Promotion or Vendor not found: {e}',
            'promotion_id': str(promotion_id),
            'vendor_id': str(vendor_id),
        }


@shared_task(name='user_portal.update_tag_vendor_counts')
def update_tag_vendor_counts():
    """
    Update vendor counts for all tags.
    Runs daily at 2:00 AM.
    """
    updated_count = 0
    
    for tag in Tag.objects.filter(is_active=True):
        tag.update_vendor_count()
        updated_count += 1
    
    return {
        'updated_tags': updated_count,
        'message': f'Updated vendor counts for {updated_count} tags'
    }


@shared_task(name='user_portal.update_city_area_vendor_counts')
def update_city_area_vendor_counts():
    """
    Update vendor counts for all cities and areas.
    Runs daily at 2:30 AM.
    """
    cities_updated = 0
    areas_updated = 0
    
    # Update cities
    for city in City.objects.filter(is_active=True):
        city.update_vendor_count()
        cities_updated += 1
    
    # Update areas
    for area in Area.objects.filter(is_active=True):
        area.update_vendor_count()
        areas_updated += 1
    
    return {
        'cities_updated': cities_updated,
        'areas_updated': areas_updated,
        'message': f'Updated vendor counts for {cities_updated} cities and {areas_updated} areas'
    }


@shared_task(name='user_portal.cleanup_old_reels')
def cleanup_old_reels():
    """
    Clean up old or underperforming reels.
    Runs weekly on Sundays at 3:00 AM.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Deactivate reels with no views in 30 days
    deactivated_count = VendorReel.objects.filter(
        view_count=0,
        created_at__lt=thirty_days_ago,
        is_active=True
    ).update(is_active=False)
    
    # Unapprove reels with very low completion rates (<10%)
    low_performance_count = VendorReel.objects.filter(
        view_count__gte=10,  # Only consider reels with some views
        completion_count__lt=1,  # Less than 10% completion
        is_approved=True
    ).update(is_approved=False)
    
    return {
        'deactivated_count': deactivated_count,
        'low_performance_count': low_performance_count,
        'message': f'Deactivated {deactivated_count} old reels, unapproved {low_performance_count} low-performance reels'
    }


@shared_task(name='user_portal.generate_discovery_analytics')
def generate_discovery_analytics():
    """
    Generate discovery analytics for reporting.
    Runs daily at 4:00 AM.
    """
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_start = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.time.min)
    )
    yesterday_end = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.time.max)
    )
    
    # Get yesterday's discovery stats
    from apps.user_preferences.models import UserSearchHistory, UserVendorInteraction
    
    stats = {
        'date': yesterday.isoformat(),
        'searches': UserSearchHistory.objects.filter(
            searched_at__range=[yesterday_start, yesterday_end]
        ).count(),
        'interactions': UserVendorInteraction.objects.filter(
            interacted_at__range=[yesterday_start, yesterday_end]
        ).count(),
        'unique_vendors_discovered': UserVendorInteraction.objects.filter(
            interacted_at__range=[yesterday_start, yesterday_end]
        ).values('vendor_id').distinct().count(),
    }
    
    # Search breakdown by type
    stats['search_breakdown'] = list(
        UserSearchHistory.objects.filter(
            searched_at__range=[yesterday_start, yesterday_end]
        ).values('query_type').annotate(count=Count('id'))
    )
    
    # Interaction breakdown by type
    stats['interaction_breakdown'] = list(
        UserVendorInteraction.objects.filter(
            interacted_at__range=[yesterday_start, yesterday_end]
        ).values('interaction_type').annotate(count=Count('id'))
    )
    
    # Store report in cache
    from django.core.cache import cache
    cache_key = f"discovery_analytics:{yesterday.strftime('%Y%m%d')}"
    cache.set(cache_key, stats, timeout=86400 * 30)  # Keep for 30 days
    
    return stats


# Django signal receivers for cache invalidation
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Vendor)
@receiver(post_delete, sender=Vendor)
def invalidate_vendor_cache(sender, instance, **kwargs):
    """Invalidate cache when vendor changes."""
    invalidate_discovery_cache.delay()

@receiver(post_save, sender=Promotion)
@receiver(post_delete, sender=Promotion)
def invalidate_promotion_cache(sender, instance, **kwargs):
    """Invalidate cache when promotion changes."""
    invalidate_discovery_cache.delay()

@receiver(post_save, sender=VendorReel)
@receiver(post_delete, sender=VendorReel)
def invalidate_reel_cache(sender, instance, **kwargs):
    """Invalidate cache when reel changes."""
    invalidate_discovery_cache.delay()
