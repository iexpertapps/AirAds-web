"""
Unit tests for User Preferences services.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from ..services import (
    UserPreferenceService,
    SearchHistoryService,
    InteractionService,
    FlashDealService,
    ReelViewService,
)
from ..models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView
from apps.customer_auth.models import CustomerUser, GuestToken

User = get_user_model()


class UserPreferenceServiceTest(TestCase):
    """Test cases for UserPreferenceService."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_get_preferences_authenticated_user(self):
        """Test getting preferences for authenticated user."""
        # Create user preferences
        UserPreference.objects.create(
            user=self.customer_user,
            default_view='MAP',
            search_radius_m=1000,
            preferred_category_slugs=['RESTAURANT', 'CAFE'],
            price_range='PREMIUM',
            theme='DARK',
            notifications_nearby_deals=True,
            notifications_flash_deals=True,
            notifications_new_vendors=False,
        )
        
        result = UserPreferenceService.get_preferences(self.customer_user)
        
        self.assertEqual(result['default_view'], 'MAP')
        self.assertEqual(result['search_radius_m'], 1000)
        self.assertEqual(result['preferred_category_slugs'], ['RESTAURANT', 'CAFE'])
        self.assertEqual(result['price_range'], 'PREMIUM')
        self.assertEqual(result['theme'], 'DARK')
        self.assertTrue(result['notifications_nearby_deals'])
        self.assertTrue(result['notifications_flash_deals'])
        self.assertFalse(result['notifications_new_vendors'])
    
    def test_get_preferences_guest_user(self):
        """Test getting preferences for guest user."""
        # Create guest preferences
        UserPreference.objects.create(
            guest_token=self.guest_token.token,
            default_view='AR',
            search_radius_m=500,
            preferred_category_slugs=['FOOD'],
            price_range='MID',
            theme='LIGHT',
        )
        
        result = UserPreferenceService.get_preferences(self.guest_token.token)
        
        self.assertEqual(result['default_view'], 'AR')
        self.assertEqual(result['search_radius_m'], 500)
        self.assertEqual(result['preferred_category_slugs'], ['FOOD'])
        self.assertEqual(result['price_range'], 'MID')
        self.assertEqual(result['theme'], 'LIGHT')
    
    def test_get_preferences_default_values(self):
        """Test getting preferences with default values."""
        result = UserPreferenceService.get_preferences(self.customer_user)
        
        # Should return default values
        self.assertEqual(result['default_view'], 'AR')
        self.assertEqual(result['search_radius_m'], 500)
        self.assertEqual(result['price_range'], 'MID')
        self.assertEqual(result['theme'], 'DARK')
        self.assertTrue(result['notifications_nearby_deals'])
        self.assertTrue(result['notifications_flash_deals'])
        self.assertTrue(result['notifications_new_vendors'])
    
    def test_update_preferences_authenticated_user(self):
        """Test updating preferences for authenticated user."""
        preferences_data = {
            'default_view': 'LIST',
            'search_radius_m': 2000,
            'preferred_category_slugs': ['SHOPPING', 'ENTERTAINMENT'],
            'price_range': 'BUDGET',
            'theme': 'LIGHT',
            'notifications_nearby_deals': False,
            'notifications_flash_deals': True,
            'notifications_new_vendors': True,
        }
        
        result = UserPreferenceService.update_preferences(
            self.customer_user,
            preferences_data
        )
        
        self.assertEqual(result['default_view'], 'LIST')
        self.assertEqual(result['search_radius_m'], 2000)
        self.assertEqual(result['preferred_category_slugs'], ['SHOPPING', 'ENTERTAINMENT'])
        self.assertEqual(result['price_range'], 'BUDGET')
        self.assertEqual(result['theme'], 'LIGHT')
        self.assertFalse(result['notifications_nearby_deals'])
        self.assertTrue(result['notifications_flash_deals'])
        self.assertTrue(result['notifications_new_vendors'])
    
    def test_update_preferences_guest_user(self):
        """Test updating preferences for guest user."""
        preferences_data = {
            'default_view': 'MAP',
            'search_radius_m': 1500,
            'price_range': 'PREMIUM',
        }
        
        result = UserPreferenceService.update_preferences(
            self.guest_token.token,
            preferences_data
        )
        
        self.assertEqual(result['default_view'], 'MAP')
        self.assertEqual(result['search_radius_m'], 1500)
        self.assertEqual(result['price_range'], 'PREMIUM')
    
    def test_update_preferences_partial_update(self):
        """Test partial preference update."""
        # Create existing preferences
        UserPreference.objects.create(
            user=self.customer_user,
            default_view='AR',
            search_radius_m=500,
            theme='DARK',
        )
        
        # Update only some fields
        preferences_data = {
            'search_radius_m': 1000,
            'price_range': 'PREMIUM',
        }
        
        result = UserPreferenceService.update_preferences(
            self.customer_user,
            preferences_data
        )
        
        # Should update only specified fields
        self.assertEqual(result['default_view'], 'AR')  # Unchanged
        self.assertEqual(result['search_radius_m'], 1000)  # Updated
        self.assertEqual(result['price_range'], 'PREMIUM')  # Updated
        self.assertEqual(result['theme'], 'DARK')  # Unchanged
    
    def test_update_preferences_caching(self):
        """Test preference caching."""
        # First call should fetch from database
        result1 = UserPreferenceService.get_preferences(self.customer_user)
        
        # Second call should use cache
        result2 = UserPreferenceService.get_preferences(self.customer_user)
        
        self.assertEqual(result1, result2)
        
        # Update preferences should invalidate cache
        UserPreferenceService.update_preferences(
            self.customer_user,
            {'search_radius_m': 1000}
        )
        
        # Next call should fetch updated data
        result3 = UserPreferenceService.get_preferences(self.customer_user)
        self.assertEqual(result3['search_radius_m'], 1000)


class SearchHistoryServiceTest(TestCase):
    """Test cases for SearchHistoryService."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_record_search_authenticated_user(self):
        """Test recording search for authenticated user."""
        result = SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='pakistani restaurant',
            query_type='TEXT',
            search_lat=24.8607,
            search_lng=67.0011,
            search_radius_m=5000,
            result_count=15,
            navigated_to_vendor_id=uuid.uuid4()
        )
        
        self.assertTrue(result)
        
        # Verify search history record
        search_history = UserSearchHistory.objects.get(user=self.customer_user)
        self.assertEqual(search_history.query_text, 'pakistani restaurant')
        self.assertEqual(search_history.query_type, 'TEXT')
        self.assertEqual(search_history.search_lat, 24.8607)
        self.assertEqual(search_history.search_lng, 67.0011)
        self.assertEqual(search_history.search_radius_m, 5000)
        self.assertEqual(search_history.result_count, 15)
        self.assertIsNotNone(search_history.navigated_to_vendor_id)
    
    def test_record_search_guest_user(self):
        """Test recording search for guest user."""
        result = SearchHistoryService.record_search(
            user_or_guest=self.guest_token.token,
            query_text='cafe near me',
            query_type='VOICE',
            search_lat=24.8607,
            search_lng=67.0011,
            search_radius_m=2000,
            result_count=8
        )
        
        self.assertTrue(result)
        
        # Verify search history record
        search_history = UserSearchHistory.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(search_history.query_text, 'cafe near me')
        self.assertEqual(search_history.query_type, 'VOICE')
        self.assertEqual(search_history.result_count, 8)
    
    def test_record_search_intent_extraction(self):
        """Test search intent extraction during recording."""
        result = SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='cheap pakistani food',
            query_type='TEXT',
            search_lat=24.8607,
            search_lng=67.0011,
            search_radius_m=5000,
            result_count=10
        )
        
        self.assertTrue(result)
        
        # Verify extracted intent
        search_history = UserSearchHistory.objects.get(user=self.customer_user)
        self.assertEqual(search_history.extracted_category, 'RESTAURANT')
        self.assertEqual(search_history.extracted_price_range, 'BUDGET')
    
    def test_get_search_history_authenticated_user(self):
        """Test getting search history for authenticated user."""
        # Create some search history
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            result_count=10
        )
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='cafe',
            query_type='VOICE',
            result_count=5
        )
        
        history = SearchHistoryService.get_search_history(
            self.customer_user,
            limit=10
        )
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['query_text'], 'cafe')  # Most recent first
        self.assertEqual(history[1]['query_text'], 'restaurant')
    
    def test_get_search_history_guest_user(self):
        """Test getting search history for guest user."""
        # Create search history for guest
        SearchHistoryService.record_search(
            user_or_guest=self.guest_token.token,
            query_text='food',
            query_type='TEXT',
            result_count=8
        )
        
        history = SearchHistoryService.get_search_history(
            self.guest_token.token,
            limit=10
        )
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['query_text'], 'food')
    
    def test_get_search_history_with_limit(self):
        """Test getting search history with limit."""
        # Create more search history than limit
        for i in range(15):
            SearchHistoryService.record_search(
                user_or_guest=self.customer_user,
                query_text=f'search {i}',
                query_type='TEXT',
                result_count=i
            )
        
        history = SearchHistoryService.get_search_history(
            self.customer_user,
            limit=10
        )
        
        self.assertEqual(len(history), 10)  # Should be limited
    
    def test_get_search_stats(self):
        """Test getting search statistics."""
        # Create search history with different types
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            result_count=10
        )
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='cafe',
            query_type='VOICE',
            result_count=5
        )
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='food',
            query_type='TEXT',
            result_count=8
        )
        
        stats = SearchHistoryService.get_search_stats(self.customer_user, days=30)
        
        self.assertEqual(stats['total_searches'], 3)
        self.assertEqual(stats['text_searches'], 2)
        self.assertEqual(stats['voice_searches'], 1)
        self.assertEqual(stats['avg_results_per_search'], 7.67)  # (10+5+8)/3
        self.assertIn('most_common_categories', stats)
        self.assertIn('search_frequency', stats)


class InteractionServiceTest(TestCase):
    """Test cases for InteractionService."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        
        self.vendor_id = uuid.uuid4()
        self.session_id = uuid.uuid4()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_record_interaction_authenticated_user(self):
        """Test recording interaction for authenticated user."""
        result = InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            lat=24.8607,
            lng=67.0011,
            metadata={'source': 'search'}
        )
        
        self.assertTrue(result)
        
        # Verify interaction record
        interaction = UserVendorInteraction.objects.get(user=self.customer_user)
        self.assertEqual(str(interaction.vendor_id), str(self.vendor_id))
        self.assertEqual(interaction.interaction_type, 'VIEW')
        self.assertEqual(str(interaction.session_id), str(self.session_id))
        self.assertEqual(interaction.lat, 24.8607)
        self.assertEqual(interaction.lng, 67.0011)
        self.assertEqual(interaction.metadata['source'], 'search')
    
    def test_record_interaction_guest_user(self):
        """Test recording interaction for guest user."""
        result = InteractionService.record_interaction(
            user_or_guest=self.guest_token.token,
            vendor_id=self.vendor_id,
            interaction_type='TAP',
            session_id=self.session_id,
            lat=24.8607,
            lng=67.0011
        )
        
        self.assertTrue(result)
        
        # Verify interaction record
        interaction = UserVendorInteraction.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(interaction.interaction_type, 'TAP')
    
    def test_record_interaction_all_types(self):
        """Test recording all interaction types."""
        interaction_types = [
            'VIEW', 'TAP', 'NAVIGATION', 'CALL', 'REEL_VIEW',
            'PROMOTION_TAP', 'ARRIVAL', 'SHARE', 'FAVORITE'
        ]
        
        for i, interaction_type in enumerate(interaction_types):
            session_id = uuid.uuid4()
            InteractionService.record_interaction(
                user_or_guest=self.customer_user,
                vendor_id=uuid.uuid4(),
                interaction_type=interaction_type,
                session_id=session_id
            )
        
        # Verify all interactions were recorded
        interactions = UserVendorInteraction.objects.filter(user=self.customer_user)
        self.assertEqual(interactions.count(), len(interaction_types))
    
    def test_get_recent_interactions(self):
        """Test getting recent interactions."""
        # Create some interactions
        vendor_id1 = uuid.uuid4()
        vendor_id2 = uuid.uuid4()
        
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=vendor_id1,
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=vendor_id2,
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        interactions = InteractionService.get_recent_interactions(
            self.customer_user,
            limit=10
        )
        
        self.assertEqual(len(interactions), 2)
        self.assertEqual(interactions[0]['interaction_type'], 'TAP')  # Most recent first
        self.assertEqual(interactions[1]['interaction_type'], 'VIEW')
    
    def test_get_interaction_stats(self):
        """Test getting interaction statistics."""
        # Create interactions with different types
        vendor_id = uuid.uuid4()
        
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=uuid.uuid4(),  # Different vendor
            interaction_type='NAVIGATION',
            session_id=uuid.uuid4()
        )
        
        stats = InteractionService.get_interaction_stats(self.customer_user, days=30)
        
        self.assertEqual(stats['total_interactions'], 3)
        self.assertEqual(stats['unique_vendors'], 2)
        self.assertEqual(stats['interaction_breakdown']['VIEW'], 1)
        self.assertEqual(stats['interaction_breakdown']['TAP'], 1)
        self.assertEqual(stats['interaction_breakdown']['NAVIGATION'], 1)
    
    def test_get_favorite_vendors(self):
        """Test getting favorite vendors."""
        # Record some favorite interactions
        vendor_id1 = uuid.uuid4()
        vendor_id2 = uuid.uuid4()
        vendor_id3 = uuid.uuid4()
        
        # Vendor 1: 3 interactions
        for i in range(3):
            InteractionService.record_interaction(
                user_or_guest=self.customer_user,
                vendor_id=vendor_id1,
                interaction_type='VIEW',
                session_id=uuid.uuid4()
            )
        
        # Vendor 2: 1 interaction
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=vendor_id2,
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        
        # Vendor 3: 2 interactions
        for i in range(2):
            InteractionService.record_interaction(
                user_or_guest=self.customer_user,
                vendor_id=vendor_id3,
                interaction_type='VIEW',
                session_id=uuid.uuid4()
            )
        
        favorites = InteractionService.get_favorite_vendors(self.customer_user, limit=5)
        
        self.assertEqual(len(favorites), 3)
        self.assertEqual(str(favorites[0]['vendor_id']), str(vendor_id1))  # Most interactions first
        self.assertEqual(str(favorites[1]['vendor_id']), str(vendor_id3))
        self.assertEqual(str(favorites[2]['vendor_id']), str(vendor_id2))


class FlashDealServiceTest(TestCase):
    """Test cases for FlashDealService."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        
        self.discount_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_create_alert_authenticated_user(self):
        """Test creating flash deal alert for authenticated user."""
        result = FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertTrue(result)
        
        # Verify alert record
        alert = FlashDealAlert.objects.get(user=self.customer_user)
        self.assertEqual(str(alert.discount_id), str(self.discount_id))
        self.assertEqual(str(alert.vendor_id), str(self.vendor_id))
        self.assertFalse(alert.dismissed)
        self.assertFalse(alert.tapped)
    
    def test_create_alert_guest_user(self):
        """Test creating flash deal alert for guest user."""
        result = FlashDealService.create_alert(
            user_or_guest=self.guest_token.token,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertTrue(result)
        
        # Verify alert record
        alert = FlashDealAlert.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(str(alert.discount_id), str(self.discount_id))
    
    def test_create_alert_duplicate(self):
        """Test creating duplicate alert (should not create duplicate)."""
        # Create first alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Try to create duplicate
        result = FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertFalse(result)  # Should not create duplicate
        
        # Should still only have one alert
        alerts = FlashDealAlert.objects.filter(user=self.customer_user)
        self.assertEqual(alerts.count(), 1)
    
    def test_dismiss_alert(self):
        """Test dismissing flash deal alert."""
        # Create alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Dismiss alert
        result = FlashDealService.dismiss_alert(
            self.customer_user,
            self.discount_id
        )
        
        self.assertTrue(result)
        
        # Verify alert is dismissed
        alert = FlashDealAlert.objects.get(user=self.customer_user)
        self.assertTrue(alert.dismissed)
        self.assertIsNotNone(alert.dismissed_at)
    
    def test_tap_alert(self):
        """Test tapping flash deal alert."""
        # Create alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Tap alert
        result = FlashDealService.tap_alert(
            self.customer_user,
            self.discount_id
        )
        
        self.assertTrue(result)
        
        # Verify alert is tapped
        alert = FlashDealAlert.objects.get(user=self.customer_user)
        self.assertTrue(alert.tapped)
        self.assertIsNotNone(alert.tapped_at)
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        # Create some alerts
        discount_id2 = uuid.uuid4()
        
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=discount_id2,
            vendor_id=self.vendor_id
        )
        
        # Dismiss one alert
        FlashDealService.dismiss_alert(self.customer_user, discount_id2)
        
        active_alerts = FlashDealService.get_active_alerts(self.customer_user)
        
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(str(active_alerts[0]['discount_id']), str(self.discount_id))
    
    def test_should_alert(self):
        """Test alert eligibility check."""
        # First time - should alert
        should_alert = FlashDealService.should_alert(
            self.customer_user,
            self.discount_id,
            self.vendor_id
        )
        self.assertTrue(should_alert)
        
        # Create alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Second time - should not alert
        should_alert = FlashDealService.should_alert(
            self.customer_user,
            self.discount_id,
            self.vendor_id
        )
        self.assertFalse(should_alert)
    
    def test_cleanup_old_alerts(self):
        """Test cleaning up old alerts."""
        # Create old alert (91 days ago)
        old_alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            alerted_at=timezone.now() - timedelta(days=91)
        )
        
        # Create recent alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=self.vendor_id
        )
        
        # Cleanup old alerts
        cleaned_count = FlashDealService.cleanup_old_alerts(days_to_keep=90)
        
        self.assertEqual(cleaned_count, 1)
        
        # Verify old alert is gone, recent alert remains
        self.assertFalse(FlashDealAlert.objects.filter(id=old_alert.id).exists())
        self.assertEqual(FlashDealAlert.objects.filter(user=self.customer_user).count(), 1)


class ReelViewServiceTest(TestCase):
    """Test cases for ReelViewService."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )
        
        self.reel_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_record_view_authenticated_user(self):
        """Test recording reel view for authenticated user."""
        result = ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=25,
            completed=True,
            cta_tapped=True,
            lat=24.8607,
            lng=67.0011
        )
        
        self.assertTrue(result)
        
        # Verify view record
        view = NearbyReelView.objects.get(user=self.customer_user)
        self.assertEqual(str(view.reel_id), str(self.reel_id))
        self.assertEqual(str(view.vendor_id), str(self.vendor_id))
        self.assertEqual(view.watched_seconds, 25)
        self.assertTrue(view.completed)
        self.assertTrue(view.cta_tapped)
        self.assertEqual(view.lat, 24.8607)
        self.assertEqual(view.lng, 67.0011)
    
    def test_record_view_guest_user(self):
        """Test recording reel view for guest user."""
        result = ReelViewService.record_view(
            user_or_guest=self.guest_token.token,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=15,
            completed=False,
            cta_tapped=False
        )
        
        self.assertTrue(result)
        
        # Verify view record
        view = NearbyReelView.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(view.watched_seconds, 15)
        self.assertFalse(view.completed)
        self.assertFalse(view.cta_tapped)
    
    def test_get_view_stats(self):
        """Test getting view statistics."""
        # Create some views
        reel_id2 = uuid.uuid4()
        
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30,
            completed=True,
            cta_tapped=True
        )
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=reel_id2,
            vendor_id=self.vendor_id,
            watched_seconds=15,
            completed=False,
            cta_tapped=False
        )
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30,
            completed=True,
            cta_tapped=False
        )
        
        stats = ReelViewService.get_view_stats(self.customer_user, days=30)
        
        self.assertEqual(stats['total_views'], 3)
        self.assertEqual(stats['unique_reels'], 2)
        self.assertEqual(stats['total_watch_time'], 75)  # 30+15+30
        self.assertEqual(stats['completed_views'], 2)
        self.assertEqual(stats['cta_taps'], 1)
        self.assertEqual(stats['completion_rate'], 66.67)  # 2/3 * 100
        self.assertEqual(stats['cta_tap_rate'], 33.33)  # 1/3 * 100
    
    def test_get_view_history(self):
        """Test getting view history."""
        # Create some views
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30
        )
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=15
        )
        
        history = ReelViewService.get_view_history(
            self.customer_user,
            limit=10
        )
        
        self.assertEqual(len(history), 2)
        self.assertIn('reel_id', history[0])
        self.assertIn('watched_seconds', history[0])
        self.assertIn('completed', history[0])
        self.assertIn('viewed_at', history[0])
    
    def test_cleanup_old_views(self):
        """Test cleaning up old view records."""
        # Create old view (91 days ago)
        old_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=30,
            viewed_at=timezone.now() - timedelta(days=91)
        )
        
        # Create recent view
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=15
        )
        
        # Cleanup old views
        cleaned_count = ReelViewService.cleanup_old_views(days_to_keep=90)
        
        self.assertEqual(cleaned_count, 1)
        
        # Verify old view is gone, recent view remains
        self.assertFalse(NearbyReelView.objects.filter(id=old_view.id).exists())
        self.assertEqual(NearbyReelView.objects.filter(user=self.customer_user).count(), 1)


class UserPreferencesIntegrationTest(TestCase):
    """Integration tests for user preferences services."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        self.vendor_id = uuid.uuid4()
        self.reel_id = uuid.uuid4()
        self.discount_id = uuid.uuid4()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_user_journey_integration(self):
        """Test complete user journey integration."""
        # 1. Set user preferences
        preferences_data = {
            'default_view': 'AR',
            'search_radius_m': 2000,
            'preferred_category_slugs': ['RESTAURANT'],
            'price_range': 'MID',
            'notifications_flash_deals': True,
        }
        
        UserPreferenceService.update_preferences(self.customer_user, preferences_data)
        
        # 2. Record search
        SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='pakistani restaurant',
            query_type='TEXT',
            search_lat=24.8607,
            search_lng=67.0011,
            search_radius_m=2000,
            result_count=10
        )
        
        # 3. Record interactions
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        
        InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        # 4. Create flash deal alert
        FlashDealService.create_alert(
            user_or_guest=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # 5. Record reel view
        ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30,
            completed=True,
            cta_tapped=True
        )
        
        # 6. Verify all data is recorded correctly
        preferences = UserPreferenceService.get_preferences(self.customer_user)
        self.assertEqual(preferences['default_view'], 'AR')
        self.assertEqual(preferences['search_radius_m'], 2000)
        
        search_history = SearchHistoryService.get_search_history(self.customer_user)
        self.assertEqual(len(search_history), 1)
        self.assertEqual(search_history[0]['query_text'], 'pakistani restaurant')
        
        interactions = InteractionService.get_recent_interactions(self.customer_user)
        self.assertEqual(len(interactions), 2)
        
        active_alerts = FlashDealService.get_active_alerts(self.customer_user)
        self.assertEqual(len(active_alerts), 1)
        
        view_stats = ReelViewService.get_view_stats(self.customer_user)
        self.assertEqual(view_stats['total_views'], 1)
        self.assertEqual(view_stats['completed_views'], 1)
        self.assertEqual(view_stats['cta_taps'], 1)
