"""
Working unit tests for User Preferences services.
Tests UserPreferenceService functionality with correct field types and method signatures.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

from apps.customer_auth.models import CustomerUser, GuestToken
from apps.user_preferences.models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView

User = get_user_model()


class UserPreferenceServiceWorkingTest(TestCase):
    """Working test cases for UserPreferenceService."""
    
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
        # Import service here to avoid import issues
        from apps.user_preferences.services import UserPreferenceService
        
        # Create user preferences
        UserPreference.objects.create(
            user=self.customer_user,
            default_view='MAP',
            search_radius_m=1000,
            preferred_category_slugs=['restaurant', 'cafe'],
            price_range='PREMIUM',
        )
        
        result = UserPreferenceService.get_preferences(self.customer_user)
        
        self.assertEqual(result['default_view'], 'MAP')
        self.assertEqual(result['search_radius_m'], 1000)
        self.assertEqual(result['preferred_category_slugs'], ['restaurant', 'cafe'])
        self.assertEqual(result['price_range'], 'PREMIUM')
    
    def test_get_preferences_guest_user(self):
        """Test getting preferences for guest user."""
        from apps.user_preferences.services import UserPreferenceService
        
        # Create guest preferences
        UserPreference.objects.create(
            guest_token=self.guest_token.token,
            default_view='AR',
            search_radius_m=500,
            preferred_category_slugs=['food'],
            price_range='MID',
        )
        
        result = UserPreferenceService.get_preferences(self.guest_token.token)
        
        self.assertEqual(result['default_view'], 'AR')
        self.assertEqual(result['search_radius_m'], 500)
        self.assertEqual(result['preferred_category_slugs'], ['food'])
        self.assertEqual(result['price_range'], 'MID')
    
    def test_get_preferences_default_values(self):
        """Test getting preferences with default values."""
        from apps.user_preferences.services import UserPreferenceService
        
        result = UserPreferenceService.get_preferences(self.customer_user)
        
        # Should return default values
        self.assertEqual(result['default_view'], 'AR')
        self.assertEqual(result['search_radius_m'], 500)
        self.assertEqual(result['price_range'], 'MID')
    
    def test_update_preferences_authenticated_user(self):
        """Test updating preferences for authenticated user."""
        from apps.user_preferences.services import UserPreferenceService
        
        preferences_data = {
            'default_view': 'LIST',
            'search_radius_m': 2000,
            'preferred_category_slugs': ['shopping', 'entertainment'],
            'price_range': 'BUDGET',
        }
        
        result = UserPreferenceService.update_preferences(
            self.customer_user,
            preferences_data
        )
        
        self.assertEqual(result['default_view'], 'LIST')
        self.assertEqual(result['search_radius_m'], 2000)
        self.assertEqual(result['preferred_category_slugs'], ['shopping', 'entertainment'])
        self.assertEqual(result['price_range'], 'BUDGET')
    
    def test_update_preferences_guest_user(self):
        """Test updating preferences for guest user."""
        from apps.user_preferences.services import UserPreferenceService
        
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


class SearchHistoryServiceWorkingTest(TestCase):
    """Working test cases for SearchHistoryService."""
    
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
        from apps.user_preferences.services import SearchHistoryService
        
        result = SearchHistoryService.record_search(
            user_or_guest=self.customer_user,
            query_text='pakistani restaurant',
            query_type='TEXT',
            search_lat=Decimal('24.8607'),
            search_lng=Decimal('67.0011'),
            search_radius_m=5000,
            result_count=15,
            navigated_to_vendor_id=uuid.uuid4()
        )
        
        self.assertTrue(result)
        
        # Verify search history record
        search_history = UserSearchHistory.objects.get(user=self.customer_user)
        self.assertEqual(search_history.query_text, 'pakistani restaurant')
        self.assertEqual(search_history.query_type, 'TEXT')
        self.assertEqual(search_history.search_lat, Decimal('24.8607000'))
        self.assertEqual(search_history.search_lng, Decimal('67.0011000'))
        self.assertEqual(search_history.search_radius_m, 5000)
        self.assertEqual(search_history.result_count, 15)
        self.assertIsNotNone(search_history.navigated_to_vendor_id)
    
    def test_record_search_guest_user(self):
        """Test recording search for guest user."""
        from apps.user_preferences.services import SearchHistoryService
        
        result = SearchHistoryService.record_search(
            user_or_guest=self.guest_token.token,
            query_text='cafe near me',
            query_type='VOICE',
            search_lat=Decimal('24.8607'),
            search_lng=Decimal('67.0011'),
            search_radius_m=2000,
            result_count=8
        )
        
        self.assertTrue(result)
        
        # Verify search history record
        search_history = UserSearchHistory.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(search_history.query_text, 'cafe near me')
        self.assertEqual(search_history.query_type, 'VOICE')
        self.assertEqual(search_history.result_count, 8)
    
    def test_get_search_history_authenticated_user(self):
        """Test getting search history for authenticated user."""
        from apps.user_preferences.services import SearchHistoryService
        
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
        from apps.user_preferences.services import SearchHistoryService
        
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


class InteractionServiceWorkingTest(TestCase):
    """Working test cases for InteractionService."""
    
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
        from apps.user_preferences.services import InteractionService
        
        result = InteractionService.record_interaction(
            user_or_guest=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            lat=Decimal('24.8607'),
            lng=Decimal('67.0011'),
            source='search'
        )
        
        self.assertTrue(result)
        
        # Verify interaction record
        interaction = UserVendorInteraction.objects.get(user=self.customer_user)
        self.assertEqual(str(interaction.vendor_id), str(self.vendor_id))
        self.assertEqual(interaction.interaction_type, 'VIEW')
        self.assertEqual(str(interaction.session_id), str(self.session_id))
        self.assertEqual(interaction.lat, Decimal('24.8607000'))
        self.assertEqual(interaction.lng, Decimal('67.0011000'))
        self.assertEqual(interaction.metadata['source'], 'search')
    
    def test_record_interaction_guest_user(self):
        """Test recording interaction for guest user."""
        from apps.user_preferences.services import InteractionService
        
        result = InteractionService.record_interaction(
            user_or_guest=self.guest_token.token,
            vendor_id=self.vendor_id,
            interaction_type='TAP',
            session_id=self.session_id,
            lat=Decimal('24.8607'),
            lng=Decimal('67.0011')
        )
        
        self.assertTrue(result)
        
        # Verify interaction record
        interaction = UserVendorInteraction.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(interaction.interaction_type, 'TAP')
    
    def test_record_interaction_all_types(self):
        """Test recording all interaction types."""
        from apps.user_preferences.services import InteractionService
        
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
        from apps.user_preferences.services import InteractionService
        
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


class FlashDealServiceWorkingTest(TestCase):
    """Working test cases for FlashDealService."""
    
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
        from apps.user_preferences.services import FlashDealService
        
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
        from apps.user_preferences.services import FlashDealService
        
        result = FlashDealService.create_alert(
            user_or_guest=self.guest_token.token,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertTrue(result)
        
        # Verify alert record
        alert = FlashDealAlert.objects.get(guest_token=self.guest_token.token)
        self.assertEqual(str(alert.discount_id), str(self.discount_id))
    
    def test_dismiss_alert(self):
        """Test dismissing flash deal alert."""
        from apps.user_preferences.services import FlashDealService
        
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
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        from apps.user_preferences.services import FlashDealService
        
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


class ReelViewServiceWorkingTest(TestCase):
    """Working test cases for ReelViewService."""
    
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
        from apps.user_preferences.services import ReelViewService
        
        result = ReelViewService.record_view(
            user_or_guest=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=25,
            completed=True,
            cta_tapped=True,
            lat=Decimal('24.8607'),
            lng=Decimal('67.0011')
        )
        
        self.assertTrue(result)
        
        # Verify view record
        view = NearbyReelView.objects.get(user=self.customer_user)
        self.assertEqual(str(view.reel_id), str(self.reel_id))
        self.assertEqual(str(view.vendor_id), str(self.vendor_id))
        self.assertEqual(view.watched_seconds, 25)
        self.assertTrue(view.completed)
        self.assertTrue(view.cta_tapped)
        self.assertEqual(view.lat, Decimal('24.8607000'))
        self.assertEqual(view.lng, Decimal('67.0011000'))
    
    def test_record_view_guest_user(self):
        """Test recording reel view for guest user."""
        from apps.user_preferences.services import ReelViewService
        
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
        from apps.user_preferences.services import ReelViewService
        
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
