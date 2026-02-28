"""
Integration tests for User Preferences with Discovery concepts.
Tests UserPreference and UserSearchHistory models that support discovery functionality.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customer_auth.models import CustomerUser
from apps.user_preferences.models import UserPreference, UserSearchHistory

User = get_user_model()


class UserPreferenceDiscoveryTest(TestCase):
    """Test UserPreference model functionality for discovery features."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user and customer user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create test location
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_user_preference_creation(self):
        """Test user preference creation with discovery-related fields."""
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
    
    def test_user_preference_views(self):
        """Test different view preference options."""
        # Test AR view
        ar_prefs = UserPreference.objects.create(
            user=self.customer_user,
            default_view='AR'
        )
        self.assertEqual(ar_prefs.default_view, 'AR')
        
        # Test MAP view
        map_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='map@example.com',
                    username='map@example.com',
                    password='testpass123'
                ),
                display_name='Map User'
            ),
            default_view='MAP'
        )
        self.assertEqual(map_prefs.default_view, 'MAP')
        
        # Test LIST view
        list_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='list@example.com',
                    username='list@example.com',
                    password='testpass123'
                ),
                display_name='List User'
            ),
            default_view='LIST'
        )
        self.assertEqual(list_prefs.default_view, 'LIST')
    
    def test_user_preference_price_ranges(self):
        """Test different price range options."""
        # Test BUDGET
        budget_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='budget@example.com',
                    username='budget@example.com',
                    password='testpass123'
                ),
                display_name='Budget User'
            ),
            price_range='BUDGET'
        )
        self.assertEqual(budget_prefs.price_range, 'BUDGET')
        
        # Test MID (default)
        mid_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='mid@example.com',
                    username='mid@example.com',
                    password='testpass123'
                ),
                display_name='Mid User'
            ),
            price_range='MID'
        )
        self.assertEqual(mid_prefs.price_range, 'MID')
        
        # Test PREMIUM
        premium_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='premium@example.com',
                    username='premium@example.com',
                    password='testpass123'
                ),
                display_name='Premium User'
            ),
            price_range='PREMIUM'
        )
        self.assertEqual(premium_prefs.price_range, 'PREMIUM')
    
    def test_user_preference_search_radius(self):
        """Test search radius preferences."""
        # Test different radius values
        radius_tests = [100, 500, 1000, 2000, 5000, 10000]
        
        for i, radius in enumerate(radius_tests):
            user = CustomerUser.objects.create(
                user=User.objects.create_user(
                    email=f'user{i}@example.com',
                    username=f'user{i}@example.com',
                    password='testpass123'
                ),
                display_name=f'User {i}'
            )
            
            prefs = UserPreference.objects.create(
                user=user,
                search_radius_m=radius
            )
            self.assertEqual(prefs.search_radius_m, radius)
    
    def test_user_preference_categories(self):
        """Test preferred category slugs."""
        # Test single category
        single_cat_prefs = UserPreference.objects.create(
            user=self.customer_user,
            preferred_category_slugs=['restaurant']
        )
        self.assertEqual(single_cat_prefs.preferred_category_slugs, ['restaurant'])
        
        # Test multiple categories
        multi_cat_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='multi@example.com',
                    username='multi@example.com',
                    password='testpass123'
                ),
                display_name='Multi User'
            ),
            preferred_category_slugs=['restaurant', 'cafe', 'retail', 'entertainment']
        )
        self.assertEqual(multi_cat_prefs.preferred_category_slugs, ['restaurant', 'cafe', 'retail', 'entertainment'])
        
        # Test empty categories
        empty_cat_prefs = UserPreference.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='empty@example.com',
                    username='empty@example.com',
                    password='testpass123'
                ),
                display_name='Empty User'
            ),
            preferred_category_slugs=[]
        )
        self.assertEqual(empty_cat_prefs.preferred_category_slugs, [])
    
    def test_user_preference_uniqueness(self):
        """Test that each user can only have one preference record."""
        # Create first preference
        prefs1 = UserPreference.objects.create(
            user=self.customer_user,
            search_radius_m=1000
        )
        
        # Try to create second preference for same user should fail
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                user=self.customer_user,
                search_radius_m=2000
            )
    
    def test_guest_preferences(self):
        """Test guest user preferences."""
        guest_token = uuid.uuid4()
        
        # Create guest preferences
        guest_prefs = UserPreference.objects.create(
            guest_token=guest_token,
            default_view='LIST',
            search_radius_m=1500,
            preferred_category_slugs=['cafe'],
            price_range='BUDGET'
        )
        
        self.assertEqual(guest_prefs.guest_token, guest_token)
        self.assertIsNone(guest_prefs.user)
        self.assertEqual(guest_prefs.default_view, 'LIST')
        self.assertEqual(guest_prefs.search_radius_m, 1500)
        self.assertEqual(guest_prefs.preferred_category_slugs, ['cafe'])
        self.assertEqual(guest_prefs.price_range, 'BUDGET')
    
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
        guest_token = uuid.uuid4()
        
        # Create preferences using class method
        prefs = UserPreference.get_for_guest(guest_token)
        
        self.assertEqual(prefs.guest_token, guest_token)
        self.assertIsNone(prefs.user)
        self.assertEqual(prefs.default_view, 'AR')  # Default
        self.assertEqual(prefs.search_radius_m, 500)  # Default
        
        # Test that it returns existing preferences
        existing_prefs = UserPreference.get_for_guest(guest_token)
        self.assertEqual(prefs.id, existing_prefs.id)


class UserSearchHistoryDiscoveryTest(TestCase):
    """Test UserSearchHistory model functionality for discovery features."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user and customer user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Create test location
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_search_history_creation(self):
        """Test search history creation."""
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant near me',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=15
        )
        
        self.assertEqual(search.user, self.customer_user)
        self.assertEqual(search.query_text, 'restaurant near me')
        self.assertEqual(search.query_type, 'TEXT')
        self.assertEqual(search.search_lat, self.test_lat)
        self.assertEqual(search.search_lng, self.test_lng)
        self.assertEqual(search.result_count, 15)
    
    def test_search_history_query_types(self):
        """Test different query types."""
        query_types = ['TEXT', 'VOICE', 'CATEGORY', 'LOCATION']
        
        for i, query_type in enumerate(query_types):
            search = UserSearchHistory.objects.create(
                user=self.customer_user,
                query_text=f'test query {i}',
                query_type=query_type,
                search_lat=self.test_lat,
                search_lng=self.test_lng,
                result_count=i * 5
            )
            self.assertEqual(search.query_type, query_type)
    
    def test_search_history_guest(self):
        """Test search history for guest users."""
        guest_token = uuid.uuid4()
        
        search = UserSearchHistory.objects.create(
            guest_token=guest_token,
            query_text='guest search',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=8
        )
        
        self.assertEqual(search.guest_token, guest_token)
        self.assertIsNone(search.user)
        self.assertEqual(search.query_text, 'guest search')
    
    def test_search_history_ordering(self):
        """Test that search history is ordered by searched_at DESC."""
        # Create multiple searches
        search1 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='first search',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=10
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.01)
        
        search2 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='second search',
            query_type='VOICE',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=20
        )
        
        # Get all searches for user
        searches = UserSearchHistory.objects.filter(user=self.customer_user)
        
        # Should be ordered by searched_at DESC (newest first)
        self.assertEqual(searches[0], search2)
        self.assertEqual(searches[1], search1)
    
    def test_search_history_with_location(self):
        """Test search history with location data."""
        # Test with valid coordinates
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            search_lat=31.5204,
            search_lng=74.3587,
            result_count=12
        )
        
        self.assertEqual(search.search_lat, 31.5204)
        self.assertEqual(search.search_lng, 74.3587)
        
        # Test with different coordinates
        search2 = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='cafe',
            query_type='CATEGORY',
            search_lat=31.5210,
            search_lng=74.3590,
            result_count=8
        )
        
        self.assertEqual(search2.search_lat, 31.5210)
        self.assertEqual(search2.search_lng, 74.3590)
    
    def test_search_history_result_counts(self):
        """Test different result counts."""
        result_counts = [0, 1, 5, 10, 25, 50, 100]
        
        for i, count in enumerate(result_counts):
            search = UserSearchHistory.objects.create(
                user=self.customer_user,
                query_text=f'search {i}',
                query_type='TEXT',
                search_lat=self.test_lat,
                search_lng=self.test_lng,
                result_count=count
            )
            self.assertEqual(search.result_count, count)
    
    def test_search_history_query_lengths(self):
        """Test different query text lengths."""
        # Test short query
        short_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='cafe',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=5
        )
        self.assertEqual(short_search.query_text, 'cafe')
        
        # Test long query
        long_query = 'best pakistani restaurant with outdoor seating and live music near me'
        long_search = UserSearchHistory.objects.create(
            user=CustomerUser.objects.create(
                user=User.objects.create_user(
                    email='long@example.com',
                    username='long@example.com',
                    password='testpass123'
                ),
                display_name='Long Query User'
            ),
            query_text=long_query,
            query_type='VOICE',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=3
        )
        self.assertEqual(long_search.query_text, long_query)
    
    def test_search_history_filtering(self):
        """Test filtering search history."""
        # Create searches with different types
        text_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=10
        )
        
        voice_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='cafe near me',
            query_type='VOICE',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=8
        )
        
        # Filter by query type
        text_searches = UserSearchHistory.objects.filter(
            user=self.customer_user,
            query_type='TEXT'
        )
        self.assertEqual(text_searches.count(), 1)
        self.assertEqual(text_searches[0], text_search)
        
        voice_searches = UserSearchHistory.objects.filter(
            user=self.customer_user,
            query_type='VOICE'
        )
        self.assertEqual(voice_searches.count(), 1)
        self.assertEqual(voice_searches[0], voice_search)
    
    def test_search_history_with_guest_and_user(self):
        """Test that searches can be created for both users and guests."""
        guest_token = uuid.uuid4()
        
        # Create guest search
        guest_search = UserSearchHistory.objects.create(
            guest_token=guest_token,
            query_text='guest search',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=5
        )
        
        # Create user search
        user_search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='user search',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=10
        )
        
        # Verify they are separate
        self.assertIsNone(guest_search.user)
        self.assertIsNotNone(guest_search.guest_token)
        
        self.assertIsNotNone(user_search.user)
        self.assertIsNone(user_search.guest_token)
        
        # Filter by user
        user_searches = UserSearchHistory.objects.filter(user=self.customer_user)
        self.assertEqual(user_searches.count(), 1)
        self.assertEqual(user_searches[0], user_search)
        
        # Filter by guest
        guest_searches = UserSearchHistory.objects.filter(guest_token=guest_token)
        self.assertEqual(guest_searches.count(), 1)
        self.assertEqual(guest_searches[0], guest_search)
