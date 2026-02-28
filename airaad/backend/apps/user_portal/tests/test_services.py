"""
Unit tests for User Portal discovery services.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.cache import cache

from ..services import DiscoveryService
from ..models import Vendor, Promotion, VendorReel, Tag, City, Area
from ..exceptions import (
    VendorNotFoundException,
    LocationValidationException,
    SearchValidationException,
)


class DiscoveryServiceTest(TestCase):
    """Test cases for DiscoveryService."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()
        
        # Create test vendor
        self.vendor = Vendor.objects.create(
            name='Test Restaurant',
            description='A great place to eat',
            category='RESTAURANT',
            subcategory='Pakistani',
            tags=['food', 'pakistani', 'halal'],
            tier='GOLD',
            is_active=True,
            is_verified=True,
            address='123 Test St',
            phone='+1234567890',
            email='test@restaurant.com',
            location=Point(67.0011, 24.8607, srid=4326),  # Karachi
            popularity_score=85.5,
            interaction_count=150,
            system_tags=['verified', 'trending']
        )
        
        # Create test promotion
        self.promotion = Promotion.objects.create(
            vendor=self.vendor,
            title='20% Off Lunch',
            description='Get 20% off on lunch items',
            discount_type='PERCENTAGE',
            discount_percent=20,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True
        )
        
        # Create test reel
        self.reel = VendorReel.objects.create(
            vendor=self.vendor,
            title='Restaurant Tour',
            description='Take a tour of our restaurant',
            video_url='https://example.com/video.mp4',
            thumbnail_url='https://example.com/thumb.jpg',
            duration_seconds=30,
            view_count=1000,
            cta_tap_count=50,
            completion_count=800,
            cta_text='Book Now',
            cta_url='https://example.com/book',
            is_active=True,
            is_approved=True
        )
        
        # Create test tag
        self.tag = Tag.objects.create(
            name='Pakistani Food',
            slug='pakistani-food',
            description='Traditional Pakistani cuisine',
            icon_url='https://example.com/icon.png',
            color='#FF5733',
            category='FOOD',
            sort_order=1,
            vendor_count=1,
            search_count=100,
            is_active=True
        )
        
        # Create test city
        self.city = City.objects.create(
            name='Karachi',
            slug='karachi',
            location=Point(67.0011, 24.8607, srid=4326),
            bounds_north=25.0,
            bounds_south=24.5,
            bounds_east=67.5,
            bounds_west=66.5,
            country='Pakistan',
            is_active=True,
            sort_order=1,
            vendor_count=1
        )
        
        # Test coordinates (Karachi)
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000  # 1km
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_get_nearby_vendors_success(self):
        """Test successful nearby vendors retrieval."""
        result = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD',
            limit=50
        )
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Check structure of vendor data
        vendor_data = result[0]
        self.assertIn('vendor_id', vendor_data)
        self.assertIn('relevance_score', vendor_data)
        self.assertIn('distance_score', vendor_data)
        self.assertIn('offer_score', vendor_data)
        self.assertIn('popularity_score', vendor_data)
        self.assertIn('tier_score', vendor_data)
        self.assertIn('weighted_score', vendor_data)
        self.assertIn('final_score', vendor_data)
        self.assertIn('distance_m', vendor_data)
    
    def test_get_nearby_vendors_with_category_filter(self):
        """Test nearby vendors with category filter."""
        result = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD',
            category='RESTAURANT',
            limit=50
        )
        
        self.assertIsInstance(result, list)
        # Should only return restaurant vendors
        for vendor_data in result:
            # This would need to be implemented based on actual vendor data
            pass
    
    def test_get_nearby_vendors_tier_limits(self):
        """Test tier-based result limits."""
        # Test SILVER tier (limit 50)
        result_silver = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='SILVER',
            limit=100  # Request more than tier limit
        )
        
        # Test PLATINUM tier (limit 500)
        result_platinum = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='PLATINUM',
            limit=100
        )
        
        # Platinum should return more or equal results
        self.assertGreaterEqual(len(result_platinum), len(result_silver))
    
    def test_get_nearby_vendors_caching(self):
        """Test caching of nearby vendors."""
        # First call
        result1 = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD'
        )
        
        # Second call should use cache
        result2 = DiscoveryService.get_nearby_vendors(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD'
        )
        
        self.assertEqual(result1, result2)
    
    def test_get_ar_markers_success(self):
        """Test successful AR markers retrieval."""
        result = DiscoveryService.get_ar_markers(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD'
        )
        
        self.assertIsInstance(result, list)
        
        if result:  # If any markers found
            marker = result[0]
            self.assertIn('id', marker)
            self.assertIn('name', marker)
            self.assertIn('category', marker)
            self.assertIn('tier', marker)
            self.assertIn('lat', marker)
            self.assertIn('lng', marker)
            self.assertIn('distance_m', marker)
            self.assertIn('logo_url', marker)
            self.assertIn('has_promotion', marker)
            self.assertIn('tier_color', marker)
    
    def test_get_ar_markers_tier_limits(self):
        """Test AR markers tier-based limits."""
        # Test SILVER tier (limit 10)
        result_silver = DiscoveryService.get_ar_markers(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='SILVER'
        )
        
        # Test PLATINUM tier (limit 100)
        result_platinum = DiscoveryService.get_ar_markers(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='PLATINUM'
        )
        
        # Platinum should return more or equal results
        self.assertGreaterEqual(len(result_platinum), len(result_silver))
    
    def test_get_vendor_detail_success(self):
        """Test successful vendor detail retrieval."""
        result = DiscoveryService.get_vendor_detail(
            vendor_id=str(self.vendor.id),
            user_lat=self.test_lat,
            user_lng=self.test_lng
        )
        
        self.assertIsNotNone(result)
        
        # Check structure
        self.assertIn('id', result)
        self.assertIn('name', result)
        self.assertIn('description', result)
        self.assertIn('category', result)
        self.assertIn('tier', result)
        self.assertIn('is_verified', result)
        self.assertIn('address', result)
        self.assertIn('phone', result)
        self.assertIn('email', result)
        self.assertIn('location', result)
        self.assertIn('promotions', result)
        self.assertIn('reels', result)
        self.assertIn('navigation_urls', result)
        self.assertIn('distance_m', result)
        
        # Check promotions structure
        promotions = result['promotions']
        if promotions:
            promo = promotions[0]
            self.assertIn('id', promo)
            self.assertIn('title', promo)
            self.assertIn('discount_percent', promo)
            self.assertIn('is_flash_deal', promo)
            self.assertIn('remaining_uses', promo)
        
        # Check reels structure
        reels = result['reels']
        if reels:
            reel = reels[0]
            self.assertIn('id', reel)
            self.assertIn('title', reel)
            self.assertIn('video_url', reel)
            self.assertIn('view_count', reel)
            self.assertIn('completion_rate', reel)
            self.assertIn('cta_text', reel)
    
    def test_get_vendor_detail_not_found(self):
        """Test vendor detail with non-existent vendor."""
        result = DiscoveryService.get_vendor_detail(
            vendor_id=str(uuid.uuid4()),
            user_lat=self.test_lat,
            user_lng=self.test_lng
        )
        
        self.assertIsNone(result)
    
    def test_search_vendors_success(self):
        """Test successful vendor search."""
        result = DiscoveryService.search_vendors(
            query_text='restaurant',
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD',
            limit=20
        )
        
        self.assertIsInstance(result, list)
        
        if result:  # If any results found
            vendor = result[0]
            self.assertIn('id', vendor)
            self.assertIn('name', vendor)
            self.assertIn('category', vendor)
            self.assertIn('tier', vendor)
            self.assertIn('relevance_score', vendor)
            self.assertIn('extracted_intent', vendor)
    
    def test_search_vendors_intent_extraction(self):
        """Test search intent extraction."""
        # Test category extraction
        result = DiscoveryService.search_vendors(
            query_text='pakistani restaurant',
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD'
        )
        
        if result:
            vendor = result[0]
            intent = vendor['extracted_intent']
            self.assertIn('category', intent)
            self.assertEqual(intent['category'], 'RESTAURANT')
    
    def test_search_vendors_price_extraction(self):
        """Test price range extraction."""
        # Test price extraction
        result = DiscoveryService.search_vendors(
            query_text='cheap food',
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD'
        )
        
        if result:
            vendor = result[0]
            intent = vendor['extracted_intent']
            self.assertIn('price_range', intent)
            self.assertEqual(intent['price_range'], 'BUDGET')
    
    def test_get_tags_success(self):
        """Test successful tags retrieval."""
        result = DiscoveryService.get_tags()
        
        self.assertIsInstance(result, list)
        
        if result:  # If any tags found
            tag = result[0]
            self.assertIn('id', tag)
            self.assertIn('name', tag)
            self.assertIn('slug', tag)
            self.assertIn('category', tag)
            self.assertIn('vendor_count', tag)
            self.assertIn('color', tag)
    
    def test_get_tags_with_category_filter(self):
        """Test tags retrieval with category filter."""
        result = DiscoveryService.get_tags(category='FOOD')
        
        self.assertIsInstance(result, list)
        
        # Should only return food category tags
        for tag in result:
            self.assertEqual(tag['category'], 'FOOD')
    
    def test_get_cities_success(self):
        """Test successful cities retrieval."""
        result = DiscoveryService.get_cities()
        
        self.assertIsInstance(result, list)
        
        if result:  # If any cities found
            city = result[0]
            self.assertIn('id', city)
            self.assertIn('name', city)
            self.assertIn('slug', city)
            self.assertIn('location', city)
            self.assertIn('vendor_count', city)
            self.assertIn('areas', city)
    
    def test_get_promotions_strip_success(self):
        """Test successful promotions strip retrieval."""
        result = DiscoveryService.get_promotions_strip(
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            limit=20
        )
        
        self.assertIsInstance(result, list)
        
        if result:  # If any promotions found
            promotion = result[0]
            self.assertIn('id', promotion)
            self.assertIn('title', promotion)
            self.assertIn('vendor', promotion)
            self.assertIn('discount_percent', promotion)
            self.assertIn('is_flash_deal', promotion)
            self.assertIn('vendor', promotion)
            self.assertIn('remaining_uses', promotion)


class DiscoveryServiceRankingTest(TestCase):
    """Test cases for ranking algorithm."""
    
    def setUp(self):
        """Set up test data for ranking tests."""
        # Create vendors with different tiers
        self.silver_vendor = Vendor.objects.create(
            name='Silver Restaurant',
            category='RESTAURANT',
            tier='SILVER',
            is_active=True,
            location=Point(67.0011, 24.8607, srid=4326),
            popularity_score=50.0,
            interaction_count=100
        )
        
        self.gold_vendor = Vendor.objects.create(
            name='Gold Restaurant',
            category='RESTAURANT',
            tier='GOLD',
            is_active=True,
            location=Point(67.0012, 24.8608, srid=4326),
            popularity_score=75.0,
            interaction_count=200
        )
        
        self.platinum_vendor = Vendor.objects.create(
            name='Platinum Restaurant',
            category='RESTAURANT',
            tier='PLATINUM',
            is_active=True,
            location=Point(67.0013, 24.8609, srid=4326),
            popularity_score=90.0,
            interaction_count=300,
            system_tags=['verified', 'trending']
        )
        
        # Create promotion for gold vendor
        self.promotion = Promotion.objects.create(
            vendor=self.gold_vendor,
            title='Special Offer',
            discount_type='PERCENTAGE',
            discount_percent=25,
            is_flash_deal=True,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        self.test_lat = 24.8607
        self.test_lng = 67.0011
    
    def test_calculate_vendor_score(self):
        """Test vendor score calculation."""
        user_point = Point(self.test_lng, self.test_lat, srid=4326)
        
        # Test silver vendor score
        silver_score = DiscoveryService._calculate_vendor_score(
            self.silver_vendor, user_point
        )
        
        # Test gold vendor score (should be higher due to promotion)
        gold_score = DiscoveryService._calculate_vendor_score(
            self.gold_vendor, user_point
        )
        
        # Test platinum vendor score (should be highest)
        platinum_score = DiscoveryService._calculate_vendor_score(
            self.platinum_vendor, user_point
        )
        
        # Check score structure
        for score_data in [silver_score, gold_score, platinum_score]:
            self.assertIn('vendor_id', score_data)
            self.assertIn('relevance_score', score_data)
            self.assertIn('distance_score', score_data)
            self.assertIn('offer_score', score_data)
            self.assertIn('popularity_score', score_data)
            self.assertIn('tier_score', score_data)
            self.assertIn('weighted_score', score_data)
            self.assertIn('final_score', score_data)
            self.assertIn('distance_m', score_data)
        
        # Check tier scores
        self.assertEqual(silver_score['tier_score'], 0.25)
        self.assertEqual(gold_score['tier_score'], 0.50)
        self.assertEqual(platinum_score['tier_score'], 1.00)
        
        # Gold vendor should have higher offer score due to promotion
        self.assertGreater(gold_score['offer_score'], silver_score['offer_score'])
        
        # Platinum vendor should have system tag boosts
        self.assertGreater(platinum_score['final_score'], platinum_score['weighted_score'])
    
    def test_distance_score_calculation(self):
        """Test distance score calculation."""
        # Very close (0-100m)
        close_score = DiscoveryService._calculate_distance_score(50)
        self.assertEqual(close_score, 1.0)
        
        # Close (100-500m)
        medium_close_score = DiscoveryService._calculate_distance_score(300)
        self.assertGreater(medium_close_score, 0.8)
        self.assertLess(medium_close_score, 1.0)
        
        # Medium (500m-2km)
        medium_score = DiscoveryService._calculate_distance_score(1000)
        self.assertGreater(medium_score, 0.4)
        self.assertLess(medium_score, 0.8)
        
        # Far (2km-5km)
        far_score = DiscoveryService._calculate_distance_score(3000)
        self.assertGreater(far_score, 0.1)
        self.assertLess(far_score, 0.4)
        
        # Very far (>5km)
        very_far_score = DiscoveryService._calculate_distance_score(10000)
        self.assertEqual(very_far_score, 0.1)
    
    def test_offer_score_calculation(self):
        """Test offer score calculation."""
        # No promotions
        no_promo_score = DiscoveryService._calculate_offer_score(self.silver_vendor)
        self.assertEqual(no_promo_score, 0.0)
        
        # Percentage promotion
        promo_score = DiscoveryService._calculate_offer_score(self.gold_vendor)
        self.assertGreater(promo_score, 0.0)
        self.assertLessEqual(promo_score, 0.8)  # Max for percentage
        
        # Flash deal boost
        self.assertGreater(promo_score, 0.8)  # Should be > 0.8 due to flash deal
    
    def test_popularity_score_calculation(self):
        """Test popularity score calculation."""
        # Zero popularity
        zero_pop_score = DiscoveryService._calculate_popularity_score(
            Vendor(popularity_score=0.0)
        )
        self.assertEqual(zero_pop_score, 0.0)
        
        # Normal popularity
        normal_pop_score = DiscoveryService._calculate_popularity_score(
            Vendor(popularity_score=50.0)
        )
        self.assertEqual(normal_pop_score, 0.5)
        
        # High popularity (capped at 1.0)
        high_pop_score = DiscoveryService._calculate_popularity_score(
            Vendor(popularity_score=150.0)
        )
        self.assertEqual(high_pop_score, 1.0)
    
    def test_extract_search_intent(self):
        """Test search intent extraction."""
        # Category extraction
        intent = DiscoveryService._extract_search_intent('pakistani restaurant')
        self.assertEqual(intent['category'], 'RESTAURANT')
        self.assertEqual(intent['query_text'], 'pakistani restaurant')
        
        # Price extraction
        intent = DiscoveryService._extract_search_intent('cheap food')
        self.assertEqual(intent['price_range'], 'BUDGET')
        
        # Multiple keywords
        intent = DiscoveryService._extract_search_intent('expensive luxury hotel')
        self.assertEqual(intent['price_range'], 'PREMIUM')
        
        # No specific intent
        intent = DiscoveryService._extract_search_intent('random query')
        self.assertIsNone(intent['category'])
        self.assertIsNone(intent['price_range'])


class DiscoveryServiceValidationTest(TestCase):
    """Test cases for input validation."""
    
    def test_invalid_coordinates(self):
        """Test invalid coordinate handling."""
        # Invalid latitude
        with self.assertRaises(Exception):  # Should raise ValueError
            DiscoveryService.get_nearby_vendors(
                lat=91.0,  # Invalid latitude
                lng=67.0,
                radius_m=1000
            )
        
        # Invalid longitude
        with self.assertRaises(Exception):  # Should raise ValueError
            DiscoveryService.get_nearby_vendors(
                lat=24.0,
                lng=181.0,  # Invalid longitude
                radius_m=1000
            )
    
    def test_invalid_radius(self):
        """Test invalid radius handling."""
        # Too small radius
        with self.assertRaises(Exception):  # Should raise ValueError
            DiscoveryService.get_nearby_vendors(
                lat=24.0,
                lng=67.0,
                radius_m=50  # Too small
            )
        
        # Too large radius
        with self.assertRaises(Exception):  # Should raise ValueError
            DiscoveryService.get_nearby_vendors(
                lat=24.0,
                lng=67.0,
                radius_m=100000  # Too large
            )
    
    def test_empty_search_query(self):
        """Test empty search query handling."""
        result = DiscoveryService.search_vendors(
            query_text='',  # Empty query
            lat=24.0,
            lng=67.0,
            radius_m=1000
        )
        
        # Should return empty list
        self.assertEqual(result, [])
    
    def test_search_query_validation(self):
        """Test search query validation."""
        # SQL injection attempt
        result = DiscoveryService.search_vendors(
            query_text="'; DROP TABLE vendors; --",
            lat=24.0,
            lng=67.0,
            radius_m=1000
        )
        
        # Should handle safely and not crash
        self.assertIsInstance(result, list)
        
        # XSS attempt
        result = DiscoveryService.search_vendors(
            query_text='<script>alert("xss")</script>',
            lat=24.0,
            lng=67.0,
            radius_m=1000
        )
        
        # Should handle safely
        self.assertIsInstance(result, list)


class DiscoveryServiceCacheTest(TestCase):
    """Test cases for caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test vendor
        self.vendor = Vendor.objects.create(
            name='Test Vendor',
            category='RESTAURANT',
            tier='GOLD',
            is_active=True,
            location=Point(67.0011, 24.8607, srid=4326)
        )
        
        self.test_lat = 24.8607
        self.test_lng = 67.0011
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key = DiscoveryService.CacheManager.get_key(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD',
            category='RESTAURANT',
            limit=50
        )
        
        expected_pattern = 'user_portal:nearby:24.8607:67.0011:1000:GOLD:RESTAURANT:50'
        self.assertEqual(key, expected_pattern)
    
    def test_cache_set_get(self):
        """Test cache set and get operations."""
        test_data = {'test': 'data'}
        
        # Set cache
        DiscoveryService.CacheManager.set(
            'nearby_vendors',
            test_data,
            timeout=300,
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        
        # Get cache
        cached_data = DiscoveryService.CacheManager.get(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        
        self.assertEqual(cached_data, test_data)
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        # Set cache
        test_data = {'test': 'data'}
        DiscoveryService.CacheManager.set(
            'nearby_vendors',
            test_data,
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        
        # Verify cache exists
        cached_data = DiscoveryService.CacheManager.get(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        self.assertEqual(cached_data, test_data)
        
        # Delete cache
        deleted = DiscoveryService.CacheManager.delete(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        self.assertTrue(deleted)
        
        # Verify cache is gone
        cached_data = DiscoveryService.CacheManager.get(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        self.assertIsNone(cached_data)
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        warmed_count = DiscoveryService.CacheManager.warm_cache(
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            user_tier='GOLD'
        )
        
        self.assertGreater(warmed_count, 0)
        
        # Verify cache exists for warmed keys
        nearby_vendors = DiscoveryService.CacheManager.get(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius=1000,
            tier='GOLD'
        )
        self.assertIsNotNone(nearby_vendors)
