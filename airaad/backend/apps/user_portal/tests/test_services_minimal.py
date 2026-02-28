"""
Unit tests for Discovery Engine services.
Tests ranking algorithm, spatial queries, and caching without PostGIS dependencies.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal

from apps.customer_auth.models import CustomerUser
from ..models import Promotion, VendorReel, Tag, UserPortalConfig
from ..services import DiscoveryService

User = get_user_model()


class DiscoveryServiceTest(TestCase):
    """Test cases for DiscoveryService without PostGIS dependencies."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()
        
        # Create test user
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
        
        # Create test promotion
        self.promotion = Promotion.objects.create(
            vendor_id=uuid.uuid4(),
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
            vendor_id=uuid.uuid4(),
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
        
        # Test coordinates (Karachi)
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000  # 1km
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_ranking_weights_constants(self):
        """Test ranking weights are properly defined."""
        self.assertIn('relevance', DiscoveryService.RANKING_WEIGHTS)
        self.assertIn('distance', DiscoveryService.RANKING_WEIGHTS)
        self.assertIn('offer', DiscoveryService.RANKING_WEIGHTS)
        self.assertIn('popularity', DiscoveryService.RANKING_WEIGHTS)
        self.assertIn('tier', DiscoveryService.RANKING_WEIGHTS)
        
        # Check weights sum to 1.0
        total_weight = sum(DiscoveryService.RANKING_WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
    
    def test_tier_scores_constants(self):
        """Test tier scores are properly defined."""
        self.assertIn('SILVER', DiscoveryService.TIER_SCORES)
        self.assertIn('GOLD', DiscoveryService.TIER_SCORES)
        self.assertIn('DIAMOND', DiscoveryService.TIER_SCORES)
        self.assertIn('PLATINUM', DiscoveryService.TIER_SCORES)
        
        # Check tier scores are in ascending order
        self.assertLess(DiscoveryService.TIER_SCORES['SILVER'], DiscoveryService.TIER_SCORES['GOLD'])
        self.assertLess(DiscoveryService.TIER_SCORES['GOLD'], DiscoveryService.TIER_SCORES['DIAMOND'])
        self.assertLess(DiscoveryService.TIER_SCORES['DIAMOND'], DiscoveryService.TIER_SCORES['PLATINUM'])
    
    def test_system_tag_boosts_constants(self):
        """Test system tag boosts are properly defined."""
        self.assertIn('new_vendor_boost', DiscoveryService.SYSTEM_TAG_BOOSTS)
        self.assertIn('trending', DiscoveryService.SYSTEM_TAG_BOOSTS)
        self.assertIn('verified', DiscoveryService.SYSTEM_TAG_BOOSTS)
        
        # Check boosts are positive values
        for boost in DiscoveryService.SYSTEM_TAG_BOOSTS.values():
            self.assertGreater(boost, 0)
    
    def test_cache_timeouts_constants(self):
        """Test cache timeouts are properly defined."""
        self.assertIn('nearby_vendors', DiscoveryService.CACHE_TIMEOUTS)
        self.assertIn('ar_markers', DiscoveryService.CACHE_TIMEOUTS)
        self.assertIn('vendor_detail', DiscoveryService.CACHE_TIMEOUTS)
        self.assertIn('promotions', DiscoveryService.CACHE_TIMEOUTS)
        self.assertIn('tags', DiscoveryService.CACHE_TIMEOUTS)
        self.assertIn('cities', DiscoveryService.CACHE_TIMEOUTS)
        
        # Check timeouts are positive integers
        for timeout in DiscoveryService.CACHE_TIMEOUTS.values():
            self.assertIsInstance(timeout, int)
            self.assertGreater(timeout, 0)
    
    @patch('apps.user_portal.services.cache')
    def test_get_cache_key_generation(self, mock_cache):
        """Test cache key generation."""
        # Test basic cache key generation
        key = DiscoveryService._generate_cache_key(
            'nearby_vendors',
            lat=self.test_lat,
            lng=self.test_lng,
            radius_m=self.test_radius,
            user_tier='GOLD',
            category='RESTAURANT',
            limit=50
        )
        
        expected_key = "nearby_vendors_24.8607_67.0011_1000_GOLD_RESTAURANT_50"
        self.assertEqual(key, expected_key)
    
    @patch('apps.user_portal.services.cache')
    def test_cache_hit_scenario(self, mock_cache):
        """Test cache hit scenario."""
        # Mock cache hit
        cached_result = [
            {'vendor_id': uuid.uuid4(), 'name': 'Test Restaurant', 'final_score': 0.85}
        ]
        mock_cache.get.return_value = cached_result
        
        # Call service method
        with patch.object(DiscoveryService, '_query_vendors') as mock_query:
            result = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='GOLD',
                limit=50
            )
        
        # Verify cache was checked
        mock_cache.get.assert_called_once()
        
        # Verify database query was not made (cache hit)
        mock_query.assert_not_called()
        
        # Verify cached result was returned
        self.assertEqual(result, cached_result)
    
    @patch('apps.user_portal.services.cache')
    def test_cache_miss_scenario(self, mock_cache):
        """Test cache miss scenario."""
        # Mock cache miss
        mock_cache.get.return_value = None
        
        # Mock vendor query result
        mock_vendors = []
        mock_cache.set.return_value = None
        
        # Call service method
        with patch.object(DiscoveryService, '_query_vendors', return_value=mock_vendors) as mock_query:
            result = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='GOLD',
                limit=50
            )
        
        # Verify cache was checked
        mock_cache.get.assert_called_once()
        
        # Verify database query was made (cache miss)
        mock_query.assert_called_once()
        
        # Verify result was cached
        mock_cache.set.assert_called_once()
        
        # Verify empty result was returned
        self.assertEqual(result, mock_vendors)
    
    def test_calculate_vendor_score_basic(self):
        """Test basic vendor score calculation."""
        # Mock vendor object
        mock_vendor = Mock()
        mock_vendor.id = uuid.uuid4()
        mock_vendor.name = 'Test Restaurant'
        mock_vendor.category = 'RESTAURANT'
        mock_vendor.tier = 'GOLD'
        mock_vendor.popularity_score = 85.5
        mock_vendor.interaction_count = 150
        mock_vendor.system_tags = ['verified']
        
        # Mock user point
        mock_user_point = Mock()
        
        # Mock user preferences
        user_preferences = {
            'preferred_categories': ['RESTAURANT'],
            'price_range': 'MID'
        }
        
        # Calculate score
        with patch.object(DiscoveryService, '_calculate_relevance_score', return_value=0.8), \
             patch.object(DiscoveryService, '_calculate_distance_score', return_value=0.9), \
             patch.object(DiscoveryService, '_calculate_offer_score', return_value=0.7), \
             patch.object(DiscoveryService, '_calculate_popularity_score', return_value=0.85), \
             patch.object(DiscoveryService, '_calculate_tier_score', return_value=0.5):
            
            score_data = DiscoveryService._calculate_vendor_score(
                mock_vendor, mock_user_point, user_preferences
            )
        
        # Verify score structure
        self.assertIn('vendor_id', score_data)
        self.assertIn('relevance_score', score_data)
        self.assertIn('distance_score', score_data)
        self.assertIn('offer_score', score_data)
        self.assertIn('popularity_score', score_data)
        self.assertIn('tier_score', score_data)
        self.assertIn('weighted_score', score_data)
        self.assertIn('final_score', score_data)
        
        # Verify score values are in expected range
        self.assertGreaterEqual(score_data['relevance_score'], 0)
        self.assertLessEqual(score_data['relevance_score'], 1)
        self.assertGreaterEqual(score_data['final_score'], 0)
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        # Mock vendor
        mock_vendor = Mock()
        mock_vendor.category = 'RESTAURANT'
        mock_vendor.subcategory = 'Pakistani'
        mock_vendor.tags = ['food', 'pakistani', 'halal']
        
        # Test exact category match
        user_preferences = {
            'preferred_categories': ['RESTAURANT'],
            'search_query': 'pakistani'
        }
        
        score = DiscoveryService._calculate_relevance_score(mock_vendor, user_preferences)
        
        # Score should be high for exact match
        self.assertGreater(score, 0.5)
        self.assertLessEqual(score, 1.0)
        
        # Test no match
        user_preferences_no_match = {
            'preferred_categories': ['SHOPPING'],
            'search_query': 'electronics'
        }
        
        score_no_match = DiscoveryService._calculate_relevance_score(mock_vendor, user_preferences_no_match)
        
        # Score should be low for no match
        self.assertLessEqual(score_no_match, 0.8)
    
    def test_calculate_distance_score(self):
        """Test distance score calculation."""
        # Mock vendor location (1km away)
        mock_vendor = Mock()
        mock_vendor.location.distance_m = 1000.0
        
        # Mock user point
        mock_user_point = Mock()
        
        # Calculate score
        score = DiscoveryService._calculate_distance_score(mock_vendor, mock_user_point)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
        
        # Closer vendor should have higher score
        mock_vendor_close = Mock()
        mock_vendor_close.location.distance_m = 100.0
        
        score_close = DiscoveryService._calculate_distance_score(mock_vendor_close, mock_user_point)
        
        self.assertGreater(score_close, score)
    
    def test_calculate_offer_score(self):
        """Test offer score calculation."""
        # Mock vendor with active promotion
        mock_vendor = Mock()
        mock_vendor.active_promotions = [self.promotion]
        
        score = DiscoveryService._calculate_offer_score(mock_vendor)
        
        # Score should be positive for active promotion
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1)
        
        # Mock vendor without promotions
        mock_vendor_no_promos = Mock()
        mock_vendor_no_promos.active_promotions = []
        
        score_no_promos = DiscoveryService._calculate_offer_score(mock_vendor_no_promos)
        
        # Score should be zero for no promotions
        self.assertEqual(score_no_promos, 0)
    
    def test_calculate_popularity_score(self):
        """Test popularity score calculation."""
        # Mock vendor with high popularity
        mock_vendor = Mock()
        mock_vendor.popularity_score = 85.5
        mock_vendor.interaction_count = 150
        
        score = DiscoveryService._calculate_popularity_score(mock_vendor)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)
        
        # More popular vendor should have higher score
        mock_vendor_unpopular = Mock()
        mock_vendor_unpopular.popularity_score = 10.0
        mock_vendor_unpopular.interaction_count = 5
        
        score_unpopular = DiscoveryService._calculate_popularity_score(mock_vendor_unpopular)
        
        self.assertGreater(score, score_unpopular)
    
    def test_calculate_tier_score(self):
        """Test tier score calculation."""
        # Test each tier
        tiers = ['SILVER', 'GOLD', 'DIAMOND', 'PLATINUM']
        
        scores = []
        for tier in tiers:
            mock_vendor = Mock()
            mock_vendor.tier = tier
            
            score = DiscoveryService._calculate_tier_score(mock_vendor)
            scores.append(score)
            
            # Score should match tier score constant
            self.assertEqual(score, DiscoveryService.TIER_SCORES[tier])
        
        # Higher tier should have higher score
        self.assertEqual(scores[0], DiscoveryService.TIER_SCORES['SILVER'])
        self.assertEqual(scores[1], DiscoveryService.TIER_SCORES['GOLD'])
        self.assertEqual(scores[2], DiscoveryService.TIER_SCORES['DIAMOND'])
        self.assertEqual(scores[3], DiscoveryService.TIER_SCORES['PLATINUM'])
        
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])
        self.assertLess(scores[2], scores[3])
    
    def test_apply_system_tag_boosts(self):
        """Test system tag boosts application."""
        # Mock vendor with system tags
        mock_vendor = Mock()
        mock_vendor.system_tags = ['verified', 'trending']
        
        base_score = 0.7
        
        boosted_score = DiscoveryService._apply_system_tag_boosts(mock_vendor, base_score)
        
        # Score should be higher than base score
        self.assertGreater(boosted_score, base_score)
        
        # Verify boost calculation
        expected_boost = base_score + DiscoveryService.SYSTEM_TAG_BOOSTS['verified'] + DiscoveryService.SYSTEM_TAG_BOOSTS['trending']
        self.assertAlmostEqual(boosted_score, expected_boost, places=5)
    
    def test_get_vendor_detail_cached(self):
        """Test get_vendor_detail with caching."""
        vendor_id = uuid.uuid4()
        
        # Mock cache hit
        cached_detail = {
            'vendor_id': vendor_id,
            'name': 'Test Restaurant',
            'description': 'Test description'
        }
        
        with patch.object(DiscoveryService, '_get_from_cache', return_value=cached_detail):
            result = DiscoveryService.get_vendor_detail(vendor_id)
        
        self.assertEqual(result, cached_detail)
    
    def test_get_vendor_detail_not_cached(self):
        """Test get_vendor_detail without caching."""
        vendor_id = uuid.uuid4()
        
        # Mock cache miss and vendor query
        mock_vendor = Mock()
        mock_vendor.id = vendor_id
        mock_vendor.name = 'Test Restaurant'
        mock_vendor.description = 'Test description'
        
        with patch.object(DiscoveryService, '_get_from_cache', return_value=None), \
             patch.object(DiscoveryService, '_query_vendor_by_id', return_value=mock_vendor), \
             patch.object(DiscoveryService, '_set_cache') as mock_set_cache:
            
            result = DiscoveryService.get_vendor_detail(vendor_id)
        
        # Verify result structure
        self.assertIn('vendor_id', result)
        self.assertIn('name', result)
        self.assertIn('description', result)
        
        # Verify result was cached
        mock_set_cache.assert_called_once()
    
    def test_get_tags_cached(self):
        """Test get_tags with caching."""
        # Mock cache hit
        cached_tags = [
            {'id': self.tag.id, 'name': 'Pakistani Food', 'slug': 'pakistani-food'}
        ]
        
        with patch.object(DiscoveryService, '_get_from_cache', return_value=cached_tags):
            result = DiscoveryService.get_tags()
        
        self.assertEqual(result, cached_tags)
    
    def test_get_tags_not_cached(self):
        """Test get_tags without caching."""
        # Mock cache miss and tag query
        with patch.object(DiscoveryService, '_get_from_cache', return_value=None), \
             patch.object(DiscoveryService, '_query_active_tags', return_value=[self.tag]), \
             patch.object(DiscoveryService, '_set_cache') as mock_set_cache:
            
            result = DiscoveryService.get_tags()
        
        # Verify result structure
        self.assertIsInstance(result, list)
        if result:
            self.assertIn('id', result[0])
            self.assertIn('name', result[0])
            self.assertIn('slug', result[0])
        
        # Verify result was cached
        mock_set_cache.assert_called_once()
    
    def test_get_promotions_strip_cached(self):
        """Test get_promotions_strip with caching."""
        # Mock cache hit
        cached_promotions = [
            {
                'discount_id': self.promotion.id,
                'title': '20% Off Lunch',
                'vendor_id': self.promotion.vendor_id
            }
        ]
        
        with patch.object(DiscoveryService, '_get_from_cache', return_value=cached_promotions):
            result = DiscoveryService.get_promotions_strip(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius
            )
        
        self.assertEqual(result, cached_promotions)
    
    def test_get_promotions_strip_not_cached(self):
        """Test get_promotions_strip without caching."""
        # Mock cache miss and promotion query
        with patch.object(DiscoveryService, '_get_from_cache', return_value=None), \
             patch.object(DiscoveryService, '_query_nearby_promotions', return_value=[self.promotion]), \
             patch.object(DiscoveryService, '_set_cache') as mock_set_cache:
            
            result = DiscoveryService.get_promotions_strip(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius
            )
        
        # Verify result structure
        self.assertIsInstance(result, list)
        if result:
            self.assertIn('discount_id', result[0])
            self.assertIn('title', result[0])
            self.assertIn('vendor_id', result[0])
        
        # Verify result was cached
        mock_set_cache.assert_called_once()
    
    def test_search_vendors_text_search(self):
        """Test text search functionality."""
        # Mock search results
        mock_vendors = []
        
        with patch.object(DiscoveryService, '_query_vendors_by_text', return_value=mock_vendors), \
             patch.object(DiscoveryService, '_set_cache'):
            
            result = DiscoveryService.search_vendors(
                query='pakistani restaurant',
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='GOLD',
                limit=50
            )
        
        # Verify result structure
        self.assertIsInstance(result, list)
    
    def test_search_vendors_voice_search(self):
        """Test voice search functionality."""
        # Mock search results
        mock_vendors = []
        
        with patch.object(DiscoveryService, '_query_vendors_by_voice', return_value=mock_vendors), \
             patch.object(DiscoveryService, '_set_cache'):
            
            result = DiscoveryService.search_vendors(
                query='find me a good restaurant',
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='GOLD',
                limit=50,
                query_type='VOICE'
            )
        
        # Verify result structure
        self.assertIsInstance(result, list)
    
    def test_extract_search_intent(self):
        """Test search intent extraction."""
        # Test food-related query
        intent = DiscoveryService._extract_search_intent('pakistani restaurant near me')
        
        self.assertIsInstance(intent, dict)
        self.assertIn('category', intent)
        self.assertIn('price_range', intent)
        # features key may not be present in all implementations
        
        # Test shopping-related query
        intent_shopping = DiscoveryService._extract_search_intent('cheap clothing store')
        
        self.assertIsInstance(intent_shopping, dict)
        self.assertIn('category', intent_shopping)
    
    def test_validate_coordinates(self):
        """Test coordinate validation."""
        # Valid coordinates
        self.assertTrue(DiscoveryService._validate_coordinates(24.8607, 67.0011))
        
        # Invalid coordinates (out of range)
        self.assertFalse(DiscoveryService._validate_coordinates(91.0, 0.0))  # Invalid latitude
        self.assertFalse(DiscoveryService._validate_coordinates(0.0, 181.0))  # Invalid longitude
        
        # Invalid coordinates (wrong type)
        self.assertFalse(DiscoveryService._validate_coordinates('invalid', 67.0011))
        self.assertFalse(DiscoveryService._validate_coordinates(24.8607, 'invalid'))
    
    def test_validate_radius(self):
        """Test radius validation."""
        # Valid radius
        self.assertTrue(DiscoveryService._validate_radius(100))
        self.assertTrue(DiscoveryService._validate_radius(5000))
        
        # Invalid radius (out of range)
        self.assertFalse(DiscoveryService._validate_radius(50))   # Too small
        self.assertFalse(DiscoveryService._validate_radius(10000))  # Too large
        
        # Invalid radius (wrong type)
        self.assertFalse(DiscoveryService._validate_radius('invalid'))
        self.assertFalse(DiscoveryService._validate_radius(-100))
    
    def test_validate_user_tier(self):
        """Test user tier validation."""
        # Valid tiers
        valid_tiers = ['SILVER', 'GOLD', 'DIAMOND', 'PLATINUM']
        for tier in valid_tiers:
            self.assertTrue(DiscoveryService._validate_user_tier(tier))
        
        # Invalid tier
        self.assertFalse(DiscoveryService._validate_user_tier('INVALID'))
        self.assertFalse(DiscoveryService._validate_user_tier(''))
        self.assertFalse(DiscoveryService._validate_user_tier(None))
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        vendor_id = uuid.uuid4()
        
        # Mock cache operations
        with patch.object(DiscoveryService, '_delete_cache_pattern') as mock_delete:
            DiscoveryService.invalidate_vendor_cache(vendor_id)
        
        # Verify cache deletion was called
        mock_delete.assert_called()
    
    def test_warm_cache(self):
        """Test cache warming."""
        # Mock cache warming operations
        with patch.object(DiscoveryService, '_set_cache') as mock_set, \
             patch.object(DiscoveryService, '_query_active_tags', return_value=[self.tag]), \
             patch.object(DiscoveryService, '_query_all_cities', return_value=[]):
            
            DiscoveryService.warm_cache()
        
        # Verify cache was set for tags
        mock_set.assert_called()
    
    def test_error_handling(self):
        """Test error handling in service methods."""
        # Test with invalid coordinates
        with self.assertRaises(ValueError):
            DiscoveryService.get_nearby_vendors(
                lat=91.0,  # Invalid latitude
                lng=67.0011,
                radius_m=1000,
                user_tier='GOLD'
            )
        
        # Test with invalid radius
        with self.assertRaises(ValueError):
            DiscoveryService.get_nearby_vendors(
                lat=24.8607,
                lng=67.0011,
                radius_m=50,  # Invalid radius
                user_tier='GOLD'
            )
        
        # Test with invalid user tier
        with self.assertRaises(ValueError):
            DiscoveryService.get_nearby_vendors(
                lat=24.8607,
                lng=67.0011,
                radius_m=1000,
                user_tier='INVALID'  # Invalid tier
            )
    
    def test_performance_optimizations(self):
        """Test performance optimizations."""
        # Test query limit enforcement
        with patch.object(DiscoveryService, '_query_vendors') as mock_query:
            # Mock large result set
            mock_query.return_value = [Mock() for _ in range(200)]
            
            result = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='GOLD',
                limit=50
            )
        
        # Result should be limited to requested limit
        self.assertLessEqual(len(result), 50)
    
    def test_configuration_driven_behavior(self):
        """Test configuration-driven behavior."""
        # Test with custom configuration
        with patch.object(UserPortalConfig, 'get_config') as mock_config:
            mock_config.return_value = {'max_results': 25}
            
            # Service should respect configuration
            with patch.object(DiscoveryService, '_query_vendors') as mock_query:
                mock_query.return_value = [Mock() for _ in range(100)]
                
                result = DiscoveryService.get_nearby_vendors(
                    lat=self.test_lat,
                    lng=self.test_lng,
                    radius_m=self.test_radius,
                    user_tier='GOLD',
                    limit=50  # Higher than config limit
                )
            
            # Should respect config limit over request limit
            self.assertLessEqual(len(result), 25)
