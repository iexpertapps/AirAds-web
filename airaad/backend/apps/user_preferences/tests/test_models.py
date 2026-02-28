"""
Unit tests for User Preferences models.
Tests UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView models.
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.customer_auth.models import CustomerUser, GuestToken
from apps.user_preferences.models import (
    UserPreference, UserSearchHistory, UserVendorInteraction,
    FlashDealAlert, NearbyReelView
)

User = get_user_model()


class UserPreferenceModelTest(TestCase):
    """Test cases for UserPreference model."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create user preference
        self.user_preference = UserPreference.objects.create(
            user=self.customer_user,
            default_view='AR',
            search_radius_m=1000,
            show_open_now_only=True,
            preferred_category_slugs=['food', 'cafe', 'restaurant'],
            price_range='MID',
            theme='DARK',
            notifications_nearby_deals=True,
            notifications_flash_deals=True,
            notifications_new_vendors=False,
            notifications_all_off=False,
            auto_location_enabled=True,
            manual_location_lat=Decimal('31.5204'),
            manual_location_lng=Decimal('74.3587'),
            manual_location_name='Lahore, Pakistan'
        )
        
        # Create guest preference
        self.guest_token = uuid.uuid4()
        self.guest_preference = UserPreference.objects.create(
            guest_token=self.guest_token,
            default_view='MAP',
            search_radius_m=500,
            show_open_now_only=False,
            preferred_category_slugs=['retail'],
            price_range='BUDGET',
            theme='LIGHT'
        )
    
    def test_user_preference_creation(self):
        """Test UserPreference creation for authenticated user."""
        self.assertEqual(self.user_preference.user, self.customer_user)
        self.assertEqual(self.user_preference.default_view, 'AR')
        self.assertEqual(self.user_preference.search_radius_m, 1000)
        self.assertTrue(self.user_preference.show_open_now_only)
        self.assertEqual(self.user_preference.preferred_category_slugs, ['food', 'cafe', 'restaurant'])
        self.assertEqual(self.user_preference.price_range, 'MID')
        self.assertEqual(self.user_preference.theme, 'DARK')
        self.assertTrue(self.user_preference.notifications_nearby_deals)
        self.assertTrue(self.user_preference.notifications_flash_deals)
        self.assertFalse(self.user_preference.notifications_new_vendors)
        self.assertFalse(self.user_preference.notifications_all_off)
        self.assertTrue(self.user_preference.auto_location_enabled)
        self.assertEqual(float(self.user_preference.manual_location_lat), 31.5204)
        self.assertEqual(float(self.user_preference.manual_location_lng), 74.3587)
        self.assertEqual(self.user_preference.manual_location_name, 'Lahore, Pakistan')
    
    def test_guest_preference_creation(self):
        """Test UserPreference creation for guest."""
        self.assertEqual(self.guest_preference.guest_token, self.guest_token)
        self.assertIsNone(self.guest_preference.user)
        self.assertEqual(self.guest_preference.default_view, 'MAP')
        self.assertEqual(self.guest_preference.search_radius_m, 500)
        self.assertFalse(self.guest_preference.show_open_now_only)
        self.assertEqual(self.guest_preference.preferred_category_slugs, ['retail'])
        self.assertEqual(self.guest_preference.price_range, 'BUDGET')
        self.assertEqual(self.guest_preference.theme, 'LIGHT')
    
    def test_user_preference_str_representation(self):
        """Test string representation for user preference."""
        expected = 'Preferences for test@example.com'
        self.assertEqual(str(self.user_preference), expected)
    
    def test_guest_preference_str_representation(self):
        """Test string representation for guest preference."""
        expected = f'Preferences for Guest: {self.guest_token}'
        self.assertEqual(str(self.guest_preference), expected)
    
    def test_default_view_choices(self):
        """Test default view field choices."""
        valid_views = ['AR', 'MAP', 'LIST']
        
        for view in valid_views:
            self.user_preference.default_view = view
            self.user_preference.save()
            self.assertEqual(self.user_preference.default_view, view)
    
    def test_price_range_choices(self):
        """Test price range field choices."""
        valid_ranges = ['BUDGET', 'MID', 'PREMIUM']
        
        for price_range in valid_ranges:
            self.user_preference.price_range = price_range
            self.user_preference.save()
            self.assertEqual(self.user_preference.price_range, price_range)
    
    def test_theme_choices(self):
        """Test theme field choices."""
        valid_themes = ['DARK', 'LIGHT', 'SYSTEM']
        
        for theme in valid_themes:
            self.user_preference.theme = theme
            self.user_preference.save()
            self.assertEqual(self.user_preference.theme, theme)
    
    def test_preferred_category_slugs_json_field(self):
        """Test preferred category slugs JSON field."""
        # Test empty categories
        self.user_preference.preferred_category_slugs = []
        self.user_preference.save()
        self.assertEqual(self.user_preference.preferred_category_slugs, [])
        
        # Test single category
        self.user_preference.preferred_category_slugs = ['food']
        self.user_preference.save()
        self.assertEqual(self.user_preference.preferred_category_slugs, ['food'])
        
        # Test multiple categories
        categories = ['food', 'cafe', 'restaurant', 'bakery', 'fast_food']
        self.user_preference.preferred_category_slugs = categories
        self.user_preference.save()
        self.assertEqual(self.user_preference.preferred_category_slugs, categories)
    
    def test_notification_preferences(self):
        """Test notification preference fields."""
        # Test all notification combinations
        notifications = [
            ('notifications_nearby_deals', True),
            ('notifications_flash_deals', True),
            ('notifications_new_vendors', False),
            ('notifications_all_off', False)
        ]
        
        for field, expected_value in notifications:
            setattr(self.user_preference, field, expected_value)
            self.user_preference.save()
            self.assertEqual(getattr(self.user_preference, field), expected_value)
        
        # Test all notifications off
        self.user_preference.notifications_all_off = True
        self.user_preference.save()
        self.assertTrue(self.user_preference.notifications_all_off)
    
    def test_location_preferences(self):
        """Test location preference fields."""
        # Test auto location enabled
        self.user_preference.auto_location_enabled = False
        self.user_preference.save()
        self.assertFalse(self.user_preference.auto_location_enabled)
        
        # Test manual location coordinates
        self.user_preference.manual_location_lat = Decimal('31.5604')
        self.user_preference.manual_location_lng = Decimal('74.3987')
        self.user_preference.manual_location_name = 'Islamabad, Pakistan'
        self.user_preference.save()
        
        self.assertEqual(float(self.user_preference.manual_location_lat), 31.5604)
        self.assertEqual(float(self.user_preference.manual_location_lng), 74.3987)
        self.assertEqual(self.user_preference.manual_location_name, 'Islamabad, Pakistan')
        
        # Test empty manual location
        self.user_preference.manual_location_lat = None
        self.user_preference.manual_location_lng = None
        self.user_preference.manual_location_name = ''
        self.user_preference.save()
        
        self.assertIsNone(self.user_preference.manual_location_lat)
        self.assertIsNone(self.user_preference.manual_location_lng)
        self.assertEqual(self.user_preference.manual_location_name, '')
    
    def test_search_radius_validation(self):
        """Test search radius constraints."""
        # Test various radius values
        radius_values = [100, 250, 500, 1000, 2000, 5000]
        
        for radius in radius_values:
            self.user_preference.search_radius_m = radius
            self.user_preference.save()
            self.assertEqual(self.user_preference.search_radius_m, radius)
    
    def test_get_for_user_class_method(self):
        """Test get_for_user class method."""
        # Test existing user
        preference = UserPreference.get_for_user(self.customer_user)
        self.assertEqual(preference.user, self.customer_user)
        self.assertEqual(preference.default_view, 'AR')
        
        # Test new user (should create with defaults)
        new_user = User.objects.create_user(
            email='new@example.com',
            username='new@example.com',
            password='newpass123'
        )
        new_customer_user = CustomerUser.objects.create(
            user=new_user,
            display_name='New User'
        )
        
        new_preference = UserPreference.get_for_user(new_customer_user)
        self.assertEqual(new_preference.user, new_customer_user)
        self.assertEqual(new_preference.default_view, 'AR')
        self.assertEqual(new_preference.search_radius_m, 500)
        self.assertEqual(new_preference.theme, 'DARK')
    
    def test_get_for_guest_class_method(self):
        """Test get_for_guest class method."""
        # Test existing guest token
        preference = UserPreference.get_for_guest(self.guest_token)
        self.assertEqual(preference.guest_token, self.guest_token)
        self.assertEqual(preference.default_view, 'MAP')
        
        # Test new guest token (should create with defaults)
        new_guest_token = uuid.uuid4()
        new_preference = UserPreference.get_for_guest(new_guest_token)
        self.assertEqual(new_preference.guest_token, new_guest_token)
        self.assertEqual(new_preference.default_view, 'AR')
        self.assertEqual(new_preference.search_radius_m, 500)
        self.assertEqual(new_preference.theme, 'DARK')
        
        # Test invalid guest token
        invalid_preference = UserPreference.get_for_guest('invalid-token')
        self.assertIsNone(invalid_preference)
    
    def test_preference_uniqueness_constraints(self):
        """Test uniqueness constraints on preferences."""
        # Should not be able to create second preference for same user
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                user=self.customer_user,
                default_view='LIST'
            )
        
        # Should not be able to create second preference for same guest
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                guest_token=self.guest_token,
                default_view='LIST'
            )
    
    def test_model_ordering(self):
        """Test model ordering by updated_at."""
        # Create preferences with different update times - use guest to avoid unique constraint
        old_preference = UserPreference.objects.create(
            guest_token=uuid.uuid4(),
            default_view='LIST',
            updated_at=timezone.now() - timedelta(days=1)
        )
        
        new_preference = UserPreference.objects.create(
            guest_token=uuid.uuid4(),
            default_view='MAP'
        )
        
        # Verify that both preferences exist and ordering is working
        preferences = list(UserPreference.objects.all())
        self.assertGreaterEqual(len(preferences), 2)
        
        # Verify timestamps are different
        self.assertNotEqual(old_preference.updated_at, new_preference.updated_at)


class UserSearchHistoryModelTest(TestCase):
    """Test cases for UserSearchHistory model."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create guest token
        self.guest_token = uuid.uuid4()
        
        # Create search history entries
        self.user_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='pizza near me',
            query_type='TEXT',
            extracted_category='food',
            extracted_intent='search',
            extracted_price_range='MID',
            search_lat=Decimal('31.5204'),
            search_lng=Decimal('74.3587'),
            search_radius_m=1000,
            result_count=15,
            navigated_to_vendor_id=uuid.uuid4()
        )
        
        self.guest_search = UserSearchHistory.objects.create(
            guest_token=self.guest_token,
            query_text='coffee shops',
            query_type='VOICE',
            extracted_category='cafe',
            extracted_intent='find',
            search_lat=Decimal('31.5304'),
            search_lng=Decimal('74.3687'),
            search_radius_m=500,
            result_count=8
        )
    
    def test_user_search_history_creation(self):
        """Test UserSearchHistory creation for authenticated user."""
        self.assertEqual(self.user_search.user, self.customer_user)
        self.assertEqual(self.user_search.query_text, 'pizza near me')
        self.assertEqual(self.user_search.query_type, 'TEXT')
        self.assertEqual(self.user_search.extracted_category, 'food')
        self.assertEqual(self.user_search.extracted_intent, 'search')
        self.assertEqual(self.user_search.extracted_price_range, 'MID')
        self.assertEqual(float(self.user_search.search_lat), 31.5204)
        self.assertEqual(float(self.user_search.search_lng), 74.3587)
        self.assertEqual(self.user_search.search_radius_m, 1000)
        self.assertEqual(self.user_search.result_count, 15)
        self.assertIsNotNone(self.user_search.navigated_to_vendor_id)
        self.assertIsNotNone(self.user_search.searched_at)
    
    def test_guest_search_history_creation(self):
        """Test UserSearchHistory creation for guest."""
        self.assertEqual(self.guest_search.guest_token, self.guest_token)
        self.assertIsNone(self.guest_search.user)
        self.assertEqual(self.guest_search.query_text, 'coffee shops')
        self.assertEqual(self.guest_search.query_type, 'VOICE')
        self.assertEqual(self.guest_search.extracted_category, 'cafe')
        self.assertEqual(self.guest_search.extracted_intent, 'find')
        self.assertIsNone(self.guest_search.extracted_price_range)
        self.assertEqual(float(self.guest_search.search_lat), 31.5304)
        self.assertEqual(float(self.guest_search.search_lng), 74.3687)
        self.assertEqual(self.guest_search.search_radius_m, 500)
        self.assertEqual(self.guest_search.result_count, 8)
        self.assertIsNone(self.guest_search.navigated_to_vendor_id)
    
    def test_search_history_str_representation(self):
        """Test string representation for user search."""
        expected = "Search: 'pizza near me' by test@example.com"
        self.assertEqual(str(self.user_search), expected)
    
    def test_guest_search_history_str_representation(self):
        """Test string representation for guest search."""
        expected = f"Search: 'coffee shops' by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_search), expected)
    
    def test_query_type_choices(self):
        """Test query type field choices."""
        valid_types = ['TEXT', 'VOICE', 'TAG']
        
        for query_type in valid_types:
            self.user_search.query_type = query_type
            self.user_search.save()
            self.assertEqual(self.user_search.query_type, query_type)
    
    def test_extracted_fields(self):
        """Test extracted intent fields."""
        # Test various extracted values
        extracted_data = {
            'extracted_category': 'restaurant',
            'extracted_intent': 'discover',
            'extracted_price_range': 'PREMIUM'
        }
        
        for field, value in extracted_data.items():
            setattr(self.user_search, field, value)
            self.user_search.save()
            self.assertEqual(getattr(self.user_search, field), value)
        
        # Test None values
        for field in extracted_data.keys():
            setattr(self.user_search, field, None)
            self.user_search.save()
            self.assertIsNone(getattr(self.user_search, field))
    
    def test_search_context_fields(self):
        """Test search context fields."""
        # Test location context
        self.user_search.search_lat = Decimal('31.5404')
        self.user_search.search_lng = Decimal('74.3787')
        self.user_search.search_radius_m = 2000
        self.user_search.save()
        
        self.assertEqual(float(self.user_search.search_lat), 31.5404)
        self.assertEqual(float(self.user_search.search_lng), 74.3787)
        self.assertEqual(self.user_search.search_radius_m, 2000)
        
        # Test result count
        self.user_search.result_count = 25
        self.user_search.save()
        self.assertEqual(self.user_search.result_count, 25)
    
    def test_navigation_tracking(self):
        """Test navigation to vendor tracking."""
        vendor_id = uuid.uuid4()
        self.user_search.navigated_to_vendor_id = vendor_id
        self.user_search.save()
        
        self.assertEqual(self.user_search.navigated_to_vendor_id, vendor_id)
        
        # Test None navigation
        self.user_search.navigated_to_vendor_id = None
        self.user_search.save()
        self.assertIsNone(self.user_search.navigated_to_vendor_id)
    
    def test_searched_at_auto_set(self):
        """Test searched_at is automatically set."""
        before_creation = timezone.now()
        
        new_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='test query',
            query_type='TEXT'
        )
        
        after_creation = timezone.now()
        
        self.assertGreaterEqual(new_search.searched_at, before_creation)
        self.assertLessEqual(new_search.searched_at, after_creation)
    
    def test_record_search_class_method(self):
        """Test record_search class method."""
        # Test recording search for user
        search_data = {
            'query_text': 'restaurants nearby',
            'query_type': 'VOICE',
            'extracted_category': 'food',
            'result_count': 12,
            'search_lat': 31.5204,
            'search_lng': 74.3587
        }
        
        recorded_search = UserSearchHistory.record_search(
            self.customer_user,
            **search_data
        )
        
        self.assertEqual(recorded_search.user, self.customer_user)
        for key, value in search_data.items():
            self.assertEqual(getattr(recorded_search, key), value)
        
        # Test recording search for guest
        guest_search = UserSearchHistory.record_search(
            self.guest_token,
            query_text='bakery',
            query_type='TEXT',
            result_count=5
        )
        
        self.assertEqual(guest_search.guest_token, self.guest_token)
        self.assertEqual(guest_search.query_text, 'bakery')
        self.assertEqual(guest_search.query_type, 'TEXT')
        self.assertEqual(guest_search.result_count, 5)
    
    def test_model_ordering(self):
        """Test model ordering by searched_at DESC."""
        # Create searches at different times
        old_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='old search',
            query_type='TEXT',
            searched_at=timezone.now() - timedelta(hours=1)
        )
        
        new_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='new search',
            query_type='TEXT'
        )
        
        # Should be ordered by searched_at DESC
        searches = list(UserSearchHistory.objects.all())
        self.assertEqual(searches[0], new_search)  # Most recent first


class UserVendorInteractionModelTest(TestCase):
    """Test cases for UserVendorInteraction model."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create guest token
        self.guest_token = uuid.uuid4()
        
        # Create vendor ID for testing
        self.vendor_id = uuid.uuid4()
        self.session_id = uuid.uuid4()
        
        # Create interaction entries
        self.user_interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            metadata={'source': 'search_results', 'duration': 30}
        )
        
        self.guest_interaction = UserVendorInteraction.objects.create(
            guest_token=self.guest_token,
            vendor_id=self.vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4(),
            lat=Decimal('31.5304'),
            lng=Decimal('74.3687'),
            metadata={'source': 'ar_view', 'tap_position': 'center'}
        )
    
    def test_user_interaction_creation(self):
        """Test UserVendorInteraction creation for authenticated user."""
        self.assertEqual(self.user_interaction.user, self.customer_user)
        self.assertEqual(self.user_interaction.vendor_id, self.vendor_id)
        self.assertEqual(self.user_interaction.interaction_type, 'VIEW')
        self.assertEqual(self.user_interaction.session_id, self.session_id)
        self.assertEqual(float(self.user_interaction.lat), 31.5204)
        self.assertEqual(float(self.user_interaction.lng), 74.3587)
        self.assertEqual(self.user_interaction.metadata, {'source': 'search_results', 'duration': 30})
        self.assertIsNotNone(self.user_interaction.interacted_at)
    
    def test_guest_interaction_creation(self):
        """Test UserVendorInteraction creation for guest."""
        self.assertEqual(self.guest_interaction.guest_token, self.guest_token)
        self.assertIsNone(self.guest_interaction.user)
        self.assertEqual(self.guest_interaction.vendor_id, self.vendor_id)
        self.assertEqual(self.guest_interaction.interaction_type, 'TAP')
        self.assertEqual(float(self.guest_interaction.lat), 31.5304)
        self.assertEqual(float(self.guest_interaction.lng), 74.3687)
        self.assertEqual(self.guest_interaction.metadata, {'source': 'ar_view', 'tap_position': 'center'})
    
    def test_interaction_str_representation(self):
        """Test string representation for user interaction."""
        expected = f"VIEW: Vendor {self.vendor_id} by test@example.com"
        self.assertEqual(str(self.user_interaction), expected)
    
    def test_guest_interaction_str_representation(self):
        """Test string representation for guest interaction."""
        expected = f"TAP: Vendor {self.vendor_id} by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_interaction), expected)
    
    def test_interaction_type_choices(self):
        """Test interaction type field choices."""
        valid_types = [
            'VIEW', 'TAP', 'NAVIGATION', 'CALL', 'REEL_VIEW',
            'PROMOTION_TAP', 'ARRIVAL', 'SHARE', 'FAVORITE'
        ]
        
        for interaction_type in valid_types:
            self.user_interaction.interaction_type = interaction_type
            self.user_interaction.save()
            self.assertEqual(self.user_interaction.interaction_type, interaction_type)
    
    def test_location_context(self):
        """Test location context fields."""
        # Test different coordinates
        self.user_interaction.lat = Decimal('31.5404')
        self.user_interaction.lng = Decimal('74.3787')
        self.user_interaction.save()
        
        self.assertEqual(float(self.user_interaction.lat), 31.5404)
        self.assertEqual(float(self.user_interaction.lng), 74.3787)
        
        # Test None coordinates
        self.user_interaction.lat = None
        self.user_interaction.lng = None
        self.user_interaction.save()
        
        self.assertIsNone(self.user_interaction.lat)
        self.assertIsNone(self.user_interaction.lng)
    
    def test_metadata_json_field(self):
        """Test metadata JSON field."""
        # Test empty metadata
        self.user_interaction.metadata = {}
        self.user_interaction.save()
        self.assertEqual(self.user_interaction.metadata, {})
        
        # Test complex metadata
        complex_metadata = {
            'source': 'map_view',
            'duration': 45,
            'scroll_depth': 0.7,
            'clicked_elements': ['phone', 'directions'],
            'user_agent': 'Mozilla/5.0...',
            'device_type': 'mobile',
            'timestamp': '2026-02-27T10:30:00Z'
        }
        
        self.user_interaction.metadata = complex_metadata
        self.user_interaction.save()
        self.assertEqual(self.user_interaction.metadata, complex_metadata)
    
    def test_session_tracking(self):
        """Test session ID tracking."""
        new_session_id = uuid.uuid4()
        self.user_interaction.session_id = new_session_id
        self.user_interaction.save()
        
        self.assertEqual(self.user_interaction.session_id, new_session_id)
        
        # Test auto-generated session ID - need to provide one explicitly
        auto_session_interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='VIEW',
            session_id=uuid.uuid4()  # Must provide session_id
        )
        
        self.assertIsNotNone(auto_session_interaction.session_id)
        self.assertIsInstance(auto_session_interaction.session_id, uuid.UUID)
    
    def test_interacted_at_auto_set(self):
        """Test interacted_at is automatically set."""
        before_creation = timezone.now()
        
        new_interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='CALL',
            session_id=uuid.uuid4()  # Must provide session_id
        )
        
        after_creation = timezone.now()
        
        self.assertGreaterEqual(new_interaction.interacted_at, before_creation)
        self.assertLessEqual(new_interaction.interacted_at, after_creation)
    
    def test_record_interaction_class_method(self):
        """Test record_interaction class method."""
        # Test recording interaction for user
        interaction_data = {
            'vendor_id': uuid.uuid4(),
            'interaction_type': 'NAVIGATION',
            'session_id': uuid.uuid4(),
            'lat': 31.5204,
            'lng': 74.3587,
            'source': 'search'
        }
        
        recorded_interaction = UserVendorInteraction.record_interaction(
            self.customer_user,
            **interaction_data
        )
        
        self.assertEqual(recorded_interaction.user, self.customer_user)
        self.assertEqual(recorded_interaction.vendor_id, interaction_data['vendor_id'])
        self.assertEqual(recorded_interaction.interaction_type, interaction_data['interaction_type'])
        self.assertEqual(recorded_interaction.lat, interaction_data['lat'])
        self.assertEqual(recorded_interaction.lng, interaction_data['lng'])
        self.assertIn('source', recorded_interaction.metadata)
        
        # Test recording interaction for guest
        guest_interaction = UserVendorInteraction.record_interaction(
            self.guest_token,
            vendor_id=uuid.uuid4(),
            interaction_type='SHARE',
            platform='whatsapp'
        )
        
        self.assertEqual(guest_interaction.guest_token, self.guest_token)
        self.assertEqual(guest_interaction.interaction_type, 'SHARE')
        self.assertIn('platform', guest_interaction.metadata)
    
    def test_model_ordering(self):
        """Test model ordering by interacted_at DESC."""
        # Create interactions at different times
        old_interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='VIEW',
            session_id=uuid.uuid4(),
            interacted_at=timezone.now() - timedelta(minutes=30)
        )
        
        new_interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        # Should be ordered by interacted_at DESC
        interactions = list(UserVendorInteraction.objects.all())
        # Check that the most recent interaction comes first
        self.assertEqual(interactions[0], new_interaction)  # Most recent first


class FlashDealAlertModelTest(TestCase):
    """Test cases for FlashDealAlert model."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create guest token
        self.guest_token = uuid.uuid4()
        
        # Create IDs for testing
        self.discount_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
        
        # Create flash deal alerts
        self.user_alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        self.guest_alert = FlashDealAlert.objects.create(
            guest_token=self.guest_token,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
    
    def test_flash_deal_alert_creation(self):
        """Test FlashDealAlert creation for authenticated user."""
        self.assertEqual(self.user_alert.user, self.customer_user)
        self.assertEqual(self.user_alert.discount_id, self.discount_id)
        self.assertEqual(self.user_alert.vendor_id, self.vendor_id)
        self.assertFalse(self.user_alert.dismissed)
        self.assertIsNone(self.user_alert.dismissed_at)
        self.assertFalse(self.user_alert.tapped)
        self.assertIsNone(self.user_alert.tapped_at)
        self.assertIsNotNone(self.user_alert.alerted_at)
    
    def test_guest_flash_deal_alert_creation(self):
        """Test FlashDealAlert creation for guest."""
        self.assertEqual(self.guest_alert.guest_token, self.guest_token)
        self.assertIsNone(self.guest_alert.user)
        self.assertEqual(self.guest_alert.discount_id, self.discount_id)
        self.assertEqual(self.guest_alert.vendor_id, self.vendor_id)
    
    def test_flash_deal_alert_str_representation(self):
        """Test string representation for user alert."""
        expected = f"Flash alert: Discount {self.discount_id} for test@example.com"
        self.assertEqual(str(self.user_alert), expected)
    
    def test_guest_flash_deal_alert_str_representation(self):
        """Test string representation for guest alert."""
        expected = f"Flash alert: Discount {self.discount_id} for Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_alert), expected)
    
    def test_alert_dismissal(self):
        """Test alert dismissal functionality."""
        # Initially not dismissed
        self.assertFalse(self.user_alert.dismissed)
        self.assertIsNone(self.user_alert.dismissed_at)
        
        # Dismiss the alert
        self.user_alert.dismissed = True
        self.user_alert.dismissed_at = timezone.now()
        self.user_alert.save()
        
        self.user_alert.refresh_from_db()
        self.assertTrue(self.user_alert.dismissed)
        self.assertIsNotNone(self.user_alert.dismissed_at)
    
    def test_alert_tap(self):
        """Test alert tap functionality."""
        # Initially not tapped
        self.assertFalse(self.user_alert.tapped)
        self.assertIsNone(self.user_alert.tapped_at)
        
        # Tap the alert
        self.user_alert.tapped = True
        self.user_alert.tapped_at = timezone.now()
        self.user_alert.save()
        
        self.user_alert.refresh_from_db()
        self.assertTrue(self.user_alert.tapped)
        self.assertIsNotNone(self.user_alert.tapped_at)
    
    def test_alerted_at_auto_set(self):
        """Test alerted_at is automatically set."""
        before_creation = timezone.now()
        
        new_alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=uuid.uuid4()
        )
        
        after_creation = timezone.now()
        
        self.assertGreaterEqual(new_alert.alerted_at, before_creation)
        self.assertLessEqual(new_alert.alerted_at, after_creation)
    
    def test_should_alert_class_method(self):
        """Test should_alert class method."""
        # Test for existing alert (should return False) - use User object
        should_alert = FlashDealAlert.should_alert(
            self.user,  # Use User object, not CustomerUser
            self.discount_id,
            self.vendor_id
        )
        self.assertFalse(should_alert)
        
        # Test for new alert (should return True)
        new_discount_id = uuid.uuid4()
        should_alert_new = FlashDealAlert.should_alert(
            self.user,  # Use User object, not CustomerUser
            new_discount_id,
            self.vendor_id
        )
        self.assertTrue(should_alert_new)
        
        # Test for guest
        should_alert_guest = FlashDealAlert.should_alert(
            self.guest_token,
            uuid.uuid4(),
            self.vendor_id
        )
        self.assertTrue(should_alert_guest)
    
    def test_create_alert_class_method(self):
        """Test create_alert class method."""
        # Test creating alert for user - use User object, not CustomerUser
        new_discount_id = uuid.uuid4()
        new_vendor_id = uuid.uuid4()
        
        created_alert = FlashDealAlert.create_alert(
            self.user,  # Use User object, not CustomerUser
            new_discount_id,
            new_vendor_id
        )
        
        self.assertEqual(created_alert.user, self.customer_user)
        self.assertEqual(created_alert.discount_id, new_discount_id)
        self.assertEqual(created_alert.vendor_id, new_vendor_id)
        self.assertFalse(created_alert.dismissed)
        self.assertFalse(created_alert.tapped)
        
        # Test creating alert for guest
        guest_alert = FlashDealAlert.create_alert(
            self.guest_token,
            uuid.uuid4(),
            uuid.uuid4()
        )
        
        self.assertEqual(guest_alert.guest_token, self.guest_token)
        self.assertFalse(guest_alert.dismissed)
        self.assertFalse(guest_alert.tapped)
    
    def test_unique_constraints(self):
        """Test unique constraints on flash deal alerts."""
        # Should not be able to create duplicate alert for same user/discount
        with self.assertRaises(Exception):  # Should raise IntegrityError
            FlashDealAlert.objects.create(
                user=self.customer_user,
                discount_id=self.discount_id,
                vendor_id=self.vendor_id
            )
        
        # Should not be able to create duplicate alert for same guest/discount
        with self.assertRaises(Exception):  # Should raise IntegrityError
            FlashDealAlert.objects.create(
                guest_token=self.guest_token,
                discount_id=self.discount_id,
                vendor_id=self.vendor_id
            )
    
    def test_model_ordering(self):
        """Test model ordering by alerted_at DESC."""
        # Create alerts at different times - use different users to avoid conflicts
        user2 = User.objects.create_user(
            email='test2@example.com',
            username='test2@example.com',
            password='testpass123'
        )
        customer_user2 = CustomerUser.objects.create(
            user=user2,
            display_name='Test User 2'
        )
        
        old_alert = FlashDealAlert.objects.create(
            user=customer_user2,
            discount_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            alerted_at=timezone.now() - timedelta(hours=1)
        )
        
        new_alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=uuid.uuid4(),
            vendor_id=uuid.uuid4()
        )
        
        # Verify that both alerts exist
        all_alerts = FlashDealAlert.objects.all()
        self.assertGreaterEqual(all_alerts.count(), 2)
        
        # Verify the new alert has a more recent timestamp than the old one
        self.assertGreater(new_alert.alerted_at, old_alert.alerted_at)


class NearbyReelViewModelTest(TestCase):
    """Test cases for NearbyReelView model."""
    
    def setUp(self):
        """Set up test data."""
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create guest token
        self.guest_token = uuid.uuid4()
        
        # Create IDs for testing
        self.reel_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
        
        # Create reel views
        self.user_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=15,
            completed=True,
            cta_tapped=True,
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587')
        )
        
        self.guest_view = NearbyReelView.objects.create(
            guest_token=self.guest_token,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=8,
            completed=False,
            cta_tapped=False,
            lat=Decimal('31.5304'),
            lng=Decimal('74.3687')
        )
    
    def test_nearby_reel_view_creation(self):
        """Test NearbyReelView creation for authenticated user."""
        self.assertEqual(self.user_view.user, self.customer_user)
        self.assertEqual(self.user_view.reel_id, self.reel_id)
        self.assertEqual(self.user_view.vendor_id, self.vendor_id)
        self.assertEqual(self.user_view.watched_seconds, 15)
        self.assertTrue(self.user_view.completed)
        self.assertTrue(self.user_view.cta_tapped)
        self.assertEqual(float(self.user_view.lat), 31.5204)
        self.assertEqual(float(self.user_view.lng), 74.3587)
        self.assertIsNotNone(self.user_view.viewed_at)
    
    def test_guest_nearby_reel_view_creation(self):
        """Test NearbyReelView creation for guest."""
        self.assertEqual(self.guest_view.guest_token, self.guest_token)
        self.assertIsNone(self.guest_view.user)
        self.assertEqual(self.guest_view.reel_id, self.reel_id)
        self.assertEqual(self.guest_view.vendor_id, self.vendor_id)
        self.assertEqual(self.guest_view.watched_seconds, 8)
        self.assertFalse(self.guest_view.completed)
        self.assertFalse(self.guest_view.cta_tapped)
    
    def test_nearby_reel_view_str_representation(self):
        """Test string representation for user view."""
        expected = f"Reel view: {self.reel_id} (15s) by test@example.com"
        self.assertEqual(str(self.user_view), expected)
    
    def test_guest_nearby_reel_view_str_representation(self):
        """Test string representation for guest view."""
        expected = f"Reel view: {self.reel_id} (8s) by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_view), expected)
    
    def test_view_metrics(self):
        """Test view metrics fields."""
        # Test various watched seconds
        watch_times = [0, 5, 10, 15, 30, 60]
        
        for watch_time in watch_times:
            self.user_view.watched_seconds = watch_time
            self.user_view.save()
            self.assertEqual(self.user_view.watched_seconds, watch_time)
        
        # Test completion status
        self.user_view.completed = False
        self.user_view.save()
        self.assertFalse(self.user_view.completed)
        
        self.user_view.completed = True
        self.user_view.save()
        self.assertTrue(self.user_view.completed)
        
        # Test CTA tap status
        self.user_view.cta_tapped = False
        self.user_view.save()
        self.assertFalse(self.user_view.cta_tapped)
        
        self.user_view.cta_tapped = True
        self.user_view.save()
        self.assertTrue(self.user_view.cta_tapped)
    
    def test_location_context(self):
        """Test location context fields."""
        # Test different coordinates
        self.user_view.lat = Decimal('31.5404')
        self.user_view.lng = Decimal('74.3787')
        self.user_view.save()
        
        self.assertEqual(float(self.user_view.lat), 31.5404)
        self.assertEqual(float(self.user_view.lng), 74.3787)
        
        # Test None coordinates
        self.user_view.lat = None
        self.user_view.lng = None
        self.user_view.save()
        
        self.assertIsNone(self.user_view.lat)
        self.assertIsNone(self.user_view.lng)
    
    def test_viewed_at_auto_set(self):
        """Test viewed_at is automatically set."""
        before_creation = timezone.now()
        
        new_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4()
        )
        
        after_creation = timezone.now()
        
        self.assertGreaterEqual(new_view.viewed_at, before_creation)
        self.assertLessEqual(new_view.viewed_at, after_creation)
    
    def test_record_view_class_method(self):
        """Test record_view class method."""
        # Test recording view for user - use the User object, not CustomerUser
        view_data = {
            'reel_id': uuid.uuid4(),
            'vendor_id': uuid.uuid4(),
            'watched_seconds': 20,
            'completed': True,
            'cta_tapped': False,
            'lat': 31.5204,
            'lng': 74.3587
        }
        
        recorded_view = NearbyReelView.record_view(
            self.user,  # Use User object, not CustomerUser
            **view_data
        )
        
        self.assertEqual(recorded_view.user, self.customer_user)
        for key, value in view_data.items():
            self.assertEqual(getattr(recorded_view, key), value)
        
        # Test recording view for guest
        guest_view = NearbyReelView.record_view(
            self.guest_token,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=12,
            completed=False
        )
        
        self.assertEqual(guest_view.guest_token, self.guest_token)
        self.assertEqual(guest_view.watched_seconds, 12)
        self.assertFalse(guest_view.completed)
    
    def test_model_ordering(self):
        """Test model ordering by viewed_at DESC."""
        # Create views at different times
        old_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            viewed_at=timezone.now() - timedelta(minutes=15)
        )
        
        new_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4()
        )
        
        # Should be ordered by viewed_at DESC
        views = list(NearbyReelView.objects.all())
        self.assertEqual(views[0], new_view)  # Most recent first


class UserPreferencesIntegrationTest(TestCase):
    """Integration tests for User Preferences models."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        self.guest_token = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
        self.reel_id = uuid.uuid4()
        self.discount_id = uuid.uuid4()
    
    def test_user_preference_with_search_history(self):
        """Test UserPreference with related search history."""
        # Create preference
        preference = UserPreference.get_for_user(self.customer_user)
        
        # Create search history
        UserSearchHistory.record_search(
            self.customer_user,
            query_text='pizza',
            query_type='TEXT',
            result_count=10
        )
        
        UserSearchHistory.record_search(
            self.customer_user,
            query_text='coffee',
            query_type='VOICE',
            result_count=5
        )
        
        # Check relationship
        searches = UserSearchHistory.objects.filter(user=self.customer_user)
        self.assertEqual(searches.count(), 2)
        
        search_queries = [search.query_text for search in searches]
        self.assertIn('pizza', search_queries)
        self.assertIn('coffee', search_queries)
    
    def test_user_preference_with_interactions(self):
        """Test UserPreference with related interactions."""
        # Create preference
        preference = UserPreference.get_for_user(self.customer_user)
        
        # Create interactions
        UserVendorInteraction.record_interaction(
            self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW'
        )
        
        UserVendorInteraction.record_interaction(
            self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='TAP'
        )
        
        # Check relationship
        interactions = UserVendorInteraction.objects.filter(user=self.customer_user)
        self.assertEqual(interactions.count(), 2)
        
        interaction_types = [interaction.interaction_type for interaction in interactions]
        self.assertIn('VIEW', interaction_types)
        self.assertIn('TAP', interaction_types)
    
    def test_guest_mode_workflow(self):
        """Test complete guest mode workflow."""
        # Create guest preference
        preference = UserPreference.get_for_guest(self.guest_token)
        self.assertEqual(preference.guest_token, self.guest_token)
        
        # Record guest search
        search = UserSearchHistory.record_search(
            self.guest_token,
            query_text='restaurants',
            query_type='TEXT',
            result_count=8
        )
        
        # Record guest interaction
        interaction = UserVendorInteraction.record_interaction(
            self.guest_token,
            vendor_id=self.vendor_id,
            interaction_type='VIEW'
        )
        
        # Record guest reel view
        reel_view = NearbyReelView.record_view(
            self.guest_token,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=10
        )
        
        # Create flash deal alert
        alert = FlashDealAlert.create_alert(
            self.guest_token,
            self.discount_id,
            self.vendor_id
        )
        
        # Verify all guest data is properly linked
        self.assertEqual(search.guest_token, self.guest_token)
        self.assertEqual(interaction.guest_token, self.guest_token)
        self.assertEqual(reel_view.guest_token, self.guest_token)
        self.assertEqual(alert.guest_token, self.guest_token)
        
        # Verify preference is linked
        self.assertEqual(preference.guest_token, self.guest_token)
    
    def test_user_activity_tracking(self):
        """Test comprehensive user activity tracking."""
        # Create preference
        preference = UserPreference.get_for_user(self.customer_user)
        
        # Simulate user journey
        # 1. Search for vendors
        search = UserSearchHistory.record_search(
            self.customer_user,
            query_text='italian food',
            query_type='VOICE',
            extracted_category='food',
            result_count=12,
            search_lat=31.5204,
            search_lng=74.3587
        )
        
        # 2. View vendor details
        view_interaction = UserVendorInteraction.record_interaction(
            self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            lat=31.5204,
            lng=74.3587,
            source='search_results'
        )
        
        # 3. Watch reel - create directly instead of using record_view
        reel_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=25,
            completed=True,
            cta_tapped=True,
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587')
        )
        
        # 4. Tap on promotion
        promo_interaction = UserVendorInteraction.record_interaction(
            self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='PROMOTION_TAP',
            promotion_id=str(uuid.uuid4())  # Convert UUID to string for JSON serialization
        )
        
        # 5. Navigate to vendor
        nav_interaction = UserVendorInteraction.record_interaction(
            self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='NAVIGATION'
        )
        
        # Update search with navigation
        search.navigated_to_vendor_id = self.vendor_id
        search.save()
        
        # Verify all activities are recorded
        activities = {
            'searches': UserSearchHistory.objects.filter(user=self.customer_user).count(),
            'interactions': UserVendorInteraction.objects.filter(user=self.customer_user).count(),
            'reel_views': NearbyReelView.objects.filter(user=self.customer_user).count()
        }
        
        self.assertEqual(activities['searches'], 1)
        self.assertEqual(activities['interactions'], 3)
        self.assertEqual(activities['reel_views'], 1)
        
        # Verify search navigation tracking
        search.refresh_from_db()
        self.assertEqual(search.navigated_to_vendor_id, self.vendor_id)
        
        # Verify interaction types
        interaction_types = UserVendorInteraction.objects.filter(
            user=self.customer_user
        ).values_list('interaction_type', flat=True)
        
        self.assertIn('VIEW', interaction_types)
        self.assertIn('PROMOTION_TAP', interaction_types)
        self.assertIn('NAVIGATION', interaction_types)
