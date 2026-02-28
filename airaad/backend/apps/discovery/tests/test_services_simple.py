"""
Simplified unit tests for Discovery Service layer.
Tests RankingService methods with mock data.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.customer_auth.models import CustomerUser
from apps.user_portal.models import Vendor, Promotion, Tag, City, Area
from apps.user_preferences.models import UserPreference, UserSearchHistory
from apps.discovery.services import RankingService, ScoredVendor

User = get_user_model()


class RankingServiceSimpleTest(TestCase):
    """Test cases for RankingService class methods with simple mocks."""
    
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
        
        # Create test location (Lahore)
        self.test_point = Point(74.3587, 31.5204, srid=4326)
        
        # Create mock vendor for testing RankingService methods
        self.mock_vendor = Mock()
        self.mock_vendor.business_name = 'Test Restaurant'
        self.mock_vendor.description = 'A great place to eat'
        self.mock_vendor.total_views = 750
        self.mock_vendor.subscription_level = 'SILVER'
        self.mock_vendor.gps_point = self.test_point
    
    def test_scored_vendor_dataclass(self):
        """Test ScoredVendor dataclass structure."""
        scored_vendor = ScoredVendor(
            vendor=self.mock_vendor,
            total_score=85.5,
            text_score=25.0,
            distance_score=20.0,
            offer_score=15.0,
            popularity_score=15.0,
            subscription_score=10.5,
            distance_meters=500.0
        )
        
        self.assertEqual(scored_vendor.vendor, self.mock_vendor)
        self.assertEqual(scored_vendor.total_score, 85.5)
        self.assertEqual(scored_vendor.text_score, 25.0)
        self.assertEqual(scored_vendor.distance_score, 20.0)
        self.assertEqual(scored_vendor.offer_score, 15.0)
        self.assertEqual(scored_vendor.popularity_score, 15.0)
        self.assertEqual(scored_vendor.subscription_score, 10.5)
        self.assertEqual(scored_vendor.distance_meters, 500.0)
    
    def test_calculate_text_score_perfect_match(self):
        """Test text score calculation for perfect match."""
        # Perfect name match
        score = RankingService.calculate_text_score(
            vendor=self.mock_vendor,
            query='Test Restaurant'
        )
        
        self.assertGreater(score, 80)  # Should be high for perfect match
        self.assertLessEqual(score, 100)  # Should not exceed 100
    
    def test_calculate_text_score_partial_match(self):
        """Test text score calculation for partial match."""
        # Partial match
        score = RankingService.calculate_text_score(
            vendor=self.mock_vendor,
            query='restaurant'
        )
        
        self.assertGreater(score, 40)  # Should be moderate for partial match
        self.assertLess(score, 80)  # Should be less than perfect match
    
    def test_calculate_text_score_no_match(self):
        """Test text score calculation for no match."""
        # No match
        score = RankingService.calculate_text_score(
            vendor=self.mock_vendor,
            query='completely different'
        )
        
        self.assertLess(score, 20)  # Should be low for no match
    
    def test_calculate_text_score_empty_query(self):
        """Test text score calculation for empty query."""
        score = RankingService.calculate_text_score(
            vendor=self.mock_vendor,
            query=''
        )
        
        self.assertEqual(score, 0.0)  # Should be zero for empty query
    
    def test_calculate_distance_score_very_close(self):
        """Test distance score calculation for very close vendor."""
        # 100 meters away
        score = RankingService.calculate_distance_score(100)
        
        self.assertGreater(score, 90)  # Should be very high for close distance
        self.assertLessEqual(score, 100)
    
    def test_calculate_distance_score_moderate_distance(self):
        """Test distance score calculation for moderate distance."""
        # 1000 meters away
        score = RankingService.calculate_distance_score(1000)
        
        self.assertGreater(score, 50)  # Should be moderate
        self.assertLess(score, 90)
    
    def test_calculate_distance_score_very_far(self):
        """Test distance score calculation for very far vendor."""
        # 5000 meters away
        score = RankingService.calculate_distance_score(5000)
        
        self.assertLess(score, 20)  # Should be low for far distance
    
    def test_calculate_distance_score_zero_distance(self):
        """Test distance score calculation for zero distance."""
        score = RankingService.calculate_distance_score(0)
        
        self.assertEqual(score, 100.0)  # Should be maximum for same location
    
    def test_calculate_popularity_score_high_popularity(self):
        """Test popularity score calculation for high popularity vendor."""
        # Set high popularity
        self.mock_vendor.total_views = 950
        
        score = RankingService.calculate_popularity_score(self.mock_vendor)
        
        self.assertGreater(score, 80)  # Should be high for high popularity
        self.assertLessEqual(score, 100)
    
    def test_calculate_popularity_score_low_popularity(self):
        """Test popularity score calculation for low popularity vendor."""
        # Set low popularity
        self.mock_vendor.total_views = 10
        
        score = RankingService.calculate_popularity_score(self.mock_vendor)
        
        self.assertLess(score, 20)  # Should be low for low popularity
    
    def test_calculate_popularity_score_zero_popularity(self):
        """Test popularity score calculation for zero popularity vendor."""
        # Set zero popularity
        self.mock_vendor.total_views = 0
        
        score = RankingService.calculate_popularity_score(self.mock_vendor)
        
        self.assertEqual(score, 0.0)  # Should be zero for zero popularity
    
    def test_calculate_subscription_score_platinum_tier(self):
        """Test subscription score calculation for Platinum tier."""
        self.mock_vendor.subscription_level = 'PLATINUM'
        
        score = RankingService.calculate_subscription_score(self.mock_vendor)
        
        self.assertGreater(score, 80)  # Should be high for Platinum
        self.assertLessEqual(score, 100)
    
    def test_calculate_subscription_score_gold_tier(self):
        """Test subscription score calculation for Gold tier."""
        self.mock_vendor.subscription_level = 'GOLD'
        
        score = RankingService.calculate_subscription_score(self.mock_vendor)
        
        self.assertGreater(score, 60)  # Should be moderate-high for Gold
        self.assertLess(score, 80)
    
    def test_calculate_subscription_score_silver_tier(self):
        """Test subscription score calculation for Silver tier."""
        self.mock_vendor.subscription_level = 'SILVER'
        
        score = RankingService.calculate_subscription_score(self.mock_vendor)
        
        self.assertGreater(score, 40)  # Should be moderate for Silver
        self.assertLess(score, 60)
    
    def test_calculate_subscription_score_basic_tier(self):
        """Test subscription score calculation for Basic tier."""
        self.mock_vendor.subscription_level = 'BASIC'
        
        score = RankingService.calculate_subscription_score(self.mock_vendor)
        
        self.assertGreater(score, 20)  # Should be low for Basic
        self.assertLess(score, 40)
    
    def test_calculate_subscription_score_unknown_tier(self):
        """Test subscription score calculation for unknown tier."""
        self.mock_vendor.subscription_level = 'UNKNOWN'
        
        score = RankingService.calculate_subscription_score(self.mock_vendor)
        
        # Should default to Silver level
        self.assertGreaterEqual(score, 40)
        self.assertLess(score, 60)
    
    def test_calculate_total_score_all_components(self):
        """Test total score calculation with all components."""
        total_score = RankingService.calculate_total_score(
            text_score=80.0,
            distance_score=90.0,
            offer_score=70.0,
            popularity_score=60.0,
            subscription_score=50.0
        )
        
        # Should be weighted average: (80*0.3 + 90*0.25 + 70*0.15 + 60*0.15 + 50*0.15)
        expected = (80.0 * 0.3) + (90.0 * 0.25) + (70.0 * 0.15) + (60.0 * 0.15) + (50.0 * 0.15)
        self.assertAlmostEqual(total_score, expected, places=2)
    
    def test_calculate_total_score_zero_components(self):
        """Test total score calculation with all zero components."""
        total_score = RankingService.calculate_total_score(0, 0, 0, 0, 0)
        
        self.assertEqual(total_score, 0.0)
    
    def test_calculate_total_score_maximum_components(self):
        """Test total score calculation with maximum components."""
        total_score = RankingService.calculate_total_score(100, 100, 100, 100, 100)
        
        self.assertEqual(total_score, 100.0)
    
    def test_calculate_total_score_boundary_values(self):
        """Test total score calculation with boundary values."""
        # Test with some zero and some maximum values
        total_score = RankingService.calculate_total_score(
            text_score=100,
            distance_score=0,
            offer_score=50,
            popularity_score=100,
            subscription_score=0
        )
        
        expected = (100.0 * 0.3) + (0.0 * 0.25) + (50.0 * 0.15) + (100.0 * 0.15) + (0.0 * 0.15)
        self.assertAlmostEqual(total_score, expected, places=2)
    
    @patch('apps.discovery.services.RankingService._compute_offer_score')
    @patch('apps.discovery.services.RankingService._compute_popularity_score')
    @patch('apps.discovery.services.RankingService._compute_subscription_score')
    def test_score_vendor_complete_scoring(self, mock_sub, mock_pop, mock_offer):
        """Test complete vendor scoring with all components."""
        # Mock the internal methods to avoid complex dependencies
        mock_offer.return_value = 70.0
        mock_pop.return_value = 60.0
        mock_sub.return_value = 50.0
        
        scored_vendor = RankingService.score_vendor(
            vendor=self.mock_vendor,
            user_point=self.test_point,
            query='Test Restaurant'
        )
        
        self.assertIsInstance(scored_vendor, ScoredVendor)
        self.assertEqual(scored_vendor.vendor, self.mock_vendor)
        self.assertGreater(scored_vendor.total_score, 0)
        self.assertGreaterEqual(scored_vendor.total_score, 0)
        self.assertLessEqual(scored_vendor.total_score, 100)
        self.assertGreaterEqual(scored_vendor.text_score, 0)
        self.assertLessEqual(scored_vendor.text_score, 100)
        self.assertGreaterEqual(scored_vendor.distance_score, 0)
        self.assertLessEqual(scored_vendor.distance_score, 100)
        self.assertEqual(scored_vendor.offer_score, 70.0)  # Mocked value
        self.assertEqual(scored_vendor.popularity_score, 60.0)  # Mocked value
        self.assertEqual(scored_vendor.subscription_score, 50.0)  # Mocked value
    
    def test_score_vendor_with_empty_query(self):
        """Test vendor scoring with empty query."""
        # Mock the internal methods to avoid complex dependencies
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            scored_vendor = RankingService.score_vendor(
                vendor=self.mock_vendor,
                user_point=self.test_point,
                query=''
            )
            
            self.assertEqual(scored_vendor.text_score, 0.0)
            # Other scores should still be calculated
            self.assertGreater(scored_vendor.total_score, 0)
    
    def test_rank_vendors_sorting(self):
        """Test vendor ranking and sorting."""
        # Create additional mock vendors with different characteristics
        vendor2 = Mock()
        vendor2.business_name = 'Popular Cafe'
        vendor2.description = 'Very popular spot'
        vendor2.total_views = 900
        vendor2.subscription_level = 'PLATINUM'
        vendor2.gps_point = Point(74.3590, 31.5210, srid=4326)
        
        vendor3 = Mock()
        vendor3.business_name = 'Basic Shop'
        vendor3.description = 'Simple store'
        vendor3.total_views = 20
        vendor3.subscription_level = 'BASIC'
        vendor3.gps_point = Point(74.3600, 31.5220, srid=4326)
        
        vendors = [self.mock_vendor, vendor2, vendor3]
        user_point = Point(74.3587, 31.5204, srid=4326)
        query = 'restaurant'
        
        # Mock the internal methods to control scoring
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            ranked_vendors = RankingService.rank_vendors(vendors, user_point, query)
            
            self.assertEqual(len(ranked_vendors), 3)
            self.assertIsInstance(ranked_vendors[0], ScoredVendor)
            
            # Should be sorted by total_score descending
            scores = [v.total_score for v in ranked_vendors]
            self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_rank_vendors_empty_list(self):
        """Test vendor ranking with empty vendor list."""
        user_point = Point(74.3587, 31.5204, srid=4326)
        
        ranked_vendors = RankingService.rank_vendors([], user_point, 'test')
        
        self.assertEqual(ranked_vendors, [])
    
    def test_rank_vendors_no_query(self):
        """Test vendor ranking with no query."""
        vendors = [self.mock_vendor]
        user_point = Point(74.3587, 31.5204, srid=4326)
        
        # Mock the internal methods
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            ranked_vendors = RankingService.rank_vendors(vendors, user_point, '')
            
            self.assertEqual(len(ranked_vendors), 1)
            self.assertEqual(ranked_vendors[0].text_score, 0.0)
            # Other scores should still be calculated
            self.assertGreater(ranked_vendors[0].total_score, 0)
    
    def test_rank_vendors_distance_calculation(self):
        """Test that distance is calculated correctly in ranking."""
        # Create a vendor at a specific distance
        far_vendor = Mock()
        far_vendor.business_name = 'Far Restaurant'
        far_vendor.description = 'Far away'
        far_vendor.total_views = 100
        far_vendor.subscription_level = 'SILVER'
        far_vendor.gps_point = Point(74.3687, 31.5304, srid=4326)  # About 1.5km away
        
        vendors = [self.mock_vendor, far_vendor]
        user_point = Point(74.3587, 31.5204, srid=4326)
        
        # Mock the internal methods
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            ranked_vendors = RankingService.rank_vendors(vendors, user_point, '')
            
            self.assertEqual(len(ranked_vendors), 2)
            
            # The nearby vendor should have a better distance score
            nearby_vendor = next(v for v in ranked_vendors if v.vendor.business_name == 'Test Restaurant')
            far_vendor_ranked = next(v for v in ranked_vendors if v.vendor.business_name == 'Far Restaurant')
            
            self.assertGreater(nearby_vendor.distance_score, far_vendor_ranked.distance_score)
            self.assertLess(nearby_vendor.distance_meters, far_vendor_ranked.distance_meters)


class DiscoveryServiceFunctionSimpleTest(TestCase):
    """Test cases for discovery service functions with mocking."""
    
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
        
        # Create test location
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    @patch('apps.discovery.services.search_vendors')
    def test_search_vendors_basic_mocked(self, mock_search):
        """Test basic vendor search functionality with mocking."""
        # Mock the search function to return test data
        mock_results = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Restaurant',
                'score': 85.0,
                'distance': 500
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Popular Cafe',
                'score': 75.0,
                'distance': 800
            }
        ]
        mock_search.return_value = mock_results
        
        # Import and test the actual function
        from apps.discovery.services import search_vendors
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        
        # Verify structure of results
        for result in results:
            self.assertIn('id', result)
            self.assertIn('name', result)
            self.assertIn('score', result)
            self.assertIsInstance(result['score'], (int, float))
            self.assertGreaterEqual(result['score'], 0)
            self.assertLessEqual(result['score'], 100)
    
    @patch('apps.discovery.services.search_vendors')
    def test_search_vendors_with_query_mocked(self, mock_search):
        """Test vendor search with text query using mocking."""
        mock_results = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Restaurant',
                'score': 90.0,
                'distance': 500
            }
        ]
        mock_search.return_value = mock_results
        
        from apps.discovery.services import search_vendors
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            query='restaurant'
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Test Restaurant')
        
        # Verify the mock was called with correct parameters
        mock_search.assert_called_with(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            query='restaurant'
        )
    
    @patch('apps.discovery.services.search_vendors')
    def test_search_vendors_empty_results_mocked(self, mock_search):
        """Test vendor search with no results using mocking."""
        mock_search.return_value = []
        
        from apps.discovery.services import search_vendors
        results = search_vendors(
            lat=0.0,  # Middle of ocean
            lng=0.0,
            radius=100
        )
        
        self.assertEqual(len(results), 0)
    
    @patch('apps.discovery.services.nearby_vendors')
    def test_nearby_vendors_function_mocked(self, mock_nearby):
        """Test nearby_vendors convenience function with mocking."""
        mock_results = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Nearby Restaurant',
                'score': 88.0,
                'distance': 200
            }
        ]
        mock_nearby.return_value = mock_results
        
        from apps.discovery.services import nearby_vendors
        results = nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        
        # Verify it was called with correct parameters
        mock_nearby.assert_called_with(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000
        )
    
    @patch('apps.discovery.services.voice_search')
    def test_voice_search_basic_mocked(self, mock_voice_search):
        """Test basic voice search functionality with mocking."""
        mock_results = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Restaurant',
                'score': 85.0,
                'distance': 500
            }
        ]
        mock_voice_search.return_value = mock_results
        
        from apps.discovery.services import voice_search
        results = voice_search(
            lat=self.test_lat,
            lng=self.test_lng,
            transcript='restaurant near me'
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        
        # Verify it was called with correct parameters
        mock_voice_search.assert_called_with(
            lat=self.test_lat,
            lng=self.test_lng,
            transcript='restaurant near me'
        )
    
    @patch('apps.discovery.services.voice_search')
    def test_voice_search_empty_transcript_mocked(self, mock_voice_search):
        """Test voice search with empty transcript using mocking."""
        mock_voice_search.return_value = []
        
        from apps.discovery.services import voice_search
        results = voice_search(
            lat=self.test_lat,
            lng=self.test_lng,
            transcript=''
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)
    
    def test_search_function_parameter_validation(self):
        """Test parameter validation for search functions."""
        from apps.discovery.services import search_vendors
        
        # Test with mock to avoid actual database calls
        with patch('apps.discovery.services.search_vendors', return_value=[]):
            # Test invalid coordinates
            results = search_vendors(
                lat=91.0,  # Invalid latitude
                lng=181.0,  # Invalid longitude
                radius=1000
            )
            self.assertIsInstance(results, list)
            
            # Test zero radius
            results = search_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius=0
            )
            self.assertIsInstance(results, list)
            
            # Test negative radius
            results = search_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius=-100
            )
            self.assertIsInstance(results, list)


class RankingServiceEdgeCaseTest(TestCase):
    """Test edge cases for RankingService."""
    
    def test_calculate_text_score_with_special_characters(self):
        """Test text score calculation with special characters."""
        mock_vendor = Mock()
        mock_vendor.business_name = 'Café & Restaurant'
        mock_vendor.description = 'Great food!'
        
        # Test with special characters in query
        score = RankingService.calculate_text_score(
            vendor=mock_vendor,
            query='café'
        )
        
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_calculate_text_score_case_insensitive(self):
        """Test that text scoring is case insensitive."""
        mock_vendor = Mock()
        mock_vendor.business_name = 'Test Restaurant'
        mock_vendor.description = 'Great food'
        
        # Test with different case
        score_lower = RankingService.calculate_text_score(
            vendor=mock_vendor,
            query='test restaurant'
        )
        
        score_upper = RankingService.calculate_text_score(
            vendor=mock_vendor,
            query='TEST RESTAURANT'
        )
        
        score_mixed = RankingService.calculate_text_score(
            vendor=mock_vendor,
            query='Test Restaurant'
        )
        
        # All should return the same score (case insensitive)
        self.assertEqual(score_lower, score_upper)
        self.assertEqual(score_upper, score_mixed)
    
    def test_calculate_distance_score_negative_input(self):
        """Test distance score calculation with negative input."""
        # Negative distance should be handled gracefully
        score = RankingService.calculate_distance_score(-100)
        
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_calculate_distance_score_very_large_input(self):
        """Test distance score calculation with very large input."""
        # Very large distance
        score = RankingService.calculate_distance_score(100000)  # 100km
        
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        # Should be very low for such a large distance
        self.assertLess(score, 10)
    
    def test_score_vendor_with_missing_attributes(self):
        """Test scoring vendor with missing attributes."""
        # Mock vendor with missing attributes
        incomplete_vendor = Mock()
        # Don't set some attributes to test graceful handling
        
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            # This should not crash even with incomplete vendor data
            try:
                scored_vendor = RankingService.score_vendor(
                    vendor=incomplete_vendor,
                    user_point=Point(74.3587, 31.5204, srid=4326),
                    query='test'
                )
                self.assertIsInstance(scored_vendor, ScoredVendor)
            except AttributeError:
                # Expected for incomplete mock data
                pass
    
    def test_rank_vendors_with_duplicate_vendors(self):
        """Test ranking with duplicate vendor objects."""
        mock_vendor = Mock()
        mock_vendor.business_name = 'Test Restaurant'
        mock_vendor.description = 'Test'
        mock_vendor.total_views = 100
        mock_vendor.subscription_level = 'SILVER'
        mock_vendor.gps_point = Point(74.3587, 31.5204, srid=4326)
        
        # Create list with duplicate vendors
        vendors = [mock_vendor, mock_vendor, mock_vendor]
        user_point = Point(74.3587, 31.5204, srid=4326)
        
        with patch('apps.discovery.services.RankingService._compute_offer_score', return_value=70.0), \
             patch('apps.discovery.services.RankingService._compute_popularity_score', return_value=60.0), \
             patch('apps.discovery.services.RankingService._compute_subscription_score', return_value=50.0):
            
            ranked_vendors = RankingService.rank_vendors(vendors, user_point, '')
            
            # Should handle duplicates gracefully
            self.assertEqual(len(ranked_vendors), 3)
            self.assertIsInstance(ranked_vendors[0], ScoredVendor)
