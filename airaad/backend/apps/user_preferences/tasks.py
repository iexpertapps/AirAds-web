from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Avg
from .models import UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView


@shared_task(name='user_preferences.purge_search_history')
def purge_search_history():
    """
    Purge search history older than 90 days.
    Runs daily at 4:00 AM.
    """
    cutoff_date = timezone.now() - timedelta(days=90)
    
    # Delete old search history
    deleted_count = UserSearchHistory.objects.filter(
        searched_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'deleted_count': deleted_count,
        'message': f'Purged {deleted_count} old search history records'
    }


@shared_task(name='user_preferences.purge_interaction_events')
def purge_interaction_events():
    """
    Purge interaction events older than 90 days.
    Runs daily at 5:00 AM.
    """
    cutoff_date = timezone.now() - timedelta(days=90)
    
    # Delete old interaction events
    deleted_count = UserVendorInteraction.objects.filter(
        interacted_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'deleted_count': deleted_count,
        'message': f'Purged {deleted_count} old interaction events'
    }


@shared_task(name='user_preferences.aggregate_user_analytics')
def aggregate_user_analytics():
    """
    Aggregate user analytics for reporting.
    Runs every 15 minutes.
    """
    now = timezone.now()
    fifteen_minutes_ago = now - timedelta(minutes=15)
    
    # Aggregate interaction counts by type
    interaction_stats = UserVendorInteraction.objects.filter(
        interacted_at__gte=fifteen_minutes_ago
    ).values('interaction_type').annotate(
        count=Count('id')
    ).order_by('interaction_type')
    
    # Aggregate search counts by type
    search_stats = UserSearchHistory.objects.filter(
        searched_at__gte=fifteen_minutes_ago
    ).values('query_type').annotate(
        count=Count('id')
    ).order_by('query_type')
    
    # Aggregate reel view metrics
    reel_stats = NearbyReelView.objects.filter(
        viewed_at__gte=fifteen_minutes_ago
    ).aggregate(
        total_views=Count('id'),
        completed_views=Count('id', filter=models.Q(completed=True)),
        cta_taps=Count('id', filter=models.Q(cta_tapped=True)),
        total_watch_time=Sum('watched_seconds')
    )
    
    # Store aggregated stats in cache
    from django.core.cache import cache
    cache_key = f"user_analytics:{now.strftime('%Y%m%d_%H%M')}"
    
    analytics_data = {
        'timestamp': now.isoformat(),
        'period_minutes': 15,
        'interactions': list(interaction_stats),
        'searches': list(search_stats),
        'reel_views': reel_stats,
    }
    
    cache.set(cache_key, analytics_data, timeout=3600)  # Keep for 1 hour
    
    return analytics_data


@shared_task(name='user_preferences.cleanup_expired_flash_alerts')
def cleanup_expired_flash_alerts():
    """
    Clean up flash deal alerts for expired deals.
    Runs every 5 minutes.
    """
    # This would integrate with the vendor promotions system
    # For now, we'll clean up alerts older than 24 hours
    
    cutoff_date = timezone.now() - timedelta(hours=24)
    
    # Delete old flash deal alerts
    deleted_count = FlashDealAlert.objects.filter(
        alerted_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'deleted_count': deleted_count,
        'message': f'Cleaned up {deleted_count} old flash deal alerts'
    }


@shared_task(name='user_preferences.update_user_engagement_scores')
def update_user_engagement_scores():
    """
    Update user engagement scores based on recent activity.
    Runs hourly.
    """
    from apps.customer_auth.models import CustomerUser
    
    # Calculate engagement scores for the last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    for customer_user in CustomerUser.objects.filter(is_deleted=False):
        # Count recent interactions
        interaction_count = UserVendorInteraction.objects.filter(
            user=customer_user,
            interacted_at__gte=seven_days_ago
        ).count()
        
        # Count recent searches
        search_count = UserSearchHistory.objects.filter(
            user=customer_user,
            searched_at__gte=seven_days_ago
        ).count()
        
        # Count recent reel views
        reel_view_count = NearbyReelView.objects.filter(
            user=customer_user,
            viewed_at__gte=seven_days_ago
        ).count()
        
        # Calculate engagement score (0-100)
        engagement_score = min(100, (
            interaction_count * 10 +
            search_count * 5 +
            reel_view_count * 3
        ))
        
        # Store in behavioral_data
        if not customer_user.behavioral_data:
            customer_user.behavioral_data = {}
        
        customer_user.behavioral_data.update({
            'engagement_score': engagement_score,
            'last_engagement_update': timezone.now().isoformat(),
            'weekly_interactions': interaction_count,
            'weekly_searches': search_count,
            'weekly_reel_views': reel_view_count,
        })
        
        customer_user.save(update_fields=['behavioral_data'])
    
    return {
        'message': 'Updated user engagement scores',
        'processed_users': CustomerUser.objects.filter(is_deleted=False).count()
    }


@shared_task(name='user_preferences.generate_daily_user_report')
def generate_daily_user_report():
    """
    Generate daily user activity report.
    Runs daily at 6:00 AM.
    """
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_start = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.time.min)
    )
    yesterday_end = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.time.max)
    )
    
    # Get yesterday's stats
    stats = {
        'date': yesterday.isoformat(),
        'new_searches': UserSearchHistory.objects.filter(
            searched_at__range=[yesterday_start, yesterday_end]
        ).count(),
        'new_interactions': UserVendorInteraction.objects.filter(
            interacted_at__range=[yesterday_start, yesterday_end]
        ).count(),
        'new_reel_views': NearbyReelView.objects.filter(
            viewed_at__range=[yesterday_start, yesterday_end]
        ).count(),
        'new_flash_alerts': FlashDealAlert.objects.filter(
            alerted_at__range=[yesterday_start, yesterday_end]
        ).count(),
    }
    
    # Calculate breakdowns
    stats['search_breakdown'] = list(
        UserSearchHistory.objects.filter(
            searched_at__range=[yesterday_start, yesterday_end]
        ).values('query_type').annotate(count=Count('id'))
    )
    
    stats['interaction_breakdown'] = list(
        UserVendorInteraction.objects.filter(
            interacted_at__range=[yesterday_start, yesterday_end]
        ).values('interaction_type').annotate(count=Count('id'))
    )
    
    # Store report in cache
    from django.core.cache import cache
    cache_key = f"daily_user_report:{yesterday.strftime('%Y%m%d')}"
    cache.set(cache_key, stats, timeout=86400 * 7)  # Keep for 7 days
    
    return stats


@shared_task(name='user_preferences.optimize_database_indexes')
def optimize_database_indexes():
    """
    Optimize database indexes for better performance.
    Runs weekly on Sundays at 2:00 AM.
    """
    from django.db import connection
    
    optimization_results = []
    
    # Analyze user_search_history table
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE user_search_history;")
        optimization_results.append("Analyzed user_search_history table")
    
    # Analyze user_vendor_interactions table
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE user_vendor_interactions;")
        optimization_results.append("Analyzed user_vendor_interactions table")
    
    # Analyze nearby_reel_views table
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE nearby_reel_views;")
        optimization_results.append("Analyzed nearby_reel_views table")
    
    # Analyze flash_deal_alerts table
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE flash_deal_alerts;")
        optimization_results.append("Analyzed flash_deal_alerts table")
    
    return {
        'message': 'Database optimization completed',
        'optimizations': optimization_results,
    }


@shared_task(name='user_preferences.cleanup_guest_preferences')
def cleanup_guest_preferences():
    """
    Clean up preferences for expired guest tokens.
    Runs daily at 3:00 AM.
    """
    from apps.customer_auth.models import GuestToken
    from .models import UserPreference
    
    # Get expired guest tokens
    expired_tokens = GuestToken.objects.filter(
        expires_at__lt=timezone.now()
    ).values_list('token', flat=True)
    
    # Delete preferences for expired guest tokens
    deleted_count = UserPreference.objects.filter(
        guest_token__in=expired_tokens
    ).delete()[0]
    
    return {
        'deleted_count': deleted_count,
        'message': f'Cleaned up preferences for {deleted_count} expired guest tokens'
    }
