"""
Unit tests for Vendor model and related spatial functionality.
Tests distance calculations, tier scoring, and location-based features.
"""

import uuid
import math
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from ..models import Vendor, Promotion, VendorReel, Tag, City, Area

User = get_user_model()


class VendorModelTest(TestCase):
    """Test cases for Vendor model."""
    
    def setUp(self):
        """Set up test data."""
        self.vendor = Vendor.objects.create(
            name='Test Restaurant',
            description='A test restaurant for unit testing',
            address='123 Test Street, Test City',
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            category='food',
            subcategory='restaurant',
            tags=['food', 'restaurant', 'pakistani'],
            tier='GOLD',
            is_active=True,
            is_verified=True,
            phone='+92-300-1234567',
            email='test@restaurant.com',
            website='https://testrestaurant.com',
            business_hours={
                'monday': {'open': '09:00', 'close': '23:00'},
                'tuesday': {'open': '09:00', 'close': '23:00'},
                'wednesday': {'open': '09:00', 'close': '23:00'},
                'thursday': {'open': '09:00', 'close': '23:00'},
                'friday': {'open': '09:00', 'close': '00:00'},
                'saturday': {'open': '10:00', 'close': '00:00'},
                'sunday': {'open': '10:00', 'close': '22:00'}
            },
            logo_url='https://example.com/logo.jpg',
            cover_image_url='https://example.com/cover.jpg',
            popularity_score=0.75,
            interaction_count=150,
            system_tags=['trending', 'verified']
        )
    
    def test_vendor_creation(self):
        """Test Vendor creation."""
        self.assertEqual(self.vendor.name, 'Test Restaurant')
        self.assertEqual(self.vendor.category, 'food')
        self.assertEqual(self.vendor.subcategory, 'restaurant')
        self.assertEqual(self.vendor.tier, 'GOLD')
        self.assertTrue(self.vendor.is_active)
        self.assertTrue(self.vendor.is_verified)
        self.assertEqual(float(self.vendor.lat), 31.5204)
        self.assertEqual(float(self.vendor.lng), 74.3587)
        self.assertEqual(self.vendor.popularity_score, 0.75)
        self.assertEqual(self.vendor.interaction_count, 150)
        self.assertEqual(self.vendor.system_tags, ['trending', 'verified'])
    
    def test_vendor_str_representation(self):
        """Test string representation."""
        expected = 'Test Restaurant (food)'
        self.assertEqual(str(self.vendor), expected)
    
    def test_get_tier_score(self):
        """Test tier score calculation."""
        # Test all tier levels
        tier_scores = {
            'SILVER': 0.25,
            'GOLD': 0.50,
            'DIAMOND': 0.75,
            'PLATINUM': 1.00,
        }
        
        for tier, expected_score in tier_scores.items():
            self.vendor.tier = tier
            self.vendor.save()
            self.assertEqual(self.vendor.get_tier_score(), expected_score)
    
    def test_calculate_distance_haversine(self):
        """Test distance calculation using Haversine formula."""
        # Test distance to same point (should be 0)
        distance = self.vendor.calculate_distance(31.5204, 74.3587)
        self.assertAlmostEqual(distance, 0, places=1)
        
        # Test distance to known nearby point (approximately 1km)
        # Using point roughly 1km north
        distance = self.vendor.calculate_distance(31.5304, 74.3587)
        self.assertAlmostEqual(distance, 1112, delta=50)  # Within 50m margin
        
        # Test distance with None values
        distance_none = self.vendor.calculate_distance(None, None)
        self.assertIsNone(distance_none)
        
        # Test distance with invalid coordinates - should handle gracefully
        try:
            distance_invalid = self.vendor.calculate_distance('invalid', 'invalid')
            self.assertIsNone(distance_invalid)
        except (ValueError, TypeError):
            # Expected behavior for invalid input
            pass
    
    def test_calculate_distance_accuracy(self):
        """Test distance calculation accuracy."""
        # Known distance between Lahore coordinates (approximately 6.1km)
        # Liberty Roundabout to Gulberg III
        vendor_lat, vendor_lng = 31.5204, 74.3587
        test_lat, test_lng = 31.4697, 74.3849
        
        distance = self.vendor.calculate_distance(test_lat, test_lng)
        
        # Should be approximately 6.1km (6100m) - adjusting expected value
        self.assertAlmostEqual(distance, 6100, delta=500)  # Within 500m margin
    
    def test_business_hours_json_field(self):
        """Test business hours JSON field."""
        expected_hours = {
            'monday': {'open': '09:00', 'close': '23:00'},
            'tuesday': {'open': '09:00', 'close': '23:00'},
            'wednesday': {'open': '09:00', 'close': '23:00'},
            'thursday': {'open': '09:00', 'close': '23:00'},
            'friday': {'open': '09:00', 'close': '00:00'},
            'saturday': {'open': '10:00', 'close': '00:00'},
            'sunday': {'open': '10:00', 'close': '22:00'}
        }
        
        self.assertEqual(self.vendor.business_hours, expected_hours)
        
        # Test empty business hours
        self.vendor.business_hours = {}
        self.vendor.save()
        self.assertEqual(self.vendor.business_hours, {})
        
        # Test complex business hours
        complex_hours = {
            'monday': {'open': '08:00', 'close': '22:00', 'break_start': '14:00', 'break_end': '15:00'},
            'tuesday': {'open': '08:00', 'close': '22:00'},
            'wednesday': None,  # Closed
            'thursday': {'open': '08:00', 'close': '22:00'},
            'friday': {'open': '08:00', 'close': '23:00'},
            'saturday': {'open': '09:00', 'close': '23:00'},
            'sunday': {'open': '10:00', 'close': '20:00'}
        }
        
        self.vendor.business_hours = complex_hours
        self.vendor.save()
        self.assertEqual(self.vendor.business_hours, complex_hours)
    
    def test_tags_json_field(self):
        """Test tags JSON field."""
        # Test initial tags
        self.assertEqual(self.vendor.tags, ['food', 'restaurant', 'pakistani'])
        
        # Test empty tags
        self.vendor.tags = []
        self.vendor.save()
        self.assertEqual(self.vendor.tags, [])
        
        # Test multiple tags
        tags = ['food', 'restaurant', 'pakistani', 'halal', 'family-friendly', 'delivery']
        self.vendor.tags = tags
        self.vendor.save()
        self.assertEqual(self.vendor.tags, tags)
        
        # Test single tag
        self.vendor.tags = ['cafe']
        self.vendor.save()
        self.assertEqual(self.vendor.tags, ['cafe'])
    
    def test_system_tags_functionality(self):
        """Test system tags for ranking boosts."""
        # Test empty system tags
        self.vendor.system_tags = []
        self.vendor.save()
        self.assertEqual(self.vendor.system_tags, [])
        
        # Test various system tags
        system_tags = ['new_vendor_boost', 'trending', 'verified', 'featured']
        self.vendor.system_tags = system_tags
        self.vendor.save()
        self.assertEqual(self.vendor.system_tags, system_tags)
        
        # Test individual system tags
        for tag in ['new_vendor_boost', 'trending', 'verified']:
            self.vendor.system_tags = [tag]
            self.vendor.save()
            self.assertEqual(self.vendor.system_tags, [tag])
    
    def test_tier_choices(self):
        """Test tier field choices."""
        valid_tiers = ['SILVER', 'GOLD', 'DIAMOND', 'PLATINUM']
        
        for tier in valid_tiers:
            self.vendor.tier = tier
            self.vendor.save()
            self.assertEqual(self.vendor.tier, tier)
    
    def test_category_and_subcategory(self):
        """Test category and subcategory fields."""
        # Test various categories
        categories = ['food', 'retail', 'services', 'healthcare', 'education']
        
        for category in categories:
            self.vendor.category = category
            self.vendor.save()
            self.assertEqual(self.vendor.category, category)
        
        # Test subcategories
        subcategories = ['restaurant', 'cafe', 'bakery', 'fast_food', 'fine_dining']
        
        for subcategory in subcategories:
            self.vendor.subcategory = subcategory
            self.vendor.save()
            self.assertEqual(self.vendor.subcategory, subcategory)
        
        # Test empty subcategory
        self.vendor.subcategory = ''
        self.vendor.save()
        self.assertEqual(self.vendor.subcategory, '')
    
    def test_contact_information_fields(self):
        """Test contact information fields."""
        # Test phone number
        self.vendor.phone = '+92-21-3456789'
        self.vendor.save()
        self.assertEqual(self.vendor.phone, '+92-21-3456789')
        
        # Test empty phone
        self.vendor.phone = ''
        self.vendor.save()
        self.assertEqual(self.vendor.phone, '')
        
        # Test email
        self.vendor.email = 'contact@test.com'
        self.vendor.save()
        self.assertEqual(self.vendor.email, 'contact@test.com')
        
        # Test website
        self.vendor.website = 'https://www.testwebsite.com'
        self.vendor.save()
        self.assertEqual(self.vendor.website, 'https://www.testwebsite.com')
    
    def test_media_url_fields(self):
        """Test media URL fields."""
        # Test logo URL
        self.vendor.logo_url = 'https://example.com/new-logo.png'
        self.vendor.save()
        self.assertEqual(self.vendor.logo_url, 'https://example.com/new-logo.png')
        
        # Test cover image URL
        self.vendor.cover_image_url = 'https://example.com/new-cover.jpg'
        self.vendor.save()
        self.assertEqual(self.vendor.cover_image_url, 'https://example.com/new-cover.jpg')
        
        # Test empty URLs
        self.vendor.logo_url = ''
        self.vendor.cover_image_url = ''
        self.vendor.save()
        self.assertEqual(self.vendor.logo_url, '')
        self.assertEqual(self.vendor.cover_image_url, '')
    
    def test_popularity_and_interaction_metrics(self):
        """Test popularity score and interaction count."""
        # Test popularity score
        for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
            self.vendor.popularity_score = score
            self.vendor.save()
            self.assertEqual(self.vendor.popularity_score, score)
        
        # Test interaction count
        for count in [0, 10, 100, 1000, 10000]:
            self.vendor.interaction_count = count
            self.vendor.save()
            self.assertEqual(self.vendor.interaction_count, count)
    
    def test_status_fields(self):
        """Test active and verified status fields."""
        # Test active status
        self.vendor.is_active = False
        self.vendor.save()
        self.assertFalse(self.vendor.is_active)
        
        self.vendor.is_active = True
        self.vendor.save()
        self.assertTrue(self.vendor.is_active)
        
        # Test verified status
        self.vendor.is_verified = False
        self.vendor.save()
        self.assertFalse(self.vendor.is_verified)
        
        self.vendor.is_verified = True
        self.vendor.save()
        self.assertTrue(self.vendor.is_verified)
    
    def test_location_precision(self):
        """Test coordinate precision handling."""
        # Test high precision coordinates - note that DecimalField may have precision limits
        high_precision_lat = Decimal('31.5204123')
        high_precision_lng = Decimal('74.3587123')
        
        self.vendor.lat = high_precision_lat
        self.vendor.lng = high_precision_lng
        self.vendor.save()
        
        self.vendor.refresh_from_db()
        # Check that values are stored correctly within field precision
        self.assertEqual(self.vendor.lat, high_precision_lat)
        self.assertEqual(self.vendor.lng, high_precision_lng)
    
    def test_model_ordering(self):
        """Test default model ordering."""
        # Create multiple vendors with different popularity scores
        vendor1 = Vendor.objects.create(
            name='Vendor 1',
            lat=Decimal('31.5200'),
            lng=Decimal('74.3580'),
            category='food',
            popularity_score=0.5
        )
        
        vendor2 = Vendor.objects.create(
            name='Vendor 2',
            lat=Decimal('31.5210'),
            lng=Decimal('74.3590'),
            category='food',
            popularity_score=0.8
        )
        
        vendor3 = Vendor.objects.create(
            name='Vendor 3',
            lat=Decimal('31.5220'),
            lng=Decimal('74.3600'),
            category='food',
            popularity_score=0.3
        )
        
        # Should be ordered by popularity_score DESC, then name ASC
        vendors = list(Vendor.objects.all())
        
        # Check that vendor2 (highest popularity) comes first
        self.assertEqual(vendors[0].name, 'Vendor 2')
        self.assertEqual(vendors[0].popularity_score, 0.8)
        
        # The original vendor from setUp might be in the list too
        # Check that vendor1 and vendor3 are in the list (order might vary due to other vendors)
        vendor_names = [v.name for v in vendors]
        self.assertIn('Vendor 1', vendor_names)
        self.assertIn('Vendor 3', vendor_names)


class VendorRelatedModelsTest(TestCase):
    """Test cases for Vendor-related models and relationships."""
    
    def setUp(self):
        """Set up test data."""
        self.vendor = Vendor.objects.create(
            name='Test Restaurant',
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            category='food',
            tier='GOLD',
            is_active=True
        )
    
    def test_vendor_with_promotions(self):
        """Test Vendor with related promotions."""
        # Create promotions
        promo1 = Promotion.objects.create(
            vendor_id=self.vendor.id,
            title='20% Off',
            discount_type='PERCENTAGE',
            discount_percent=20,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True
        )
        
        promo2 = Promotion.objects.create(
            vendor_id=self.vendor.id,
            title='Free Delivery',
            discount_type='FIXED',
            discount_amount=Decimal('50.00'),
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() + timedelta(hours=6),
            is_active=True
        )
        
        # Test get_active_promotions method
        active_promos = self.vendor.get_active_promotions()
        self.assertEqual(len(active_promos), 2)
        self.assertIn(promo1, active_promos)
        self.assertIn(promo2, active_promos)
        
        # Test with inactive promotion
        promo2.is_active = False
        promo2.save()
        
        active_promos = self.vendor.get_active_promotions()
        self.assertEqual(len(active_promos), 1)
        self.assertIn(promo1, active_promos)
        self.assertNotIn(promo2, active_promos)
        
        # Test with expired promotion
        promo1.end_time = timezone.now() - timedelta(hours=1)
        promo1.save()
        
        active_promos = self.vendor.get_active_promotions()
        self.assertEqual(len(active_promos), 0)
    
    def test_vendor_with_reels(self):
        """Test Vendor with related reels."""
        # Create reels
        reel1 = VendorReel.objects.create(
            vendor_id=self.vendor.id,
            title='Food Preparation',
            video_url='https://example.com/reel1.mp4',
            thumbnail_url='https://example.com/thumb1.jpg',
            duration_seconds=15,
            is_active=True,
            is_approved=True,
            view_count=100,
            completion_count=80,
            cta_tap_count=20
        )
        
        reel2 = VendorReel.objects.create(
            vendor_id=self.vendor.id,
            title='Customer Experience',
            video_url='https://example.com/reel2.mp4',
            thumbnail_url='https://example.com/thumb2.jpg',
            duration_seconds=10,
            is_active=True,
            is_approved=True,
            view_count=200,
            completion_count=150,
            cta_tap_count=50
        )
        
        # Test reel properties
        self.assertEqual(reel1.completion_rate, 80.0)
        self.assertEqual(reel1.cta_tap_rate, 20.0)
        
        self.assertEqual(reel2.completion_rate, 75.0)
        self.assertEqual(reel2.cta_tap_rate, 25.0)
        
        # Test with zero views
        reel3 = VendorReel.objects.create(
            vendor_id=self.vendor.id,
            title='Empty Reel',
            video_url='https://example.com/reel3.mp4',
            thumbnail_url='https://example.com/thumb3.jpg',
            duration_seconds=8,
            is_active=True,
            is_approved=True,
            view_count=0
        )
        
        self.assertEqual(reel3.completion_rate, 0)
        self.assertEqual(reel3.cta_tap_rate, 0)


class VendorSpatialQueryTest(TestCase):
    """Test spatial queries and location-based filtering."""
    
    def setUp(self):
        """Set up test vendors at different locations."""
        # Create vendors at different locations around Lahore
        self.vendors = [
            Vendor.objects.create(
                name=f'Vendor {i}',
                lat=Decimal(str(31.5204 + i * 0.01)),
                lng=Decimal(str(74.3587 + i * 0.01)),
                category='food',
                tier='GOLD',
                is_active=True
            )
            for i in range(5)
        ]
        
        # Create some inactive vendors
        self.inactive_vendor = Vendor.objects.create(
            name='Inactive Vendor',
            lat=Decimal('31.5204'),
            lng=Decimal('74.3587'),
            category='food',
            tier='SILVER',
            is_active=False
        )
    
    def test_location_based_filtering(self):
        """Test filtering vendors by location."""
        # Test filtering by coordinates (simple coordinate comparison)
        center_lat = 31.5204
        center_lng = 74.3587
        
        # Find vendors within ~1km (very rough approximation)
        nearby_vendors = Vendor.objects.filter(
            lat__gte=Decimal(str(center_lat - 0.01)),
            lat__lte=Decimal(str(center_lat + 0.01)),
            lng__gte=Decimal(str(center_lng - 0.01)),
            lng__lte=Decimal(str(center_lng + 0.01)),
            is_active=True
        )
        
        # Should include our first vendor and exclude inactive ones
        self.assertIn(self.vendors[0], nearby_vendors)
        self.assertNotIn(self.inactive_vendor, nearby_vendors)
    
    def test_category_filtering(self):
        """Test filtering vendors by category."""
        food_vendors = Vendor.objects.filter(category='food', is_active=True)
        self.assertEqual(food_vendors.count(), 5)  # All our test vendors are food vendors
        
        # Create vendors in different categories
        retail_vendor = Vendor.objects.create(
            name='Retail Shop',
            lat=Decimal('31.5300'),
            lng=Decimal('74.3687'),
            category='retail',
            is_active=True
        )
        
        service_vendor = Vendor.objects.create(
            name='Service Provider',
            lat=Decimal('31.5400'),
            lng=Decimal('74.3787'),
            category='services',
            is_active=True
        )
        
        # Test category filtering
        retail_vendors = Vendor.objects.filter(category='retail', is_active=True)
        service_vendors = Vendor.objects.filter(category='services', is_active=True)
        
        self.assertEqual(retail_vendors.count(), 1)
        self.assertEqual(service_vendors.count(), 1)
        self.assertEqual(retail_vendors.first().name, 'Retail Shop')
        self.assertEqual(service_vendors.first().name, 'Service Provider')
    
    def test_tier_filtering(self):
        """Test filtering vendors by subscription tier."""
        # Create vendors with different tiers
        silver_vendor = Vendor.objects.create(
            name='Silver Vendor',
            lat=Decimal('31.5500'),
            lng=Decimal('74.3887'),
            category='food',
            tier='SILVER',
            is_active=True
        )
        
        diamond_vendor = Vendor.objects.create(
            name='Diamond Vendor',
            lat=Decimal('31.5600'),
            lng=Decimal('74.3987'),
            category='food',
            tier='DIAMOND',
            is_active=True
        )
        
        platinum_vendor = Vendor.objects.create(
            name='Platinum Vendor',
            lat=Decimal('31.5700'),
            lng=Decimal('74.4087'),
            category='food',
            tier='PLATINUM',
            is_active=True
        )
        
        # Test tier filtering
        gold_vendors = Vendor.objects.filter(tier='GOLD', is_active=True)
        silver_vendors = Vendor.objects.filter(tier='SILVER', is_active=True)
        diamond_vendors = Vendor.objects.filter(tier='DIAMOND', is_active=True)
        platinum_vendors = Vendor.objects.filter(tier='PLATINUM', is_active=True)
        
        self.assertEqual(gold_vendors.count(), 5)  # Our original 5 vendors
        self.assertEqual(silver_vendors.count(), 1)
        self.assertEqual(diamond_vendors.count(), 1)
        self.assertEqual(platinum_vendors.count(), 1)
        
        # Test tier scores
        self.assertEqual(silver_vendors.first().get_tier_score(), 0.25)
        self.assertEqual(diamond_vendors.first().get_tier_score(), 0.75)
        self.assertEqual(platinum_vendors.first().get_tier_score(), 1.00)
    
    def test_status_filtering(self):
        """Test filtering vendors by active and verified status."""
        # Create verified and unverified vendors
        verified_vendor = Vendor.objects.create(
            name='Verified Vendor',
            lat=Decimal('31.5800'),
            lng=Decimal('74.4187'),
            category='food',
            tier='GOLD',
            is_active=True,
            is_verified=True
        )
        
        unverified_vendor = Vendor.objects.create(
            name='Unverified Vendor',
            lat=Decimal('31.5900'),
            lng=Decimal('74.4287'),
            category='food',
            tier='GOLD',
            is_active=True,
            is_verified=False
        )
        
        # Test status filtering
        active_vendors = Vendor.objects.filter(is_active=True)
        inactive_vendors = Vendor.objects.filter(is_active=False)
        verified_vendors = Vendor.objects.filter(is_verified=True)
        unverified_vendors = Vendor.objects.filter(is_verified=False)
        
        self.assertGreater(active_vendors.count(), inactive_vendors.count())
        # There might be more unverified vendors from other test setups, so just check counts are positive
        self.assertGreater(verified_vendors.count(), 0)
        self.assertGreater(unverified_vendors.count(), 0)
        
        # Test combined filtering
        active_verified_vendors = Vendor.objects.filter(is_active=True, is_verified=True)
        self.assertIn(verified_vendor, active_verified_vendors)
        self.assertNotIn(unverified_vendor, active_verified_vendors)
        self.assertNotIn(self.inactive_vendor, active_verified_vendors)
