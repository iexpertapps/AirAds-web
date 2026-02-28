from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView
from apps.customer_auth.models import CustomerUser


class UserPreferenceService:
    """
    Service layer for user preferences management.
    Handles preferences for both authenticated users and guests.
    """
    
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def get_preferences(cls, user_or_guest):
        """
        Get preferences for user or guest.
        Returns cached preferences if available.
        """
        # Generate cache key
        if hasattr(user_or_guest, 'customer_profile') or isinstance(user_or_guest, CustomerUser):
            # Handle authenticated user
            if hasattr(user_or_guest, 'customer_profile'):
                user_profile = user_or_guest.customer_profile
            else:
                user_profile = user_or_guest
            cache_key = f"user_prefs:{user_profile.id}"
            preference_obj = UserPreference.get_for_user(user_profile)
        else:
            # Handle guest token (could be string or UUID object)
            if hasattr(user_or_guest, 'token'):
                guest_token = user_or_guest.token
            else:
                guest_token = user_or_guest
            cache_key = f"guest_prefs:{guest_token}"
            preference_obj = UserPreference.get_for_guest(guest_token)
        
        if not preference_obj:
            return None
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Build preferences data
        preferences_data = {
            'default_view': preference_obj.default_view,
            'search_radius_m': preference_obj.search_radius_m,
            'show_open_now_only': preference_obj.show_open_now_only,
            'preferred_category_slugs': preference_obj.preferred_category_slugs,
            'price_range': preference_obj.price_range,
            'theme': preference_obj.theme,
            'notifications': {
                'nearby_deals': preference_obj.notifications_nearby_deals,
                'flash_deals': preference_obj.notifications_flash_deals,
                'new_vendors': preference_obj.notifications_new_vendors,
                'all_off': preference_obj.notifications_all_off,
            },
            'location': {
                'auto_enabled': preference_obj.auto_location_enabled,
                'manual_lat': float(preference_obj.manual_location_lat) if preference_obj.manual_location_lat else None,
                'manual_lng': float(preference_obj.manual_location_lng) if preference_obj.manual_location_lng else None,
                'manual_name': preference_obj.manual_location_name,
            },
            'updated_at': preference_obj.updated_at.isoformat(),
        }
        
        # Cache the result
        cache.set(cache_key, preferences_data, timeout=cls.CACHE_TIMEOUT)
        
        return preferences_data
    
    @classmethod
    def update_preferences(cls, user_or_guest, preferences_data):
        """
        Update preferences for user or guest.
        """
        with transaction.atomic():
            # Get or create preference object
            if hasattr(user_or_guest, 'customer_profile') or isinstance(user_or_guest, CustomerUser):
                # Handle authenticated user
                if hasattr(user_or_guest, 'customer_profile'):
                    user_profile = user_or_guest.customer_profile
                else:
                    user_profile = user_or_guest
                preference_obj = UserPreference.get_for_user(user_profile)
                cache_key = f"user_prefs:{user_profile.id}"
            else:
                # Handle guest token (could be string or UUID object)
                if hasattr(user_or_guest, 'token'):
                    guest_token = user_or_guest.token
                else:
                    guest_token = user_or_guest
                preference_obj = UserPreference.get_for_guest(guest_token)
                cache_key = f"guest_prefs:{guest_token}"
            
            # Update allowed fields
            updatable_fields = [
                'default_view', 'search_radius_m', 'show_open_now_only',
                'preferred_category_slugs', 'price_range', 'theme',
                'notifications_nearby_deals', 'notifications_flash_deals',
                'notifications_new_vendors', 'notifications_all_off',
                'auto_location_enabled', 'manual_location_lat', 'manual_location_lng',
                'manual_location_name'
            ]
            
            for field in updatable_fields:
                if field in preferences_data:
                    setattr(preference_obj, field, preferences_data[field])
            
            preference_obj.save()
            
            # Clear cache
            cache.delete(cache_key)
            
            # Return updated preferences
            return cls.get_preferences(user_or_guest)
    
    @classmethod
    def migrate_guest_preferences(cls, guest_token_str, customer_user):
        """
        Migrate guest preferences to user account.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            guest_preference = UserPreference.objects.get(guest_token=guest_uuid)
            
            # Get user preferences
            user_preference = UserPreference.get_for_user(customer_user)
            
            # Merge preferences (guest preferences take precedence if user has defaults)
            merge_fields = [
                'default_view', 'search_radius_m', 'show_open_now_only',
                'preferred_category_slugs', 'price_range', 'theme',
                'notifications_nearby_deals', 'notifications_flash_deals',
                'notifications_new_vendors', 'notifications_all_off',
                'auto_location_enabled', 'manual_location_lat', 'manual_location_lng',
                'manual_location_name'
            ]
            
            for field in merge_fields:
                guest_value = getattr(guest_preference, field)
                user_value = getattr(user_preference, field)
                
                # Use guest value if user has default value
                if (guest_value is not None and 
                    (user_value is None or 
                     field in ['default_view', 'search_radius_m', 'theme'] and 
                     user_value in ['AR', 500, 'DARK'])):  # Default values
                    setattr(user_preference, field, guest_value)
            
            user_preference.save()
            
            # Clear guest token from guest preference
            guest_preference.guest_token = None
            guest_preference.save()
            
            # Clear caches
            cache.delete(f"guest_prefs:{guest_uuid}")
            cache.delete(f"user_prefs:{customer_user.id}")
            
            return True
            
        except (ValueError, UserPreference.DoesNotExist):
            return False
    
    @classmethod
    def clear_guest_preferences(cls, guest_token_str):
        """
        Clear guest preferences (cleanup after migration or expiry).
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            UserPreference.objects.filter(guest_token=guest_uuid).delete()
            cache.delete(f"guest_prefs:{guest_uuid}")
            return True
        except (ValueError, UserPreference.DoesNotExist):
            return False


class SearchHistoryService:
    """
    Service layer for user search history management.
    """
    
    @classmethod
    def record_search(cls, user_or_guest, query_text, query_type, **kwargs):
        """
        Record a search query in history.
        """
        return UserSearchHistory.record_search(user_or_guest, query_text, query_type, **kwargs)
    
    @classmethod
    def get_search_history(cls, user_or_guest, limit=20):
        """
        Get search history for user or guest.
        """
        if hasattr(user_or_guest, 'customer_profile'):
            history = UserSearchHistory.objects.filter(
                user=user_or_guest.customer_profile
            ).order_by('-searched_at')[:limit]
        else:
            history = UserSearchHistory.objects.filter(
                guest_token=user_or_guest
            ).order_by('-searched_at')[:limit]
        
        return [
            {
                'id': str(search.id),
                'query_text': search.query_text,
                'query_type': search.query_type,
                'extracted_category': search.extracted_category,
                'extracted_intent': search.extracted_intent,
                'result_count': search.result_count,
                'navigated_to_vendor_id': str(search.navigated_to_vendor_id) if search.navigated_to_vendor_id else None,
                'searched_at': search.searched_at.isoformat(),
            }
            for search in history
        ]
    
    @classmethod
    def clear_search_history(cls, user_or_guest):
        """
        Clear all search history for user or guest.
        """
        if hasattr(user_or_guest, 'customer_profile'):
            deleted_count = UserSearchHistory.objects.filter(
                user=user_or_guest.customer_profile
            ).delete()[0]
        else:
            deleted_count = UserSearchHistory.objects.filter(
                guest_token=user_or_guest
            ).delete()[0]
        
        return deleted_count
    
    @classmethod
    def migrate_search_history(cls, guest_token_str, customer_user):
        """
        Migrate guest search history to user account.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            
            # Update guest history records to belong to user
            updated_count = UserSearchHistory.objects.filter(
                guest_token=guest_uuid
            ).update(
                user=customer_user,
                guest_token=None
            )
            
            return updated_count
            
        except (ValueError, UserSearchHistory.DoesNotExist):
            return 0


class InteractionService:
    """
    Service layer for user-vendor interaction tracking.
    """
    
    @classmethod
    def record_interaction(cls, user_or_guest, vendor_id, interaction_type, 
                          session_id=None, lat=None, lng=None, **metadata):
        """
        Record a vendor interaction.
        """
        return UserVendorInteraction.record_interaction(
            user_or_guest, vendor_id, interaction_type, session_id, lat, lng, **metadata
        )
    
    @classmethod
    def get_interaction_count(cls, user_or_guest, interaction_type=None, days=30):
        """
        Get interaction count for user or guest.
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        if hasattr(user_or_guest, 'customer_profile'):
            queryset = UserVendorInteraction.objects.filter(
                user=user_or_guest.customer_profile,
                interacted_at__gte=cutoff_date
            )
        else:
            queryset = UserVendorInteraction.objects.filter(
                guest_token=user_or_guest,
                interacted_at__gte=cutoff_date
            )
        
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)
        
        return queryset.count()
    
    @classmethod
    def get_recent_interactions(cls, user_or_guest, limit=50):
        """
        Get recent interactions for user or guest.
        """
        if hasattr(user_or_guest, 'customer_profile'):
            interactions = UserVendorInteraction.objects.filter(
                user=user_or_guest.customer_profile
            ).order_by('-interacted_at')[:limit]
        else:
            interactions = UserVendorInteraction.objects.filter(
                guest_token=user_or_guest
            ).order_by('-interacted_at')[:limit]
        
        return [
            {
                'id': str(interaction.id),
                'vendor_id': str(interaction.vendor_id),
                'interaction_type': interaction.interaction_type,
                'session_id': str(interaction.session_id),
                'lat': float(interaction.lat) if interaction.lat else None,
                'lng': float(interaction.lng) if interaction.lng else None,
                'metadata': interaction.metadata,
                'interacted_at': interaction.interacted_at.isoformat(),
            }
            for interaction in interactions
        ]
    
    @classmethod
    def migrate_interactions(cls, guest_token_str, customer_user):
        """
        Migrate guest interactions to user account.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            
            # Update guest interaction records to belong to user
            updated_count = UserVendorInteraction.objects.filter(
                guest_token=guest_uuid
            ).update(
                user=customer_user,
                guest_token=None
            )
            
            return updated_count
            
        except (ValueError, UserVendorInteraction.DoesNotExist):
            return 0


class FlashDealService:
    """
    Service layer for flash deal alerts.
    """
    
    @classmethod
    def should_alert(cls, user_or_guest, discount_id, vendor_id):
        """
        Check if user should be alerted about flash deal.
        """
        return FlashDealAlert.should_alert(user_or_guest, discount_id, vendor_id)
    
    @classmethod
    def create_alert(cls, user_or_guest, discount_id, vendor_id):
        """
        Create flash deal alert.
        """
        return FlashDealAlert.create_alert(user_or_guest, discount_id, vendor_id)
    
    @classmethod
    def dismiss_alert(cls, user_or_guest, discount_id):
        """
        Dismiss flash deal alert.
        """
        if hasattr(user_or_guest, 'customer_profile'):
            updated = FlashDealAlert.objects.filter(
                user=user_or_guest.customer_profile,
                discount_id=discount_id,
                dismissed=False
            ).update(
                dismissed=True,
                dismissed_at=timezone.now()
            )
        else:
            updated = FlashDealAlert.objects.filter(
                guest_token=user_or_guest,
                discount_id=discount_id,
                dismissed=False
            ).update(
                dismissed=True,
                dismissed_at=timezone.now()
            )
        
        return updated > 0
    
    @classmethod
    def tap_alert(cls, user_or_guest, discount_id):
        """
        Record tap on flash deal alert.
        """
        if hasattr(user_or_guest, 'customer_profile'):
            updated = FlashDealAlert.objects.filter(
                user=user_or_guest.customer_profile,
                discount_id=discount_id
            ).update(
                tapped=True,
                tapped_at=timezone.now()
            )
        else:
            updated = FlashDealAlert.objects.filter(
                guest_token=user_or_guest,
                discount_id=discount_id
            ).update(
                tapped=True,
                tapped_at=timezone.now()
            )
        
        return updated > 0
    
    @classmethod
    def migrate_flash_alerts(cls, guest_token_str, customer_user):
        """
        Migrate guest flash alerts to user account.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            
            # Update guest alert records to belong to user
            updated_count = FlashDealAlert.objects.filter(
                guest_token=guest_uuid
            ).update(
                user=customer_user,
                guest_token=None
            )
            
            return updated_count
            
        except (ValueError, FlashDealAlert.DoesNotExist):
            return 0


class ReelViewService:
    """
    Service layer for reel view tracking.
    """
    
    @classmethod
    def record_view(cls, user_or_guest, reel_id, vendor_id, **kwargs):
        """
        Record a reel view.
        """
        return NearbyReelView.record_view(user_or_guest, reel_id, vendor_id, **kwargs)
    
    @classmethod
    def get_view_stats(cls, user_or_guest, days=30):
        """
        Get reel viewing statistics for user or guest.
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        if hasattr(user_or_guest, 'customer_profile'):
            queryset = NearbyReelView.objects.filter(
                user=user_or_guest.customer_profile,
                viewed_at__gte=cutoff_date
            )
        else:
            queryset = NearbyReelView.objects.filter(
                guest_token=user_or_guest,
                viewed_at__gte=cutoff_date
            )
        
        total_views = queryset.count()
        completed_views = queryset.filter(completed=True).count()
        cta_taps = queryset.filter(cta_tapped=True).count()
        total_watch_time = queryset.aggregate(
            total=models.Sum('watched_seconds')
        )['total'] or 0
        
        return {
            'total_views': total_views,
            'completed_views': completed_views,
            'completion_rate': (completed_views / total_views * 100) if total_views > 0 else 0,
            'cta_taps': cta_taps,
            'cta_tap_rate': (cta_taps / total_views * 100) if total_views > 0 else 0,
            'total_watch_time_seconds': total_watch_time,
            'avg_watch_time_seconds': (total_watch_time / total_views) if total_views > 0 else 0,
        }
    
    @classmethod
    def migrate_reel_views(cls, guest_token_str, customer_user):
        """
        Migrate guest reel views to user account.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            
            # Update guest reel view records to belong to user
            updated_count = NearbyReelView.objects.filter(
                guest_token=guest_uuid
            ).update(
                user=customer_user,
                guest_token=None
            )
            
            return updated_count
            
        except (ValueError, NearbyReelView.DoesNotExist):
            return 0


class MigrationService:
    """
    Service for migrating guest data to user account during login.
    """
    
    @classmethod
    def migrate_all_guest_data(cls, guest_token_str, customer_user):
        """
        Migrate all guest data to user account.
        """
        migration_results = {
            'preferences': UserPreferenceService.migrate_guest_preferences(guest_token_str, customer_user),
            'search_history': SearchHistoryService.migrate_search_history(guest_token_str, customer_user),
            'interactions': InteractionService.migrate_interactions(guest_token_str, customer_user),
            'flash_alerts': FlashDealService.migrate_flash_alerts(guest_token_str, customer_user),
            'reel_views': ReelViewService.migrate_reel_views(guest_token_str, customer_user),
        }
        
        # Clean up guest preferences after migration
        UserPreferenceService.clear_guest_preferences(guest_token_str)
        
        return migration_results
