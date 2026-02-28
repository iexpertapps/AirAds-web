"""
Business Metrics Dashboard for AirAds User Portal
Comprehensive KPI dashboard for business intelligence
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F, Window
from django.db.models.functions import Trunc, TruncDay, TruncHour, TruncMonth
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache

from apps.customer_auth.models import CustomerUser
from apps.user_preferences.models import UserVendorInteraction, UserSearchHistory
from apps.user_portal.models import Vendor, Promotion, VendorReel
from apps.user_portal.models_backup import BackupLog, RecoveryLog
from apps.user_portal.models_error import ErrorLog
from .logging import structured_logger


class BusinessMetricsDashboard(View):
    """
    Business metrics dashboard view.
    Provides comprehensive KPI data for business intelligence.
    """
    
    def __init__(self):
        self.logger = structured_logger
        self.cache_timeout = 300  # 5 minutes
    
    def get(self, request):
        """Get comprehensive business metrics dashboard."""
        try:
            # Get time ranges
            now = timezone.now()
            time_ranges = {
                'last_24h': now - timedelta(days=1),
                'last_7d': now - timedelta(days=7),
                'last_30d': now - timedelta(days=30),
                'last_90d': now - timedelta(days=90),
            }
            
            # Generate dashboard data
            dashboard_data = {
                'timestamp': now.isoformat(),
                'overview': self._get_overview_metrics(time_ranges),
                'user_analytics': self._get_user_analytics(time_ranges),
                'vendor_analytics': self._get_vendor_analytics(time_ranges),
                'engagement_analytics': self._get_engagement_analytics(time_ranges),
                'search_analytics': self._get_search_analytics(time_ranges),
                'promotion_analytics': self._get_promotion_analytics(time_ranges),
                'revenue_analytics': self._get_revenue_analytics(time_ranges),
                'performance_analytics': self._get_performance_analytics(time_ranges),
                'trend_analysis': self._get_trend_analysis(time_ranges),
                'geographic_analytics': self._get_geographic_analytics(time_ranges),
            }
            
            return JsonResponse(dashboard_data)
            
        except Exception as e:
            self.logger.error("Failed to generate business metrics dashboard", error=str(e))
            return JsonResponse(
                {'error': 'Failed to generate dashboard data', 'message': str(e)},
                status=500
            )
    
    def _get_overview_metrics(self, time_ranges: Dict) -> Dict:
        """Get overview KPI metrics."""
        cache_key = 'business_overview_metrics'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        metrics = {}
        
        for range_name, start_date in time_ranges.items():
            # User metrics
            total_users = CustomerUser.objects.filter(created_at__gte=start_date).count()
            active_users = CustomerUser.objects.filter(
                user__last_login__gte=start_date
            ).count()
            
            # Vendor metrics
            total_vendors = Vendor.objects.filter(created_at__gte=start_date, is_active=True).count()
            verified_vendors = Vendor.objects.filter(
                created_at__gte=start_date,
                is_active=True,
                is_verified=True
            ).count()
            
            # Interaction metrics
            total_interactions = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).count()
            unique_users_engaged = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).values('user_id').distinct().count()
            
            # Search metrics
            total_searches = UserSearchHistory.objects.filter(
                searched_at__gte=start_date
            ).count()
            
            # Error metrics
            total_errors = ErrorLog.objects.filter(occurred_at__gte=start_date).count()
            
            metrics[range_name] = {
                'users': {
                    'total_registered': total_users,
                    'active': active_users,
                    'engagement_rate': (active_users / max(total_users, 1)) * 100
                },
                'vendors': {
                    'total': total_vendors,
                    'verified': verified_vendors,
                    'verification_rate': (verified_vendors / max(total_vendors, 1)) * 100
                },
                'engagement': {
                    'total_interactions': total_interactions,
                    'unique_users_engaged': unique_users_engaged,
                    'avg_interactions_per_user': total_interactions / max(unique_users_engaged, 1)
                },
                'search': {
                    'total_searches': total_searches,
                    'searches_per_user': total_searches / max(active_users, 1)
                },
                'errors': {
                    'total_errors': total_errors,
                    'error_rate': (total_errors / max(total_interactions, 1)) * 100
                }
            }
        
        cache.set(cache_key, metrics, self.cache_timeout)
        return metrics
    
    def _get_user_analytics(self, time_ranges: Dict) -> Dict:
        """Get detailed user analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # User growth over time
            user_growth = CustomerUser.objects.filter(
                created_at__gte=start_date
            ).annotate(
                date=TruncDay('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # User activity patterns
            activity_by_hour = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).annotate(
                hour=TruncHour('interacted_at')
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
            
            # User retention (simplified - users who returned after first interaction)
            first_interactions = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).values('user_id').annotate(
                first_interaction=Min('interacted_at')
            )
            
            returning_users = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).values('user_id').annotate(
                interaction_count=Count('id')
            ).filter(interaction_count__gt=1).count()
            
            analytics[range_name] = {
                'user_growth': list(user_growth),
                'activity_patterns': list(activity_by_hour),
                'returning_users': returning_users,
                'user_segments': self._get_user_segments(start_date)
            }
        
        return analytics
    
    def _get_user_segments(self, start_date) -> Dict:
        """Get user segmentation analytics."""
        # Segment users by activity level
        active_users = CustomerUser.objects.filter(
            user__last_login__gte=start_date
        )
        
        # Power users (high engagement)
        power_user_ids = UserVendorInteraction.objects.filter(
            interacted_at__gte=start_date
        ).values('user_id').annotate(
            interaction_count=Count('id')
        ).filter(interaction_count__gte=10).values('user_id')
        
        power_users = active_users.filter(user_id__in=power_user_ids).count()
        
        # Regular users (moderate engagement)
        regular_user_ids = UserVendorInteraction.objects.filter(
            interacted_at__gte=start_date
        ).values('user_id').annotate(
            interaction_count=Count('id')
        ).filter(interaction_count__gte=3, interaction_count__lt=10).values('user_id')
        
        regular_users = active_users.filter(user_id__in=regular_user_ids).count()
        
        # Casual users (low engagement)
        casual_users = active_users.count() - power_users - regular_users
        
        return {
            'power_users': power_users,
            'regular_users': regular_users,
            'casual_users': casual_users,
            'total_active': active_users.count()
        }
    
    def _get_vendor_analytics(self, time_ranges: Dict) -> Dict:
        """Get vendor analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # Vendor growth
            vendor_growth = Vendor.objects.filter(
                created_at__gte=start_date,
                is_active=True
            ).annotate(
                date=TruncDay('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # Vendor performance by tier
            tier_performance = Vendor.objects.filter(
                is_active=True
            ).values('tier').annotate(
                vendor_count=Count('id'),
                avg_popularity=Avg('popularity_score'),
                total_interactions=Count('uservendorinteraction')
            ).order_by('tier')
            
            # Top performing vendors
            top_vendors = Vendor.objects.filter(
                is_active=True
            ).annotate(
                interaction_count=Count('uservendorinteraction')
            ).order_by('-interaction_count')[:10]
            
            analytics[range_name] = {
                'vendor_growth': list(vendor_growth),
                'tier_performance': list(tier_performance),
                'top_vendors': [
                    {
                        'id': str(vendor.id),
                        'name': vendor.business_name,
                        'tier': vendor.tier,
                        'interactions': vendor.interaction_count
                    }
                    for vendor in top_vendors
                ]
            }
        
        return analytics
    
    def _get_engagement_analytics(self, time_ranges: Dict) -> Dict:
        """Get engagement analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # Engagement trends
            engagement_trends = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).annotate(
                date=TruncDay('interacted_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # Interaction types
            interaction_types = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).values('interaction_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Engagement by vendor tier
            engagement_by_tier = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date
            ).values('vendor__tier').annotate(
                count=Count('id')
            ).order_by('-count')
            
            analytics[range_name] = {
                'engagement_trends': list(engagement_trends),
                'interaction_types': list(interaction_types),
                'engagement_by_tier': list(engagement_by_tier)
            }
        
        return analytics
    
    def _get_search_analytics(self, time_ranges: Dict) -> Dict:
        """Get search analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # Search trends
            search_trends = UserSearchHistory.objects.filter(
                searched_at__gte=start_date
            ).annotate(
                date=TruncDay('searched_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # Top search terms
            top_search_terms = UserSearchHistory.objects.filter(
                searched_at__gte=start_date
            ).values('query').annotate(
                count=Count('id')
            ).order_by('-count')[:20]
            
            # Search types
            search_types = UserSearchHistory.objects.filter(
                searched_at__gte=start_date
            ).values('search_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Search success rate (results found)
            successful_searches = UserSearchHistory.objects.filter(
                searched_at__gte=start_date,
                results_count__gt=0
            ).count()
            
            total_searches = UserSearchHistory.objects.filter(
                searched_at__gte=start_date
            ).count()
            
            analytics[range_name] = {
                'search_trends': list(search_trends),
                'top_search_terms': list(top_search_terms),
                'search_types': list(search_types),
                'success_rate': (successful_searches / max(total_searches, 1)) * 100
            }
        
        return analytics
    
    def _get_promotion_analytics(self, time_ranges: Dict) -> Dict:
        """Get promotion analytics."""
        analytics = {}
        
        now = timezone.now()
        
        for range_name, start_date in time_ranges.items():
            # Active promotions
            active_promotions = Promotion.objects.filter(
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).count()
            
            # Promotion performance
            promotion_performance = Promotion.objects.filter(
                created_at__gte=start_date
            ).annotate(
                interaction_count=Count('uservendorinteraction')
            ).values(
                'discount_percent',
                'is_flash_deal',
                'interaction_count'
            ).order_by('-interaction_count')
            
            # Flash deal performance
            flash_deals = Promotion.objects.filter(
                is_flash_deal=True,
                created_at__gte=start_date
            ).annotate(
                interaction_count=Count('uservendorinteraction')
            ).order_by('-interaction_count')
            
            analytics[range_name] = {
                'active_promotions': active_promotions,
                'promotion_performance': list(promotion_performance),
                'top_flash_deals': [
                    {
                        'id': str(deal.id),
                        'title': deal.title,
                        'discount_percent': deal.discount_percent,
                        'interactions': deal.interaction_count
                    }
                    for deal in flash_deals[:10]
                ]
            }
        
        return analytics
    
    def _get_revenue_analytics(self, time_ranges: Dict) -> Dict:
        """Get revenue analytics (simplified for demo)."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # This would typically integrate with payment systems
            # For now, we'll provide placeholder metrics based on vendor tiers
            
            tier_revenue = Vendor.objects.filter(
                is_active=True
            ).values('tier').annotate(
                vendor_count=Count('id')
            )
            
            # Simulated revenue based on tier
            tier_multipliers = {
                'SILVER': 100,
                'GOLD': 250,
                'DIAMOND': 500,
                'PLATINUM': 1000
            }
            
            revenue_by_tier = []
            for tier_data in tier_revenue:
                tier = tier_data['tier']
                vendor_count = tier_data['vendor_count']
                estimated_revenue = vendor_count * tier_multipliers.get(tier, 0)
                
                revenue_by_tier.append({
                    'tier': tier,
                    'vendor_count': vendor_count,
                    'estimated_revenue': estimated_revenue
                })
            
            total_revenue = sum(item['estimated_revenue'] for item in revenue_by_tier)
            
            analytics[range_name] = {
                'revenue_by_tier': revenue_by_tier,
                'total_estimated_revenue': total_revenue,
                'revenue_per_vendor': total_revenue / max(Vendor.objects.filter(is_active=True).count(), 1)
            }
        
        return analytics
    
    def _get_performance_analytics(self, time_ranges: Dict) -> Dict:
        """Get system performance analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # Error analysis
            error_analysis = ErrorLog.objects.filter(
                occurred_at__gte=start_date
            ).values('error_type', 'severity').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Backup performance
            backup_performance = BackupLog.objects.filter(
                started_at__gte=start_date
            ).values('backup_type').annotate(
                avg_duration=Avg('duration_seconds'),
                avg_size=Avg('backup_size_bytes'),
                success_rate=Avg('success') * 100
            )
            
            # Response time trends (placeholder - would come from APM)
            response_time_trends = []  # Implement with actual APM data
            
            analytics[range_name] = {
                'error_analysis': list(error_analysis),
                'backup_performance': list(backup_performance),
                'response_time_trends': response_time_trends
            }
        
        return analytics
    
    def _get_trend_analysis(self, time_ranges: Dict) -> Dict:
        """Get trend analysis and predictions."""
        trends = {}
        
        # User growth trend
        user_growth_7d = CustomerUser.objects.filter(
            created_at__gte=time_ranges['last_7d']
        ).count()
        user_growth_30d = CustomerUser.objects.filter(
            created_at__gte=time_ranges['last_30d']
        ).count()
        
        user_growth_rate = (user_growth_7d / 7) / (user_growth_30d / 30) if user_growth_30d > 0 else 0
        
        # Engagement trend
        engagement_7d = UserVendorInteraction.objects.filter(
            interacted_at__gte=time_ranges['last_7d']
        ).count()
        engagement_30d = UserVendorInteraction.objects.filter(
            interacted_at__gte=time_ranges['last_30d']
        ).count()
        
        engagement_growth_rate = (engagement_7d / 7) / (engagement_30d / 30) if engagement_30d > 0 else 0
        
        trends = {
            'user_growth': {
                'current_rate': user_growth_7d / 7,
                'growth_trend': 'increasing' if user_growth_rate > 1 else 'decreasing',
                'trend_percentage': (user_growth_rate - 1) * 100
            },
            'engagement': {
                'current_rate': engagement_7d / 7,
                'growth_trend': 'increasing' if engagement_growth_rate > 1 else 'decreasing',
                'trend_percentage': (engagement_growth_rate - 1) * 100
            }
        }
        
        return trends
    
    def _get_geographic_analytics(self, time_ranges: Dict) -> Dict:
        """Get geographic analytics."""
        analytics = {}
        
        for range_name, start_date in time_ranges.items():
            # Vendor distribution by city
            vendor_by_city = Vendor.objects.filter(
                is_active=True
            ).values('city__name').annotate(
                count=Count('id')
            ).order_by('-count')[:20]
            
            # User interactions by city
            interactions_by_city = UserVendorInteraction.objects.filter(
                interacted_at__gte=start_date,
                vendor__city__isnull=False
            ).values('vendor__city__name').annotate(
                count=Count('id')
            ).order_by('-count')[:20]
            
            analytics[range_name] = {
                'vendor_distribution': list(vendor_by_city),
                'interaction_distribution': list(interactions_by_city)
            }
        
        return analytics


# Import Min function for user analytics
from django.db.models import Min
