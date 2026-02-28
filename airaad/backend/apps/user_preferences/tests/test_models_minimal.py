"""
Unit tests for User Preferences models.
Tests all models without PostGIS dependencies.
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.customer_auth.models import CustomerUser

# Import only models that don't require PostGIS
from ..models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView

User = get_user_model()


class UserPreferenceModelTest(TestCase):
    """Test cases for UserPreference model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create customer user
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create user preference
        self.preference = UserPreference.objects.create(
            user=self.customer_user,
            default_view='AR',
            search_radius_m=500,
            show_open_now_only=False,
            preferred_category_slugs=['food', 'cafe'],
            price_range='MID',
            theme='DARK',
            notifications_nearby_deals=True,
            notifications_flash_deals=True,
            notifications_new_vendors=False,
            notifications_all_off=False,
            auto_location_enabled=True,
            manual_location_lat=Decimal('24.8607'),
            manual_location_lng=Decimal('67.0011'),
            manual_location_name='Karachi'
        )
        
        # Create guest preference
        self.guest_token = uuid.uuid4()
        self.guest_preference = UserPreference.objects.create(
            guest_token=self.guest_token,
            default_view='MAP',
            search_radius_m=1000,
            price_range='BUDGET',
            theme='LIGHT'
        )
    
    def test_user_preference_creation(self):
        """Test UserPreference creation for authenticated user."""
        self.assertEqual(self.preference.user, self.customer_user)
        self.assertEqual(self.preference.default_view, 'AR')
        self.assertEqual(self.preference.search_radius_m, 500)
        self.assertFalse(self.preference.show_open_now_only)
        self.assertEqual(self.preference.preferred_category_slugs, ['food', 'cafe'])
        self.assertEqual(self.preference.price_range, 'MID')
        self.assertEqual(self.preference.theme, 'DARK')
        self.assertTrue(self.preference.notifications_nearby_deals)
        self.assertTrue(self.preference.notifications_flash_deals)
        self.assertFalse(self.preference.notifications_new_vendors)
        self.assertFalse(self.preference.notifications_all_off)
        self.assertTrue(self.preference.auto_location_enabled)
        self.assertEqual(float(self.preference.manual_location_lat), 24.8607)
        self.assertEqual(float(self.preference.manual_location_lng), 67.0011)
        self.assertEqual(self.preference.manual_location_name, 'Karachi')
    
    def test_guest_preference_creation(self):
        """Test UserPreference creation for guest."""
        self.assertEqual(self.guest_preference.guest_token, self.guest_token)
        self.assertEqual(self.guest_preference.default_view, 'MAP')
        self.assertEqual(self.guest_preference.search_radius_m, 1000)
        self.assertEqual(self.guest_preference.price_range, 'BUDGET')
        self.assertEqual(self.guest_preference.theme, 'LIGHT')
        self.assertIsNone(self.guest_preference.user)
    
    def test_preference_str_representation(self):
        """Test string representation."""
        expected = "Preferences for test@example.com"
        self.assertEqual(str(self.preference), expected)
        
        expected_guest = f"Preferences for Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_preference), expected_guest)
    
    def test_get_for_user_class_method(self):
        """Test get_for_user class method."""
        # Get existing preference
        preference = UserPreference.get_for_user(self.customer_user)
        self.assertEqual(preference, self.preference)
        
        # Create preference for new user
        new_user = User.objects.create_user(
            username='new@example.com',
            email='new@example.com',
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
        # Get existing guest preference
        preference = UserPreference.get_for_guest(self.guest_token)
        self.assertEqual(preference, self.guest_preference)
        
        # Create preference for new guest
        new_guest_token = uuid.uuid4()
        new_preference = UserPreference.get_for_guest(new_guest_token)
        self.assertEqual(new_preference.guest_token, new_guest_token)
        self.assertEqual(new_preference.default_view, 'AR')
        self.assertEqual(new_preference.search_radius_m, 500)
        self.assertEqual(new_preference.theme, 'DARK')
        
        # Test invalid guest token
        invalid_preference = UserPreference.get_for_guest('invalid-uuid')
        self.assertIsNone(invalid_preference)
    
    def test_default_view_choices(self):
        """Test all default view choices."""
        views = ['AR', 'MAP', 'LIST']
        
        for view in views:
            preference = UserPreference.objects.create(
                user=self.customer_user,
                default_view=view
            )
            self.assertEqual(preference.default_view, view)
    
    def test_price_range_choices(self):
        """Test all price range choices."""
        price_ranges = ['BUDGET', 'MID', 'PREMIUM']
        
        for price_range in price_ranges:
            preference = UserPreference.objects.create(
                user=self.customer_user,
                price_range=price_range
            )
            self.assertEqual(preference.price_range, price_range)
    
    def test_theme_choices(self):
        """Test all theme choices."""
        themes = ['DARK', 'LIGHT', 'SYSTEM']
        
        for theme in themes:
            preference = UserPreference.objects.create(
                user=self.customer_user,
                theme=theme
            )
            self.assertEqual(preference.theme, theme)
    
    def test_notification_preferences(self):
        """Test notification preference combinations."""
        # All notifications on
        preference = UserPreference.objects.create(
            user=self.customer_user,
            notifications_nearby_deals=True,
            notifications_flash_deals=True,
            notifications_new_vendors=True,
            notifications_all_off=False
        )
        self.assertTrue(preference.notifications_nearby_deals)
        self.assertTrue(preference.notifications_flash_deals)
        self.assertTrue(preference.notifications_new_vendors)
        self.assertFalse(preference.notifications_all_off)
        
        # All notifications off
        preference_all_off = UserPreference.objects.create(
            user=self.customer_user,
            notifications_nearby_deals=False,
            notifications_flash_deals=False,
            notifications_new_vendors=False,
            notifications_all_off=True
        )
        self.assertFalse(preference_all_off.notifications_nearby_deals)
        self.assertFalse(preference_all_off.notifications_flash_deals)
        self.assertFalse(preference_all_off.notifications_new_vendors)
        self.assertTrue(preference_all_off.notifications_all_off)
    
    def test_preferred_categories_json_field(self):
        """Test preferred categories JSON field."""
        # Empty categories
        preference = UserPreference.objects.create(
            user=self.customer_user,
            preferred_category_slugs=[]
        )
        self.assertEqual(preference.preferred_category_slugs, [])
        
        # Multiple categories
        categories = ['food', 'cafe', 'restaurant', 'bakery', 'shopping']
        preference = UserPreference.objects.create(
            user=self.customer_user,
            preferred_category_slugs=categories
        )
        self.assertEqual(preference.preferred_category_slugs, categories)
    
    def test_location_preferences(self):
        """Test location preference fields."""
        # Auto location enabled
        preference = UserPreference.objects.create(
            user=self.customer_user,
            auto_location_enabled=True
        )
        self.assertTrue(preference.auto_location_enabled)
        
        # Manual location set
        preference_manual = UserPreference.objects.create(
            user=self.customer_user,
            auto_location_enabled=False,
            manual_location_lat=Decimal('25.0'),
            manual_location_lng=Decimal('67.0'),
            manual_location_name='Islamabad'
        )
        self.assertFalse(preference_manual.auto_location_enabled)
        self.assertEqual(float(preference_manual.manual_location_lat), 25.0)
        self.assertEqual(float(preference_manual.manual_location_lng), 67.0)
        self.assertEqual(preference_manual.manual_location_name, 'Islamabad')


class UserSearchHistoryModelTest(TestCase):
    """Test cases for UserSearchHistory model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create customer user
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create search history for user
        self.search_history = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='pakistani restaurant',
            query_type='TEXT',
            extracted_category='RESTAURANT',
            extracted_intent={'category': 'RESTAURANT', 'price_range': 'MID'},
            extracted_price_range='MID',
            search_lat=Decimal('24.8607'),
            search_lng=Decimal('67.0011'),
            search_radius_m=1000,
            result_count=15,
            navigated_to_vendor_id=uuid.uuid4()
        )
        
        # Create search history for guest
        self.guest_token = uuid.uuid4()
        self.guest_search_history = UserSearchHistory.objects.create(
            guest_token=self.guest_token,
            query_text='cafe near me',
            query_type='VOICE',
            extracted_category='CAFE',
            result_count=8
        )
    
    def test_search_history_creation(self):
        """Test UserSearchHistory creation."""
        self.assertEqual(self.search_history.user, self.customer_user)
        self.assertEqual(self.search_history.query_text, 'pakistani restaurant')
        self.assertEqual(self.search_history.query_type, 'TEXT')
        self.assertEqual(self.search_history.extracted_category, 'RESTAURANT')
        self.assertEqual(self.search_history.extracted_intent, {'category': 'RESTAURANT', 'price_range': 'MID'})
        self.assertEqual(self.search_history.extracted_price_range, 'MID')
        self.assertEqual(float(self.search_history.search_lat), 24.8607)
        self.assertEqual(float(self.search_history.search_lng), 67.0011)
        self.assertEqual(self.search_history.search_radius_m, 1000)
        self.assertEqual(self.search_history.result_count, 15)
        self.assertIsNotNone(self.search_history.navigated_to_vendor_id)
        self.assertIsNotNone(self.search_history.searched_at)
    
    def test_guest_search_history_creation(self):
        """Test UserSearchHistory creation for guest."""
        self.assertEqual(self.guest_search_history.guest_token, self.guest_token)
        self.assertEqual(self.guest_search_history.query_text, 'cafe near me')
        self.assertEqual(self.guest_search_history.query_type, 'VOICE')
        self.assertEqual(self.guest_search_history.extracted_category, 'CAFE')
        self.assertEqual(self.guest_search_history.result_count, 8)
        self.assertIsNone(self.guest_search_history.user)
    
    def test_search_history_str_representation(self):
        """Test string representation."""
        expected = "Search: 'pakistani restaurant' by test@example.com"
        self.assertEqual(str(self.search_history), expected)
        
        expected_guest = f"Search: 'cafe near me' by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_search_history), expected_guest)
    
    def test_query_type_choices(self):
        """Test all query type choices."""
        query_types = ['TEXT', 'VOICE', 'TAG']
        
        for query_type in query_types:
            search = UserSearchHistory.objects.create(
                user=self.customer_user,
                query_text=f'test {query_type}',
                query_type=query_type
            )
            self.assertEqual(search.query_type, query_type)
    
    def test_record_search_class_method(self):
        """Test record_search class method."""
        # Record search for user
        search = UserSearchHistory.record_search(
            self.customer_user,
            'pizza delivery',
            'TEXT',
            extracted_category='RESTAURANT',
            extracted_intent={'category': 'RESTAURANT'},
            search_lat=Decimal('24.86'),
            search_lng=Decimal('67.00'),
            search_radius_m=2000,
            result_count=12
        )
        
        self.assertEqual(search.user, self.customer_user)
        self.assertEqual(search.query_text, 'pizza delivery')
        self.assertEqual(search.query_type, 'TEXT')
        self.assertEqual(search.extracted_category, 'RESTAURANT')
        self.assertEqual(search.result_count, 12)
        
        # Record search for guest
        guest_search = UserSearchHistory.record_search(
            self.guest_token,
            'coffee shops',
            'VOICE',
            extracted_category='CAFE',
            result_count=5
        )
        
        self.assertEqual(guest_search.guest_token, self.guest_token)
        self.assertEqual(guest_search.query_text, 'coffee shops')
        self.assertEqual(guest_search.query_type, 'VOICE')
        self.assertEqual(guest_search.extracted_category, 'CAFE')
    
    def test_extracted_fields_json(self):
        """Test extracted fields as JSON."""
        # Complex extracted intent
        complex_intent = {
            'category': 'RESTAURANT',
            'price_range': 'BUDGET',
            'features': ['delivery', 'takeout'],
            'time_of_day': 'lunch'
        }
        
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='cheap lunch delivery',
            query_type='TEXT',
            extracted_intent=complex_intent,
            extracted_category='RESTAURANT',
            extracted_price_range='BUDGET'
        )
        
        self.assertEqual(search.extracted_intent, complex_intent)
        self.assertEqual(search.extracted_category, 'RESTAURANT')
        self.assertEqual(search.extracted_price_range, 'BUDGET')
    
    def test_search_ordering(self):
        """Test search history ordering."""
        # Create multiple searches
        search1 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='first search',
            query_type='TEXT'
        )
        search2 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='second search',
            query_type='TEXT'
        )
        
        # Query searches ordered by searched_at (descending)
        searches = UserSearchHistory.objects.filter(user=self.customer_user)
        
        # Most recent should be first
        self.assertEqual(searches[0], search2)
        self.assertEqual(searches[1], search1)
        self.assertEqual(searches[2], self.search_history)  # From setUp


class UserVendorInteractionModelTest(TestCase):
    """Test cases for UserVendorInteraction model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create customer user
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create vendor interaction
        self.vendor_id = uuid.uuid4()
        self.session_id = uuid.uuid4()
        self.interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='VIEW',
            session_id=self.session_id,
            lat=Decimal('24.8607'),
            lng=Decimal('67.0011'),
            metadata={'source': 'ar_view', 'duration_seconds': 30}
        )
        
        # Create guest interaction
        self.guest_token = uuid.uuid4()
        self.guest_session_id = uuid.uuid4()
        self.guest_interaction = UserVendorInteraction.objects.create(
            guest_token=self.guest_token,
            vendor_id=uuid.uuid4(),
            interaction_type='TAP',
            session_id=self.guest_session_id,
            metadata={'source': 'map_view'}
        )
    
    def test_vendor_interaction_creation(self):
        """Test UserVendorInteraction creation."""
        self.assertEqual(self.interaction.user, self.customer_user)
        self.assertEqual(self.interaction.vendor_id, self.vendor_id)
        self.assertEqual(self.interaction.interaction_type, 'VIEW')
        self.assertEqual(self.interaction.session_id, self.session_id)
        self.assertEqual(float(self.interaction.lat), 24.8607)
        self.assertEqual(float(self.interaction.lng), 67.0011)
        self.assertEqual(self.interaction.metadata, {'source': 'ar_view', 'duration_seconds': 30})
        self.assertIsNotNone(self.interaction.interacted_at)
    
    def test_guest_interaction_creation(self):
        """Test UserVendorInteraction creation for guest."""
        self.assertEqual(self.guest_interaction.guest_token, self.guest_token)
        self.assertEqual(self.guest_interaction.interaction_type, 'TAP')
        self.assertEqual(self.guest_interaction.session_id, self.guest_session_id)
        self.assertEqual(self.guest_interaction.metadata, {'source': 'map_view'})
        self.assertIsNone(self.guest_interaction.user)
    
    def test_interaction_str_representation(self):
        """Test string representation."""
        expected = f"VIEW: Vendor {self.vendor_id} by test@example.com"
        self.assertEqual(str(self.interaction), expected)
        
        expected_guest = f"TAP: Vendor {self.guest_interaction.vendor_id} by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_interaction), expected_guest)
    
    def test_interaction_type_choices(self):
        """Test all interaction type choices."""
        interaction_types = ['VIEW', 'TAP', 'NAVIGATION', 'CALL', 'REEL_VIEW', 'PROMOTION_TAP', 'ARRIVAL', 'SHARE', 'FAVORITE']
        
        for interaction_type in interaction_types:
            interaction = UserVendorInteraction.objects.create(
                user=self.customer_user,
                vendor_id=uuid.uuid4(),
                interaction_type=interaction_type,
                session_id=uuid.uuid4()
            )
            self.assertEqual(interaction.interaction_type, interaction_type)
    
    def test_record_interaction_class_method(self):
        """Test record_interaction class method."""
        # Record interaction for user
        interaction = UserVendorInteraction.record_interaction(
            self.customer_user,
            uuid.uuid4(),
            'NAVIGATION',
            session_id=uuid.uuid4(),
            lat=Decimal('24.86'),
            lng=Decimal('67.00'),
            source='map_click',
            duration_seconds=45
        )
        
        self.assertEqual(interaction.user, self.customer_user)
        self.assertEqual(interaction.interaction_type, 'NAVIGATION')
        self.assertEqual(interaction.metadata, {'source': 'map_click', 'duration_seconds': 45})
        
        # Record interaction for guest
        guest_interaction = UserVendorInteraction.record_interaction(
            self.guest_token,
            uuid.uuid4(),
            'CALL',
            session_id=uuid.uuid4(),
            phone_number='+1234567890'
        )
        
        self.assertEqual(guest_interaction.guest_token, self.guest_token)
        self.assertEqual(guest_interaction.interaction_type, 'CALL')
        self.assertEqual(guest_interaction.metadata, {'phone_number': '+1234567890'})
    
    def test_metadata_json_field(self):
        """Test metadata JSON field."""
        # Complex metadata
        complex_metadata = {
            'source': 'ar_view',
            'duration_seconds': 120,
            'user_action': 'pinch_to_zoom',
            'device_info': {
                'platform': 'ios',
                'version': '1.0.0'
            },
            'context': {
                'nearby_vendors': 5,
                'weather': 'sunny'
            }
        }
        
        interaction = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='VIEW',
            session_id=uuid.uuid4(),
            metadata=complex_metadata
        )
        
        self.assertEqual(interaction.metadata, complex_metadata)
    
    def test_interaction_ordering(self):
        """Test interaction ordering by interacted_at."""
        # Create multiple interactions
        interaction1 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        interaction2 = UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=uuid.uuid4(),
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        # Query interactions ordered by interacted_at (descending)
        interactions = UserVendorInteraction.objects.filter(user=self.customer_user)
        
        # Most recent should be first
        self.assertEqual(interactions[0], interaction2)
        self.assertEqual(interactions[1], interaction1)
        self.assertEqual(interactions[2], self.interaction)  # From setUp


class FlashDealAlertModelTest(TestCase):
    """Test cases for FlashDealAlert model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create customer user
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create flash deal alert for user
        self.discount_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
        self.alert = FlashDealAlert.objects.create(
            user=self.customer_user,
            discount_id=self.discount_id,
            vendor_id=self.vendor_id
        )
        
        # Create flash deal alert for guest
        self.guest_token = uuid.uuid4()
        self.guest_alert = FlashDealAlert.objects.create(
            guest_token=self.guest_token,
            discount_id=uuid.uuid4(),
            vendor_id=uuid.uuid4()
        )
    
    def test_flash_deal_alert_creation(self):
        """Test FlashDealAlert creation."""
        self.assertEqual(self.alert.user, self.customer_user)
        self.assertEqual(self.alert.discount_id, self.discount_id)
        self.assertEqual(self.alert.vendor_id, self.vendor_id)
        self.assertFalse(self.alert.dismissed)
        self.assertFalse(self.alert.tapped)
        self.assertIsNone(self.alert.dismissed_at)
        self.assertIsNone(self.alert.tapped_at)
        self.assertIsNotNone(self.alert.alerted_at)
    
    def test_guest_alert_creation(self):
        """Test FlashDealAlert creation for guest."""
        self.assertEqual(self.guest_alert.guest_token, self.guest_token)
        self.assertIsNone(self.guest_alert.user)
        self.assertFalse(self.guest_alert.dismissed)
        self.assertFalse(self.guest_alert.tapped)
    
    def test_alert_str_representation(self):
        """Test string representation."""
        expected = f"Flash alert: Discount {self.discount_id} for test@example.com"
        self.assertEqual(str(self.alert), expected)
        
        expected_guest = f"Flash alert: Discount {self.guest_alert.discount_id} for Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_alert), expected_guest)
    
    def test_should_alert_class_method(self):
        """Test should_alert class method."""
        # Test non-existent alert (should alert)
        new_discount_id = uuid.uuid4()
        new_vendor_id = uuid.uuid4()
        should_alert = FlashDealAlert.should_alert(self.customer_user, new_discount_id, new_vendor_id)
        self.assertTrue(should_alert)
        
        # Test existing alert (should not alert)
        should_not_alert = FlashDealAlert.should_alert(self.customer_user, self.discount_id, self.vendor_id)
        self.assertFalse(should_not_alert)
        
        # Test guest alert
        guest_should_alert = FlashDealAlert.should_alert(self.guest_token, uuid.uuid4(), uuid.uuid4())
        self.assertTrue(guest_should_alert)
        
        guest_should_not_alert = FlashDealAlert.should_alert(self.guest_token, self.guest_alert.discount_id, self.guest_alert.vendor_id)
        self.assertFalse(guest_should_not_alert)
    
    def test_create_alert_class_method(self):
        """Test create_alert class method."""
        # Create alert for user
        new_discount_id = uuid.uuid4()
        new_vendor_id = uuid.uuid4()
        alert = FlashDealAlert.create_alert(self.customer_user, new_discount_id, new_vendor_id)
        
        self.assertEqual(alert.user, self.customer_user)
        self.assertEqual(alert.discount_id, new_discount_id)
        self.assertEqual(alert.vendor_id, new_vendor_id)
        
        # Create alert for guest
        guest_alert = FlashDealAlert.create_alert(self.guest_token, uuid.uuid4(), uuid.uuid4())
        
        self.assertEqual(guest_alert.guest_token, self.guest_token)
        self.assertIsNone(guest_alert.user)
    
    def test_alert_dismissal(self):
        """Test alert dismissal functionality."""
        # Dismiss alert
        self.alert.dismissed = True
        self.alert.dismissed_at = timezone.now()
        self.alert.save()
        
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.dismissed)
        self.assertIsNotNone(self.alert.dismissed_at)
    
    def test_alert_tap(self):
        """Test alert tap functionality."""
        # Tap alert
        self.alert.tapped = True
        self.alert.tapped_at = timezone.now()
        self.alert.save()
        
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.tapped)
        self.assertIsNotNone(self.alert.tapped_at)
    
    def test_unique_constraints(self):
        """Test unique constraints on alerts."""
        # Try to create duplicate alert for same user and discount
        with self.assertRaises(Exception):  # Should be IntegrityError
            FlashDealAlert.objects.create(
                user=self.customer_user,
                discount_id=self.discount_id,
                vendor_id=uuid.uuid4()  # Different vendor_id but same discount_id should still fail
            )


class NearbyReelViewModelTest(TestCase):
    """Test cases for NearbyReelView model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create customer user
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create reel view for user
        self.reel_id = uuid.uuid4()
        self.vendor_id = uuid.uuid4()
        self.reel_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=self.reel_id,
            vendor_id=self.vendor_id,
            watched_seconds=30,
            completed=True,
            cta_tapped=True,
            lat=Decimal('24.8607'),
            lng=Decimal('67.0011')
        )
        
        # Create reel view for guest
        self.guest_token = uuid.uuid4()
        self.guest_reel_view = NearbyReelView.objects.create(
            guest_token=self.guest_token,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=15,
            completed=False,
            cta_tapped=False
        )
    
    def test_reel_view_creation(self):
        """Test NearbyReelView creation."""
        self.assertEqual(self.reel_view.user, self.customer_user)
        self.assertEqual(self.reel_view.reel_id, self.reel_id)
        self.assertEqual(self.reel_view.vendor_id, self.vendor_id)
        self.assertEqual(self.reel_view.watched_seconds, 30)
        self.assertTrue(self.reel_view.completed)
        self.assertTrue(self.reel_view.cta_tapped)
        self.assertEqual(float(self.reel_view.lat), 24.8607)
        self.assertEqual(float(self.reel_view.lng), 67.0011)
        self.assertIsNotNone(self.reel_view.viewed_at)
    
    def test_guest_reel_view_creation(self):
        """Test NearbyReelView creation for guest."""
        self.assertEqual(self.guest_reel_view.guest_token, self.guest_token)
        self.assertEqual(self.guest_reel_view.watched_seconds, 15)
        self.assertFalse(self.guest_reel_view.completed)
        self.assertFalse(self.guest_reel_view.cta_tapped)
        self.assertIsNone(self.guest_reel_view.user)
    
    def test_reel_view_str_representation(self):
        """Test string representation."""
        expected = f"Reel view: {self.reel_id} (30s) by test@example.com"
        self.assertEqual(str(self.reel_view), expected)
        
        expected_guest = f"Reel view: {self.guest_reel_view.reel_id} (15s) by Guest: {self.guest_token}"
        self.assertEqual(str(self.guest_reel_view), expected_guest)
    
    def test_record_view_class_method(self):
        """Test record_view class method."""
        # Record view for user
        new_reel_id = uuid.uuid4()
        new_vendor_id = uuid.uuid4()
        view = NearbyReelView.record_view(
            self.customer_user,
            new_reel_id,
            new_vendor_id,
            watched_seconds=45,
            completed=True,
            cta_tapped=True,
            lat=Decimal('24.86'),
            lng=Decimal('67.00')
        )
        
        self.assertEqual(view.user, self.customer_user)
        self.assertEqual(view.reel_id, new_reel_id)
        self.assertEqual(view.watched_seconds, 45)
        self.assertTrue(view.completed)
        self.assertTrue(view.cta_tapped)
        
        # Record view for guest
        guest_view = NearbyReelView.record_view(
            self.guest_token,
            uuid.uuid4(),
            uuid.uuid4(),
            watched_seconds=20,
            completed=False
        )
        
        self.assertEqual(guest_view.guest_token, self.guest_token)
        self.assertEqual(guest_view.watched_seconds, 20)
        self.assertFalse(guest_view.completed)
    
    def test_view_ordering(self):
        """Test view ordering by viewed_at."""
        # Create multiple views
        view1 = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=10
        )
        view2 = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=25
        )
        
        # Query views ordered by viewed_at (descending)
        views = NearbyReelView.objects.filter(user=self.customer_user)
        
        # Most recent should be first
        self.assertEqual(views[0], view2)
        self.assertEqual(views[1], view1)
        self.assertEqual(views[2], self.reel_view)  # From setUp
    
    def test_completion_tracking(self):
        """Test completion tracking functionality."""
        # Test completed view
        self.assertTrue(self.reel_view.completed)
        
        # Test incomplete view
        incomplete_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=5,
            completed=False
        )
        self.assertFalse(incomplete_view.completed)
    
    def test_cta_tracking(self):
        """Test CTA tap tracking functionality."""
        # Test CTA tapped
        self.assertTrue(self.reel_view.cta_tapped)
        
        # Test CTA not tapped
        no_cta_view = NearbyReelView.objects.create(
            user=self.customer_user,
            reel_id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            watched_seconds=10,
            cta_tapped=False
        )
        self.assertFalse(no_cta_view.cta_tapped)
    
    def test_watched_seconds_validation(self):
        """Test watched seconds field."""
        # Test various watched seconds values
        test_cases = [0, 5, 15, 30, 60, 120]
        
        for seconds in test_cases:
            view = NearbyReelView.objects.create(
                user=self.customer_user,
                reel_id=uuid.uuid4(),
                vendor_id=uuid.uuid4(),
                watched_seconds=seconds
            )
            self.assertEqual(view.watched_seconds, seconds)
