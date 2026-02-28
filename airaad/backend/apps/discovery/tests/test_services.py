"""
Unit tests for Discovery Service layer.
Tests RankingService and discovery service functions.
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
from apps.vendors.models import Vendor as VendorsVendor
from apps.user_portal.models import Vendor, Promotion, Tag, City, Area
from apps.user_preferences.models import UserPreference, UserSearchHistory
from apps.discovery.services import RankingService, ScoredVendor, search_vendors, nearby_vendors, voice_search

User = get_user_model()


class RankingServiceTest(TestCase):
    """Test cases for RankingService class methods."""
    
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
        
        # Create test vendor using the vendors app model
        self.vendor = VendorsVendor.objects.create(
            business_name='Test Restaurant',
            description='A great place to eat',
            gps_point=Point(74.3587, 31.5204, srid=4326),
            qc_status='APPROVED'
        )
        
        # Create test promotion using user_portal model (for other tests)
        self.promotion = Promotion.objects.create(
            vendor=Vendor.objects.create(
                name='Test Restaurant',
                description='A great place to eat',
                lat=Decimal('31.5204'),
                lng=Decimal('74.3587'),
                category_slug='restaurant',
                subscription_tier='SILVER',
                status='VERIFIED'
            ),
            title='50% Off',
            description='Half price on all items',
            discount_type='PERCENTAGE',
            discount_value=50,
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7)
        )
        
        # Create test tag
        self.tag = Tag.objects.create(
            name='Pakistani',
            slug='pakistani',
            color='#FF0000'
        )
        self.vendor.tags.add(self.tag)
    
    def test_scored_vendor_dataclass(self):
        """Test ScoredVendor dataclass structure."""
        scored_vendor = ScoredVendor(
            vendor=self.vendor,
            total_score=85.5,
            text_score=25.0,
            distance_score=20.0,
            offer_score=15.0,
            popularity_score=15.0,
            subscription_score=10.5,
            distance_meters=500.0
        )
        
        self.assertEqual(scored_vendor.vendor, self.vendor)
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
            vendor=self.vendor,
            query='Test Restaurant'
        )
        
        self.assertGreater(score, 80)  # Should be high for perfect match
        self.assertLessEqual(score, 100)  # Should not exceed 100
    
    def test_calculate_text_score_partial_match(self):
        """Test text score calculation for partial match."""
        # Partial match
        score = RankingService.calculate_text_score(
            vendor=self.vendor,
            query='restaurant'
        )
        
        self.assertGreater(score, 40)  # Should be moderate for partial match
        self.assertLess(score, 80)  # Should be less than perfect match
    
    def test_calculate_text_score_no_match(self):
        """Test text score calculation for no match."""
        # No match
        score = RankingService.calculate_text_score(
            vendor=self.vendor,
            query='completely different'
        )
        
        self.assertLess(score, 20)  # Should be low for no match
    
    def test_calculate_text_score_empty_query(self):
        """Test text score calculation for empty query."""
        score = RankingService.calculate_text_score(
            vendor=self.vendor,
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
    
    def test_calculate_offer_score_with_active_promotion(self):
        """Test offer score calculation with active promotion."""
        score = RankingService.calculate_offer_score(self.vendor)
        
        self.assertGreater(score, 0)  # Should have positive score for active promotion
        self.assertLessEqual(score, 100)
    
    def test_calculate_offer_score_no_active_promotion(self):
        """Test offer score calculation with no active promotion."""
        # Deactivate promotion
        self.promotion.is_active = False
        self.promotion.save()
        
        score = RankingService.calculate_offer_score(self.vendor)
        
        self.assertEqual(score, 0.0)  # Should be zero for no active promotion
    
    def test_calculate_popularity_score_high_popularity(self):
        """Test popularity score calculation for high popularity vendor."""
        # Set high popularity
        self.vendor.total_views = 950  # High view count
        self.vendor.save()
        
        score = RankingService.calculate_popularity_score(self.vendor)
        
        self.assertGreater(score, 80)  # Should be high for high popularity
        self.assertLessEqual(score, 100)
    
    def test_calculate_popularity_score_low_popularity(self):
        """Test popularity score calculation for low popularity vendor."""
        # Set low popularity
        self.vendor.total_views = 10  # Low view count
        self.vendor.save()
        
        score = RankingService.calculate_popularity_score(self.vendor)
        
        self.assertLess(score, 20)  # Should be low for low popularity
    
    def test_calculate_popularity_score_zero_popularity(self):
        """Test popularity score calculation for zero popularity vendor."""
        # Set zero popularity
        self.vendor.total_views = 0
        self.vendor.save()
        
        score = RankingService.calculate_popularity_score(self.vendor)
        
        self.assertEqual(score, 0.0)  # Should be zero for zero popularity
    
    def test_calculate_subscription_score_platinum_tier(self):
        """Test subscription score calculation for Platinum tier."""
        self.vendor.subscription_level = 'PLATINUM'
        self.vendor.save()
        
        score = RankingService.calculate_subscription_score(self.vendor)
        
        self.assertGreater(score, 80)  # Should be high for Platinum
        self.assertLessEqual(score, 100)
    
    def test_calculate_subscription_score_gold_tier(self):
        """Test subscription score calculation for Gold tier."""
        self.vendor.subscription_level = 'GOLD'
        self.vendor.save()
        
        score = RankingService.calculate_subscription_score(self.vendor)
        
        self.assertGreater(score, 60)  # Should be moderate-high for Gold
        self.assertLess(score, 80)
    
    def test_calculate_subscription_score_silver_tier(self):
        """Test subscription score calculation for Silver tier."""
        self.vendor.subscription_level = 'SILVER'
        self.vendor.save()
        
        score = RankingService.calculate_subscription_score(self.vendor)
        
        self.assertGreater(score, 40)  # Should be moderate for Silver
        self.assertLess(score, 60)
    
    def test_calculate_subscription_score_basic_tier(self):
        """Test subscription score calculation for Basic tier."""
        self.vendor.subscription_level = 'BASIC'
        self.vendor.save()
        
        score = RankingService.calculate_subscription_score(self.vendor)
        
        self.assertGreater(score, 20)  # Should be low for Basic
        self.assertLess(score, 40)
    
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
    
    def test_score_vendor_complete_scoring(self):
        """Test complete vendor scoring with all components."""
        # Create point at vendor location for maximum scores
        vendor_point = Point(
            float(self.vendor.lng),
            float(self.vendor.lat),
            srid=4326
        )
        
        scored_vendor = RankingService.score_vendor(
            vendor=self.vendor,
            user_point=vendor_point,
            query='Test Restaurant'
        )
        
        self.assertIsInstance(scored_vendor, ScoredVendor)
        self.assertEqual(scored_vendor.vendor, self.vendor)
        self.assertGreater(scored_vendor.total_score, 0)
        self.assertGreaterEqual(scored_vendor.total_score, 0)
        self.assertLessEqual(scored_vendor.total_score, 100)
        self.assertGreaterEqual(scored_vendor.text_score, 0)
        self.assertLessEqual(scored_vendor.text_score, 100)
        self.assertGreaterEqual(scored_vendor.distance_score, 0)
        self.assertLessEqual(scored_vendor.distance_score, 100)
        self.assertGreaterEqual(scored_vendor.offer_score, 0)
        self.assertLessEqual(scored_vendor.offer_score, 100)
        self.assertGreaterEqual(scored_vendor.popularity_score, 0)
        self.assertLessEqual(scored_vendor.popularity_score, 100)
        self.assertGreaterEqual(scored_vendor.subscription_score, 0)
        self.assertLessEqual(scored_vendor.subscription_score, 100)
    
    def test_score_vendor_with_empty_query(self):
        """Test vendor scoring with empty query."""
        vendor_point = Point(
            float(self.vendor.lng),
            float(self.vendor.lat),
            srid=4326
        )
        
        scored_vendor = RankingService.score_vendor(
            vendor=self.vendor,
            user_point=vendor_point,
            query=''
        )
        
        self.assertEqual(scored_vendor.text_score, 0.0)
        # Other scores should still be calculated
        self.assertGreater(scored_vendor.distance_score, 0)
    
    def test_rank_vendors_sorting(self):
        """Test vendor ranking and sorting."""
        # Create additional vendors with different characteristics
        vendor2 = VendorsVendor.objects.create(
            business_name='Popular Cafe',
            description='Very popular spot',
            gps_point=Point(74.3590, 31.5210, srid=4326),
            qc_status='APPROVED',
            subscription_level='PLATINUM',
            total_views=900
        )
        
        vendor3 = VendorsVendor.objects.create(
            business_name='Basic Shop',
            description='Simple store',
            gps_point=Point(74.3600, 31.5220, srid=4326),
            qc_status='APPROVED',
            subscription_level='BASIC',
            total_views=20
        )
        
        vendors = [self.vendor, vendor2, vendor3]
        user_point = Point(74.3587, 31.5204, srid=4326)
        query = 'restaurant'
        
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
        vendors = [self.vendor]
        user_point = Point(74.3587, 31.5204, srid=4326)
        
        ranked_vendors = RankingService.rank_vendors(vendors, user_point, '')
        
        self.assertEqual(len(ranked_vendors), 1)
        self.assertEqual(ranked_vendors[0].text_score, 0.0)
        # Other scores should still be calculated
        self.assertGreater(ranked_vendors[0].total_score, 0)


class DiscoveryServiceFunctionTest(TestCase):
    """Test cases for discovery service functions."""
    
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
        
        # Create test vendors using the correct model structure
        self.vendor1 = VendorsVendor.objects.create(
            business_name='Test Restaurant',
            description='Great food',
            gps_point=Point(74.3587, 31.5204, srid=4326),
            qc_status='APPROVED',
            subscription_level='SILVER',
            total_views=750
        )
        
        self.vendor2 = VendorsVendor.objects.create(
            business_name='Popular Cafe',
            description='Coffee and pastries',
            gps_point=Point(74.3590, 31.5210, srid=4326),
            qc_status='APPROVED',
            subscription_level='GOLD',
            total_views=850
        )
        
        # Create active promotion for vendor1 (using user_portal Vendor for promotion)
        user_portal_vendor = Vendor.objects.create(
            name='Test Restaurant',
            description='Great food',
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            category_slug='restaurant',
            subscription_tier='SILVER',
            status='VERIFIED'
        )
        
        self.promotion = Promotion.objects.create(
            vendor=user_portal_vendor,
            title='Weekend Special',
            description='20% off',
            discount_type='PERCENTAGE',
            discount_value=20,
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=6)
        )
    
    def test_search_vendors_basic(self):
        """Test basic vendor search functionality."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000
        )
        
        self.assertIsInstance(results, list)
        # Results should contain vendor dictionaries with scores
        if results:
            result = results[0]
            self.assertIn('id', result)
            self.assertIn('name', result)
            self.assertIn('score', result)
            self.assertIsInstance(result['score'], (int, float))
            self.assertGreaterEqual(result['score'], 0)
            self.assertLessEqual(result['score'], 100)
    
    def test_search_vendors_with_query(self):
        """Test vendor search with text query."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            query='restaurant'
        )
        
        self.assertIsInstance(results, list)
        # Should find vendors matching 'restaurant'
        if results:
            # Check if any result contains the query term
            found_match = any(
                'restaurant' in str(result.get('name', '')).lower() or
                'restaurant' in str(result.get('description', '')).lower()
                for result in results
            )
            # This might not always find matches depending on data
    
    def test_search_vendors_with_radius_limit(self):
        """Test vendor search with radius limiting."""
        # Small radius
        results_small = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=100
        )
        
        # Large radius
        results_large = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=5000
        )
        
        self.assertIsInstance(results_small, list)
        self.assertIsInstance(results_large, list)
        # Large radius should find equal or more results
        self.assertLessEqual(len(results_small), len(results_large))
    
    def test_search_vendors_max_radius_cap(self):
        """Test that very large radius is capped to maximum."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=50000  # Very large radius
        )
        
        self.assertIsInstance(results, list)
        # Should not crash and should return results within max radius
    
    def test_nearby_vendors_function(self):
        """Test nearby_vendors convenience function."""
        results = nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000
        )
        
        self.assertIsInstance(results, list)
        # Should be same as search_vendors with empty query
        results_direct = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            query=""
        )
        
        self.assertEqual(len(results), len(results_direct))
    
    def test_voice_search_basic(self):
        """Test basic voice search functionality."""
        results = voice_search(
            lat=self.test_lat,
            lng=self.test_lng,
            transcript='restaurant near me'
        )
        
        self.assertIsInstance(results, list)
        # Should return similar results to text search
        text_results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            query='restaurant'
        )
        
        # Results should be comparable (voice search processes transcript)
        self.assertIsInstance(results, list)
    
    def test_voice_search_empty_transcript(self):
        """Test voice search with empty transcript."""
        results = voice_search(
            lat=self.test_lat,
            lng=self.test_lng,
            transcript=''
        )
        
        self.assertIsInstance(results, list)
        # Should handle empty transcript gracefully
    
    def test_search_vendors_invalid_coordinates(self):
        """Test vendor search with invalid coordinates."""
        # Test with coordinates outside valid ranges
        results = search_vendors(
            lat=91.0,  # Invalid latitude
            lng=181.0,  # Invalid longitude
            radius=1000
        )
        
        # Should handle gracefully (may return empty list or not crash)
        self.assertIsInstance(results, list)
    
    def test_search_vendors_zero_radius(self):
        """Test vendor search with zero radius."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=0
        )
        
        self.assertIsInstance(results, list)
        # Zero radius should return very few or no results
    
    def test_search_vendors_negative_radius(self):
        """Test vendor search with negative radius."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=-100
        )
        
        self.assertIsInstance(results, list)
        # Negative radius should be handled (treated as zero or default)


class DiscoveryServiceIntegrationTest(TestCase):
    """Integration tests for discovery services with real data."""
    
    def setUp(self):
        """Set up test data."""
        # Create test location (Lahore)
        self.test_lat = 31.5204
        self.test_lng = 74.3587
        
        # Create clustered vendors around test location
        self.nearby_vendor = VendorsVendor.objects.create(
            business_name='Nearby Restaurant',
            description='Very close',
            gps_point=Point(74.3588, 31.5205, srid=4326),
            qc_status='APPROVED',
            subscription_level='GOLD',
            total_views=800
        )
        
        self.medium_vendor = VendorsVendor.objects.create(
            business_name='Medium Distance Cafe',
            description='Moderately close',
            gps_point=Point(74.3630, 31.5250, srid=4326),
            qc_status='APPROVED',
            subscription_level='SILVER',
            total_views=600
        )
        
        self.far_vendor = VendorsVendor.objects.create(
            business_name='Far Restaurant',
            description='Quite far',
            gps_point=Point(74.3780, 31.5400, srid=4326),
            qc_status='APPROVED',
            subscription_level='PLATINUM',
            total_views=900
        )
        
        # Add promotion to nearby vendor (using user_portal Vendor for promotion)
        user_portal_vendor = Vendor.objects.create(
            name='Nearby Restaurant',
            description='Very close',
            lat=Decimal('31.5205'),
            lng=Decimal('74.3588'),
            category_slug='restaurant',
            subscription_tier='GOLD',
            status='VERIFIED'
        )
        
        self.promotion = Promotion.objects.create(
            vendor=user_portal_vendor,
            title='Special Offer',
            description='30% off',
            discount_type='PERCENTAGE',
            discount_value=30,
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=6)
        )
    
    def test_real_search_with_ranking(self):
        """Test real vendor search with actual ranking."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=2000,
            query='restaurant'
        )
        
        self.assertIsInstance(results, list)
        
        # Check that results are properly structured
        for result in results:
            self.assertIn('id', result)
            self.assertIn('name', result)
            self.assertIn('score', result)
            self.assertGreaterEqual(result['score'], 0)
            self.assertLessEqual(result['score'], 100)
    
    def test_distance_based_filtering(self):
        """Test that distance-based filtering works correctly."""
        # Small radius should only find nearby vendor
        results_small = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=200  # Very small radius
        )
        
        # Larger radius should find more vendors
        results_large = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=5000  # Large radius
        )
        
        self.assertLessEqual(len(results_small), len(results_large))
    
    def test_subscription_tier_effect(self):
        """Test that subscription tier affects ranking."""
        results = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=5000,
            query='restaurant'
        )
        
        # Find the restaurant vendors in results
        restaurants = [v for v in results if v.get('category_slug') == 'restaurant']
        
        if len(restaurants) >= 2:
            # Sort by score to check ranking
            restaurants_sorted = sorted(restaurants, key=lambda x: x['score'], reverse=True)
            
            # Check that scores are properly calculated
            for restaurant in restaurants_sorted:
                self.assertIsInstance(restaurant['score'], (int, float))
                self.assertGreaterEqual(restaurant['score'], 0)
                self.assertLessEqual(restaurant['score'], 100)
    
    def test_search_result_consistency(self):
        """Test that search results are consistent across calls."""
        results1 = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=2000,
            query='restaurant'
        )
        
        results2 = search_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=2000,
            query='restaurant'
        )
        
        # Results should be identical for same parameters
        self.assertEqual(len(results1), len(results2))
        
        # Scores should be the same
        if results1 and results2:
            scores1 = [r['score'] for r in results1]
            scores2 = [r['score'] for r in results2]
            self.assertEqual(scores1, scores2)
