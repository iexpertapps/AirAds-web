"""
Unit tests for Ranking Service logic.
Tests the core ranking algorithms without requiring full app setup.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.customer_auth.models import CustomerUser
from apps.user_preferences.models import UserPreference, UserSearchHistory

User = get_user_model()


class RankingLogicTest(TestCase):
    """Test cases for ranking service logic with isolated testing."""
    
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
        
        # Create user preferences
        self.preferences = UserPreference.objects.create(
            user=self.customer_user,
            search_radius_m=2000,
            preferred_category_slugs=['restaurant', 'cafe'],
            price_range='MID'
        )
        
        # Create test location (Lahore)
        self.test_point = Point(74.3587, 31.5204, srid=4326)
    
    def test_text_scoring_logic(self):
        """Test text scoring algorithm logic."""
        # Import the scoring function directly
        from apps.discovery.services import RankingService
        
        # Create mock vendor
        vendor = Mock()
        vendor.business_name = 'Test Restaurant'
        vendor.description = 'A great place to eat Pakistani food'
        
        # Test perfect name match
        score = RankingService.calculate_text_score(vendor, 'Test Restaurant')
        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)
        
        # Test partial match
        score = RankingService.calculate_text_score(vendor, 'restaurant')
        self.assertGreater(score, 40)
        self.assertLess(score, 80)
        
        # Test description match
        score = RankingService.calculate_text_score(vendor, 'Pakistani')
        self.assertGreater(score, 30)
        self.assertLess(score, 70)
        
        # Test no match
        score = RankingService.calculate_text_score(vendor, 'completely different')
        self.assertLess(score, 20)
        
        # Test empty query
        score = RankingService.calculate_text_score(vendor, '')
        self.assertEqual(score, 0.0)
    
    def test_distance_scoring_logic(self):
        """Test distance scoring algorithm logic."""
        from apps.discovery.services import RankingService
        
        # Test very close (100m)
        score = RankingService.calculate_distance_score(100)
        self.assertGreater(score, 90)
        self.assertLessEqual(score, 100)
        
        # Test moderate distance (1000m)
        score = RankingService.calculate_distance_score(1000)
        self.assertGreater(score, 50)
        self.assertLess(score, 90)
        
        # Test far distance (5000m)
        score = RankingService.calculate_distance_score(5000)
        self.assertLess(score, 20)
        
        # Test zero distance
        score = RankingService.calculate_distance_score(0)
        self.assertEqual(score, 100.0)
        
        # Test very far distance (10000m)
        score = RankingService.calculate_distance_score(10000)
        self.assertLess(score, 10)
    
    def test_popularity_scoring_logic(self):
        """Test popularity scoring algorithm logic."""
        from apps.discovery.services import RankingService
        
        # Create mock vendor
        vendor = Mock()
        
        # Test high popularity (950 views)
        vendor.total_views = 950
        score = RankingService.calculate_popularity_score(vendor)
        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)
        
        # Test moderate popularity (200 views)
        vendor.total_views = 200
        score = RankingService.calculate_popularity_score(vendor)
        self.assertGreater(score, 40)
        self.assertLess(score, 80)
        
        # Test low popularity (10 views)
        vendor.total_views = 10
        score = RankingService.calculate_popularity_score(vendor)
        self.assertLess(score, 20)
        
        # Test zero popularity
        vendor.total_views = 0
        score = RankingService.calculate_popularity_score(vendor)
        self.assertEqual(score, 0.0)
        
        # Test very high popularity (5000 views)
        vendor.total_views = 5000
        score = RankingService.calculate_popularity_score(vendor)
        self.assertEqual(score, 100.0)  # Should cap at 100
    
    def test_subscription_scoring_logic(self):
        """Test subscription scoring algorithm logic."""
        from apps.discovery.services import RankingService
        
        # Create mock vendor
        vendor = Mock()
        
        # Test Platinum tier
        vendor.subscription_level = 'PLATINUM'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)
        
        # Test Diamond tier
        vendor.subscription_level = 'DIAMOND'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 70)
        self.assertLess(score, 90)
        
        # Test Gold tier
        vendor.subscription_level = 'GOLD'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 60)
        self.assertLess(score, 80)
        
        # Test Silver tier
        vendor.subscription_level = 'SILVER'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 40)
        self.assertLess(score, 60)
        
        # Test Basic tier
        vendor.subscription_level = 'BASIC'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 20)
        self.assertLess(score, 40)
        
        # Test unknown tier (should default to Silver)
        vendor.subscription_level = 'UNKNOWN'
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreater(score, 40)
        self.assertLess(score, 60)
    
    def test_total_score_calculation(self):
        """Test total score calculation logic."""
        from apps.discovery.services import RankingService
        
        # Test with all components
        total_score = RankingService.calculate_total_score(
            text_score=80.0,
            distance_score=90.0,
            offer_score=70.0,
            popularity_score=60.0,
            subscription_score=50.0
        )
        
        # Expected: (80*0.3) + (90*0.25) + (70*0.15) + (60*0.15) + (50*0.15)
        expected = 24.0 + 22.5 + 10.5 + 9.0 + 7.5
        self.assertAlmostEqual(total_score, expected, places=2)
        
        # Test with zeros
        total_score = RankingService.calculate_total_score(0, 0, 0, 0, 0)
        self.assertEqual(total_score, 0.0)
        
        # Test with maximum values
        total_score = RankingService.calculate_total_score(100, 100, 100, 100, 100)
        self.assertEqual(total_score, 100.0)
        
        # Test with mixed values
        total_score = RankingService.calculate_total_score(
            text_score=100,
            distance_score=0,
            offer_score=50,
            popularity_score=100,
            subscription_score=0
        )
        
        expected = (100.0 * 0.3) + (0.0 * 0.25) + (50.0 * 0.15) + (100.0 * 0.15) + (0.0 * 0.15)
        self.assertAlmostEqual(total_score, expected, places=2)
    
    def test_scored_vendor_dataclass(self):
        """Test ScoredVendor dataclass functionality."""
        from apps.discovery.services import ScoredVendor
        
        # Create mock vendor
        vendor = Mock()
        vendor.business_name = 'Test Restaurant'
        
        # Create ScoredVendor instance
        scored_vendor = ScoredVendor(
            vendor=vendor,
            total_score=85.5,
            text_score=25.0,
            distance_score=20.0,
            offer_score=15.0,
            popularity_score=15.0,
            subscription_score=10.5,
            distance_meters=500.0
        )
        
        # Test all attributes
        self.assertEqual(scored_vendor.vendor, vendor)
        self.assertEqual(scored_vendor.total_score, 85.5)
        self.assertEqual(scored_vendor.text_score, 25.0)
        self.assertEqual(scored_vendor.distance_score, 20.0)
        self.assertEqual(scored_vendor.offer_score, 15.0)
        self.assertEqual(scored_vendor.popularity_score, 15.0)
        self.assertEqual(scored_vendor.subscription_score, 10.5)
        self.assertEqual(scored_vendor.distance_meters, 500.0)
        
        # Test string representation
        str_repr = str(scored_vendor)
        self.assertIn('Test Restaurant', str_repr)
        self.assertIn('85.5', str_repr)
    
    def test_ranking_edge_cases(self):
        """Test ranking algorithm edge cases."""
        from apps.discovery.services import RankingService
        
        # Test with very long query
        vendor = Mock()
        vendor.business_name = 'Test Restaurant'
        vendor.description = 'A great place'
        
        long_query = 'test restaurant a great place to eat food with very long query string that might cause issues'
        score = RankingService.calculate_text_score(vendor, long_query)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test with special characters
        special_query = 'café & restaurant! @#$%'
        score = RankingService.calculate_text_score(vendor, special_query)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test distance with negative values (should be handled gracefully)
        score = RankingService.calculate_distance_score(-100)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test very large distance
        score = RankingService.calculate_distance_score(1000000)  # 1000km
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertLess(score, 5)  # Should be very low
    
    def test_scoring_consistency(self):
        """Test that scoring is consistent across multiple calls."""
        from apps.discovery.services import RankingService
        
        vendor = Mock()
        vendor.business_name = 'Test Restaurant'
        vendor.description = 'Great food'
        vendor.total_views = 500
        vendor.subscription_level = 'GOLD'
        
        # Test text scoring consistency
        score1 = RankingService.calculate_text_score(vendor, 'restaurant')
        score2 = RankingService.calculate_text_score(vendor, 'restaurant')
        self.assertEqual(score1, score2)
        
        # Test distance scoring consistency
        score1 = RankingService.calculate_distance_score(1000)
        score2 = RankingService.calculate_distance_score(1000)
        self.assertEqual(score1, score2)
        
        # Test popularity scoring consistency
        score1 = RankingService.calculate_popularity_score(vendor)
        score2 = RankingService.calculate_popularity_score(vendor)
        self.assertEqual(score1, score2)
        
        # Test subscription scoring consistency
        score1 = RankingService.calculate_subscription_score(vendor)
        score2 = RankingService.calculate_subscription_score(vendor)
        self.assertEqual(score1, score2)
    
    def test_scoring_ranges(self):
        """Test that all scoring methods return values in expected ranges."""
        from apps.discovery.services import RankingService
        
        vendor = Mock()
        vendor.business_name = 'Test Restaurant'
        vendor.description = 'Great food'
        vendor.total_views = 500
        vendor.subscription_level = 'GOLD'
        
        # Test text scoring range
        score = RankingService.calculate_text_score(vendor, 'test')
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test distance scoring range
        score = RankingService.calculate_distance_score(1000)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test popularity scoring range
        score = RankingService.calculate_popularity_score(vendor)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test subscription scoring range
        score = RankingService.calculate_subscription_score(vendor)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Test total scoring range
        total_score = RankingService.calculate_total_score(50, 60, 70, 80, 90)
        self.assertGreaterEqual(total_score, 0)
        self.assertLessEqual(total_score, 100)


class UserPreferenceIntegrationTest(TestCase):
    """Test user preferences integration with discovery logic."""
    
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
        """Test user preference creation and validation."""
        # Create preferences with all fields
        preferences = UserPreference.objects.create(
            user=self.customer_user,
            search_radius_m=2000,
            preferred_category_slugs=['restaurant', 'cafe', 'retail'],
            price_range='MID',
            notification_enabled=True,
            location_sharing=True
        )
        
        self.assertEqual(preferences.user, self.customer_user)
        self.assertEqual(preferences.search_radius_m, 2000)
        self.assertEqual(preferences.preferred_category_slugs, ['restaurant', 'cafe', 'retail'])
        self.assertEqual(preferences.price_range, 'MID')
        self.assertTrue(preferences.notification_enabled)
        self.assertTrue(preferences.location_sharing)
    
    def test_user_preference_defaults(self):
        """Test user preference default values."""
        # Create preferences with minimal fields
        preferences = UserPreference.objects.create(
            user=self.customer_user
        )
        
        self.assertEqual(preferences.user, self.customer_user)
        self.assertEqual(preferences.search_radius_m, 2000)  # Default value
        self.assertEqual(preferences.preferred_category_slugs, [])  # Default empty list
        self.assertEqual(preferences.price_range, 'MID')  # Default value
        self.assertFalse(preferences.notification_enabled)  # Default False
        self.assertFalse(preferences.location_sharing)  # Default False
    
    def test_user_preference_uniqueness(self):
        """Test that each user can only have one preference record."""
        # Create first preference
        preferences1 = UserPreference.objects.create(
            user=self.customer_user,
            search_radius_m=1000
        )
        
        # Try to create second preference for same user
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserPreference.objects.create(
                user=self.customer_user,
                search_radius_m=3000
            )
    
    def test_search_history_creation(self):
        """Test search history creation and tracking."""
        # Create search history
        search = UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant near me',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=15,
            extracted_intent='FOOD',
            extracted_categories=['restaurant'],
            extracted_price_range='MID'
        )
        
        self.assertEqual(search.user, self.customer_user)
        self.assertEqual(search.query_text, 'restaurant near me')
        self.assertEqual(search.query_type, 'TEXT')
        self.assertEqual(search.search_lat, self.test_lat)
        self.assertEqual(search.search_lng, self.test_lng)
        self.assertEqual(search.result_count, 15)
        self.assertEqual(search.extracted_intent, 'FOOD')
        self.assertEqual(search.extracted_categories, ['restaurant'])
        self.assertEqual(search.extracted_price_range, 'MID')
    
    def test_search_history_ordering(self):
        """Test that search history is ordered by searched_at DESC."""
        # Create multiple search records
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
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=20
        )
        
        # Get all searches for user
        searches = UserSearchHistory.objects.filter(user=self.customer_user)
        
        # Should be ordered by searched_at DESC (newest first)
        self.assertEqual(searches[0], search2)
        self.assertEqual(searches[1], search1)
    
    def test_guest_search_history(self):
        """Test search history for guest users."""
        # Create search history for guest
        guest_token = uuid.uuid4()
        search = UserSearchHistory.objects.create(
            guest_token=guest_token,
            query_text='guest search',
            query_type='TEXT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=5
        )
        
        self.assertEqual(search.guest_token, guest_token)
        self.assertIsNone(search.user)
        self.assertEqual(search.query_text, 'guest search')
        
        # Should be able to retrieve by guest token
        found_search = UserSearchHistory.objects.get(guest_token=guest_token)
        self.assertEqual(found_search, search)
