"""
Simple unit tests for User Preferences models.
Tests core model functionality without complex service dependencies.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customer_auth.models import CustomerUser, GuestToken
from apps.user_preferences.models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView

User = get_user_model()


class UserPreferenceSimpleTest(TestCase):
    """Simple test cases for UserPreference model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_user_preference_creation(self):
        """Test user preference creation with all fields."""
        preferences = UserPreference.objects.create(
            user=self.customer_user,
            default_view='MAP',
            search_radius_m=2000,
            show_open_now_only=True,
            preferred_category_slugs=['restaurant', 'cafe', 'retail'],
            price_range='MID'
        )
        
        self.assertEqual(preferences.user, self.customer_user)
        self.assertEqual(preferences.default_view, 'MAP')
        self.assertEqual(preferences.search_radius_m, 2000)
        self.assertTrue(preferences.show_open_now_only)
        self.assertEqual(preferences.preferred_category_slugs, ['restaurant', 'cafe', 'retail'])
        self.assertEqual(preferences.price_range, 'MID')
    
    def test_user_preference_defaults(self):
        """Test user preference default values."""
        preferences = UserPreference.objects.create(
            user=self.customer_user
        )
        
        self.assertEqual(preferences.default_view, 'AR')  # Default
        self.assertEqual(preferences.search_radius_m, 500)  # Default
        self.assertFalse(preferences.show_open_now_only)  # Default False
        self.assertEqual(preferences.preferred_category_slugs, [])  # Default empty list
        self.assertEqual(preferences.price_range, 'MID')  # Default
    
    def test_user_preference_guest_creation(self):
        """Test guest preference creation."""
        preferences = UserPreference.objects.create(
            guest_token=self.guest_token.token,
            default_view='LIST',
            search_radius_m=1500,
            preferred_category_slugs=['food'],
            price_range='BUDGET'
        )
        
        self.assertEqual(preferences.guest_token, self.guest_token.token)
        self.assertIsNone(preferences.user)
        self.assertEqual(preferences.default_view, 'LIST')
        self.assertEqual(preferences.search_radius_m, 1500)
        self.assertEqual(preferences.preferred_category_slugs, ['food'])
        self.assertEqual(preferences.price_range, 'BUDGET')
    
    def test_user_preference_uniqueness(self):
        """Test that each user can only have one preference record."""
        # Create first preference
        UserPreference.objects.create(
            user=self.customer_user,
            search_radius_m=1000
        )
        
        # Try to create second preference for same user should fail
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                user=self.customer_user,
                search_radius_m=2000
            )
    
    def test_user_preference_guest_uniqueness(self):
        """Test that each guest token can only have one preference record."""
        # Create first preference
        UserPreference.objects.create(
            guest_token=self.guest_token.token,
            search_radius_m=1000
        )
        
        # Try to create second preference for same guest should fail
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                guest_token=self.guest_token.token,
                search_radius_m=2000
            )
    
    def test_get_for_user_class_method(self):
        """Test the get_for_user class method."""
        # Create preferences using class method
        prefs = UserPreference.get_for_user(self.customer_user)
        
        self.assertEqual(prefs.user, self.customer_user)
        self.assertEqual(prefs.default_view, 'AR')  # Default
        self.assertEqual(prefs.search_radius_m, 500)  # Default
        
        # Test that it returns existing preferences
        existing_prefs = UserPreference.get_for_user(self.customer_user)
        self.assertEqual(prefs.id, existing_prefs.id)
    
    def test_get_for_guest_class_method(self):
        """Test the get_for_guest class method."""
        # Create preferences using class method
        prefs = UserPreference.get_for_guest(self.guest_token.token)
        
        self.assertEqual(prefs.guest_token, self.guest_token.token)
        self.assertIsNone(prefs.user)
        self.assertEqual(prefs.default_view, 'AR')  # Default
        self.assertEqual(prefs.search_radius_m, 500)  # Default
        
        # Test that it returns existing preferences
        existing_prefs = UserPreference.get_for_guest(self.guest_token.token)
        self.assertEqual(prefs.id, existing_prefs.id)


class UserSearchHistorySimpleTest(TestCase):
    """Simple test cases for UserSearchHistory model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_search_history_creation(self):
        """Test search history creation."""
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant near me',
            query_type='TEXT',
            search_lat=Decimal('31.5204'),
            search_lng=Decimal('74.3587'),
            result_count=15
        )
        
        self.assertEqual(search.user, self.customer_user)
        self.assertEqual(search.query_text, 'restaurant near me')
        self.assertEqual(search.query_type, 'TEXT')
        self.assertEqual(search.search_lat, Decimal('31.5204'))
        self.assertEqual(search.search_lng, Decimal('74.3587'))
        self.assertEqual(search.result_count, 15)
    
    def test_search_history_guest_creation(self):
        """Test search history creation for guest."""
        search = UserSearchHistory.objects.create(
            guest_token=self.guest_token.token,
            query_text='cafe near me',
            query_type='VOICE',
            search_lat=Decimal('31.5210'),
            search_lng=Decimal('74.3590'),
            result_count=8
        )
        
        self.assertEqual(search.guest_token, self.guest_token.token)
        self.assertIsNone(search.user)
        self.assertEqual(search.query_text, 'cafe near me')
        self.assertEqual(search.query_type, 'VOICE')
        self.assertEqual(search.result_count, 8)
    
    def test_search_history_ordering(self):
        """Test that search history is ordered by searched_at DESC."""
        # Create multiple searches
        search1 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='first search',
            query_type='TEXT',
            result_count=10
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.01)
        
        search2 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='second search',
            query_type='VOICE',
            result_count=20
        )
        
        # Get all searches for user
        searches = UserSearchHistory.objects.filter(user=self.customer_user)
        
        # Should be ordered by searched_at DESC (newest first)
        self.assertEqual(searches[0], search2)
        self.assertEqual(searches[1], search1)
    
    def test_search_history_query_types(self):
        """Test different query types."""
        query_types = ['TEXT', 'VOICE', 'CATEGORY', 'LOCATION']
        
        for i, query_type in enumerate(query_types):
            search = UserSearchHistory.objects.create(
                user=self.customer_user,
                query_text=f'search {i}',
                query_type=query_type,
                result_count=i * 5
            )
            self.assertEqual(search.query_type, query_type)
    
    def test_search_history_with_optional_fields(self):
        """Test search history with optional fields."""
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            search_lat=Decimal('31.5204'),
            search_lng=Decimal('74.3587'),
            search_radius_m=2000,
            result_count=12,
            extracted_category='RESTAURANT',
            extracted_intent='FOOD',
            extracted_price_range='MID',
            navigated_to_vendor_id=uuid.uuid4()
        )
        
        self.assertEqual(search.extracted_category, 'RESTAURANT')
        self.assertEqual(search.extracted_intent, 'FOOD')
        self.assertEqual(search.extracted_price_range, 'MID')
        self.assertIsNotNone(search.navigated_to_vendor_id)


class UserVendorInteractionSimpleTest(TestCase):
    """Simple test cases for UserVendorInteraction model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_interaction_creation(self):
        """Test interaction creation."""
        interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            metadata={'source': 'search'}
        )
        
        self.assertEqual(interaction.user, self.customer_user)
        self.assertEqual(str(interaction.vendor_id), str(self.vendor_id))
        self.assertEqual(interaction.interaction_type, 'VIEW')
        self.assertEqual(str(interaction.session_id), str(self.session_id))
        self.assertEqual(interaction.lat, Decimal('31.5204'))
        self.assertEqual(interaction.lng, Decimal('74.3587'))
        self.assertEqual(interaction.metadata['source'], 'search')
    
    def test_interaction_guest_creation(self):
        """Test interaction creation for guest."""
        interaction = UserVendorInteraction.objects.create(
            guest_token=self.guest_token.token,
            vendor_id=self.vendor_id,
            interaction_type='TAP',
            session_id=self.session_id,
            lat=Decimal('31.5210'),
            lng=Decimal('74.3590')
        )
        
        self.assertEqual(interaction.guest_token, self.guest_token.token)
        self.assertIsNone(interaction.user)
        self.assertEqual(interaction.interaction_type, 'TAP')
    
    def test_interaction_types(self):
        """Test all interaction types."""
        interaction_types = [
            'VIEW', 'TAP', 'NAVIGATION', 'CALL', 'REEL_VIEW',
            'PROMOTION_TAP', 'ARRIVAL', 'SHARE', 'FAVORITE'
        ]
        
        for i, interaction_type in enumerate(interaction_types):
            interaction = UserVendorInteraction.objects.create(
                user=self.customer_user,
                vendor_id=uuid.uuid4(),
                interaction_type=interaction_type,
                session_id=uuid.uuid4()
            )
            self.assertEqual(interaction.interaction_type, interaction_type)
    
    def test_interaction_ordering(self):
        """Test that interactions are ordered by interacted_at DESC."""
        # Create multiple interactions
        interaction1 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.01)
        
        interaction2 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        # Get all interactions for user
        interactions = UserVendorInteraction.objects.filter(user=self.customer_user)
        
        # Should be ordered by interacted_at DESC (newest first)
        self.assertEqual(interactions[0], interaction2)
        self.assertEqual(interactions[1], interaction1)
    
    def test_interaction_metadata(self):
        """Test interaction metadata storage."""
        # Test with simple metadata
        interaction1 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            metadata={'source': 'search', 'page': 'discovery'}
        )
        
        self.assertEqual(interaction1.metadata['source'], 'search')
        self.assertEqual(interaction1.metadata['page'], 'discovery')
        
        # Test with complex metadata
        complex_metadata = {
            'source': 'voice',
            'query': 'restaurant near me',
            'result_position': 3,
            'filters': {
                'price_range': 'MID',
                'categories': ['restaurant', 'pakistani']
            }
        }
        
        interaction2 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='NAVIGATION',
            session_id=uuid.uuid4(),
            metadata=complex_metadata
        )
        
        self.assertEqual(interaction2.metadata['source'], 'voice')
        self.assertEqual(interaction2.metadata['query'], 'restaurant near me')
        self.assertEqual(interaction2.metadata['result_position'], 3)
        self.assertEqual(interaction2.metadata['filters']['price_range'], 'MID')
        self.assertEqual(interaction2.metadata['filters']['categories'], ['restaurant', 'pakistani'])


class FlashDealAlertSimpleTest(TestCase):
    """Simple test cases for FlashDealAlert model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_alert_creation(self):
        """Test flash deal alert creation."""
        alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertEqual(alert.user, self.customer_user)
        self.assertEqual(str(alert.discount_id), str(self.discount_id))
        self.assertEqual(str(alert.vendor_id), str(self.vendor_id))
        self.assertFalse(alert.dismissed)
        self.assertFalse(alert.tapped)
        self.assertIsNone(alert.dismissed_at)
        self.assertIsNone(alert.tapped_at)
    
    def test_alert_guest_creation(self):
        """Test flash deal alert creation for guest."""
        alert = FlashDealAlert.objects.create(
            guest_token=self.guest_token.token,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.assertEqual(alert.guest_token, self.guest_token.token)
        self.assertIsNone(alert.user)
        self.assertFalse(alert.dismissed)
        self.assertFalse(alert.tapped)
    
    def test_alert_dismissal(self):
        """Test alert dismissal."""
        alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Dismiss the alert
        alert.dismissed = True
        alert.dismissed_at = timezone.now()
        alert.save()
        
        # Verify dismissal
        updated_alert = FlashDealAlert.objects.get(id=alert.id)
        self.assertTrue(updated_alert.dismissed)
        self.assertIsNotNone(updated_alert.dismissed_at)
    
    def test_alert_tap(self):
        """Test alert tap."""
        alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Tap the alert
        alert.tapped = True
        alert.tapped_at = timezone.now()
        alert.save()
        
        # Verify tap
        updated_alert = FlashDealAlert.objects.get(id=alert.id)
        self.assertTrue(updated_alert.tapped)
        self.assertIsNotNone(updated_alert.tapped_at)
    
    def test_alert_ordering(self):
        """Test that alerts can be ordered by alerted_at DESC."""
        # Create multiple alerts
        alert1 = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=self.vendor_id
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.1)  # Increased sleep time
        
        alert2 = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=self.vendor_id
        )
        
        # Get all alerts for user explicitly ordered by alerted_at DESC
        alerts = list(FlashDealAlert.objects.filter(user=self.customer_user).order_by('-alerted_at'))
        
        # Should be ordered by alerted_at DESC (newest first)
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0].id, alert2.id)  # alert2 should be first
        self.assertEqual(alerts[1].id, alert1.id)  # alert1 should be second
        self.assertGreater(alerts[0].alerted_at, alerts[1].alerted_at)


class NearbyReelViewSimpleTest(TestCase):
    """Simple test cases for NearbyReelView model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_reel_view_creation(self):
        """Test reel view creation."""
        view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30,
            completed=True,
            cta_tapped=True,
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587')
        )
        
        self.assertEqual(view.user, self.customer_user)
        self.assertEqual(str(view.reel_id), str(self.reel_id))
        self.assertEqual(str(view.vendor_id), str(self.vendor_id))
        self.assertEqual(view.watched_seconds, 30)
        self.assertTrue(view.completed)
        self.assertTrue(view.cta_tapped)
        self.assertEqual(view.lat, Decimal('31.5204'))
        self.assertEqual(view.lng, Decimal('74.3587'))
    
    def test_reel_view_guest_creation(self):
        """Test reel view creation for guest."""
        view = NearbyReelView.objects.create(
            guest_token=self.guest_token.token,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=15,
            completed=False,
            cta_tapped=False
        )
        
        self.assertEqual(view.guest_token, self.guest_token.token)
        self.assertIsNone(view.user)
        self.assertEqual(view.watched_seconds, 15)
        self.assertFalse(view.completed)
        self.assertFalse(view.cta_tapped)
    
    def test_reel_view_ordering(self):
        """Test that reel views are ordered by viewed_at DESC."""
        # Create multiple views
        view1 = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=30
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.01)
        
        view2 = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=45
        )
        
        # Get all views for user
        views = NearbyReelView.objects.filter(user=self.customer_user)
        
        # Should be ordered by viewed_at DESC (newest first)
        self.assertEqual(views[0], view2)
        self.assertEqual(views[1], view1)
    
    def test_reel_view_basic_functionality(self):
        """Test basic reel view functionality without class methods."""
        # Test with user
        view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=25,
            completed=True,
            cta_tapped=False
        )
        
        self.assertEqual(view.user, self.customer_user)
        self.assertEqual(str(view.reel_id), str(self.reel_id))
        self.assertEqual(view.watched_seconds, 25)
        self.assertTrue(view.completed)
        self.assertFalse(view.cta_tapped)
        
        # Test with guest
        guest_view = NearbyReelView.objects.create(
            guest_token=self.guest_token.token,
            reel_id=uuid.uuid4(),
            vendor_id=self.vendor_id,
            watched_seconds=10,
            completed=False,
            cta_tapped=False
        )
        
        self.assertEqual(guest_view.guest_token, self.guest_token.token)
        self.assertIsNone(guest_view.user)
        self.assertEqual(guest_view.watched_seconds, 10)
        self.assertFalse(guest_view.completed)
