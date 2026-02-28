"""
Unit tests for Customer User Portal models.
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
from ..models import Promotion, VendorReel, Tag, UserPortalConfig

User = get_user_model()


class PromotionModelTest(TestCase):
    """Test cases for Promotion model."""
    
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
        
        # Create test promotion (without vendor for testing)
        self.promotion = Promotion.objects.create(
            vendor_id=uuid.uuid4(),  # Use UUID instead of FK for testing
            title='20% Off Lunch',
            description='Get 20% off on lunch items',
            discount_type='PERCENTAGE',
            discount_percent=20,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True
        )
    
    def test_promotion_creation(self):
        """Test Promotion creation."""
        self.assertIsNotNone(self.promotion.id)
        self.assertEqual(self.promotion.title, '20% Off Lunch')
        self.assertEqual(self.promotion.description, 'Get 20% off on lunch items')
        self.assertEqual(self.promotion.discount_type, 'PERCENTAGE')
        self.assertEqual(self.promotion.discount_percent, 20)
        self.assertFalse(self.promotion.is_flash_deal)
        self.assertTrue(self.promotion.is_active)
        self.assertEqual(self.promotion.usage_count, 0)
    
    def test_promotion_str_representation(self):
        """Test string representation."""
        expected = f"{self.promotion.title} - Vendor {self.promotion.vendor_id}"
        self.assertEqual(str(self.promotion), expected)
    
    def test_is_currently_active_property(self):
        """Test is_currently_active property."""
        # Active promotion
        self.assertTrue(self.promotion.is_currently_active)
        
        # Inactive promotion (not active flag)
        self.promotion.is_active = False
        self.promotion.save()
        self.assertFalse(self.promotion.is_currently_active)
        
        # Inactive promotion (future start time)
        self.promotion.is_active = True
        self.promotion.start_time = timezone.now() + timedelta(days=1)
        self.promotion.save()
        self.assertFalse(self.promotion.is_currently_active)
        
        # Inactive promotion (past end time)
        self.promotion.start_time = timezone.now() - timedelta(days=2)
        self.promotion.end_time = timezone.now() - timedelta(days=1)
        self.promotion.save()
        self.assertFalse(self.promotion.is_currently_active)
    
    def test_get_remaining_uses(self):
        """Test get remaining uses."""
        # Unlimited uses (usage_limit is None)
        self.assertIsNone(self.promotion.get_remaining_uses())
        
        # Limited uses
        self.promotion.usage_limit = 100
        self.promotion.save()
        self.assertEqual(self.promotion.get_remaining_uses(), 100)
        
        # Some uses consumed
        self.promotion.usage_count = 30
        self.promotion.save()
        self.assertEqual(self.promotion.get_remaining_uses(), 70)
        
        # All uses consumed
        self.promotion.usage_count = 100
        self.promotion.save()
        self.assertEqual(self.promotion.get_remaining_uses(), 0)
    
    def test_discount_types(self):
        """Test all discount types."""
        discount_types = ['PERCENTAGE', 'FIXED', 'BOGO', 'FREE_ITEM']
        
        for discount_type in discount_types:
            promotion = Promotion.objects.create(
                vendor_id=uuid.uuid4(),
                title=f'Test {discount_type}',
                discount_type=discount_type,
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(days=1),
                is_active=True
            )
            self.assertEqual(promotion.discount_type, discount_type)
    
    def test_flash_deal_properties(self):
        """Test flash deal specific properties."""
        # Create flash deal
        flash_deal = Promotion.objects.create(
            vendor_id=uuid.uuid4(),
            title='Flash Deal - 50% Off',
            discount_type='PERCENTAGE',
            discount_percent=50,
            is_flash_deal=True,
            flash_duration_minutes=60,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        self.assertTrue(flash_deal.is_flash_deal)
        self.assertEqual(flash_deal.flash_duration_minutes, 60)


class VendorReelModelTest(TestCase):
    """Test cases for VendorReel model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_vendor_reel_creation(self):
        """Test VendorReel creation."""
        self.assertIsNotNone(self.reel.id)
        self.assertEqual(self.reel.title, 'Restaurant Tour')
        self.assertEqual(self.reel.description, 'Take a tour of our restaurant')
        self.assertEqual(self.reel.video_url, 'https://example.com/video.mp4')
        self.assertEqual(self.reel.thumbnail_url, 'https://example.com/thumb.jpg')
        self.assertEqual(self.reel.duration_seconds, 30)
        self.assertEqual(self.reel.view_count, 1000)
        self.assertEqual(self.reel.cta_tap_count, 50)
        self.assertEqual(self.reel.completion_count, 800)
        self.assertTrue(self.reel.is_active)
        self.assertTrue(self.reel.is_approved)
    
    def test_vendor_reel_str_representation(self):
        """Test string representation."""
        expected = f"{self.reel.title} - Vendor {self.reel.vendor_id}"
        self.assertEqual(str(self.reel), expected)
    
    def test_completion_rate_property(self):
        """Test completion rate calculation."""
        # Normal completion rate
        expected_rate = (800 / 1000) * 100
        self.assertEqual(self.reel.completion_rate, expected_rate)
        
        # Zero views
        self.reel.view_count = 0
        self.reel.save()
        self.assertEqual(self.reel.completion_rate, 0)
        
        # Perfect completion
        self.reel.view_count = 100
        self.reel.completion_count = 100
        self.reel.save()
        self.assertEqual(self.reel.completion_rate, 100.0)
    
    def test_cta_tap_rate_property(self):
        """Test CTA tap rate calculation."""
        # Normal CTA tap rate
        expected_rate = (50 / 1000) * 100
        self.assertEqual(self.reel.cta_tap_rate, expected_rate)
        
        # Zero views
        self.reel.view_count = 0
        self.reel.save()
        self.assertEqual(self.reel.cta_tap_rate, 0)
        
        # High CTA tap rate
        self.reel.view_count = 100
        self.reel.cta_tap_count = 25
        self.reel.save()
        self.assertEqual(self.reel.cta_tap_rate, 25.0)
    
    def test_reel_status_combinations(self):
        """Test different status combinations."""
        # Active and approved
        self.reel.is_active = True
        self.reel.is_approved = True
        self.reel.save()
        self.assertTrue(self.reel.is_active)
        self.assertTrue(self.reel.is_approved)
        
        # Inactive but approved
        self.reel.is_active = False
        self.reel.is_approved = True
        self.reel.save()
        self.assertFalse(self.reel.is_active)
        self.assertTrue(self.reel.is_approved)
        
        # Active but not approved
        self.reel.is_active = True
        self.reel.is_approved = False
        self.reel.save()
        self.assertTrue(self.reel.is_active)
        self.assertFalse(self.reel.is_approved)
        
        # Inactive and not approved
        self.reel.is_active = False
        self.reel.is_approved = False
        self.reel.save()
        self.assertFalse(self.reel.is_active)
        self.assertFalse(self.reel.is_approved)


class TagModelTest(TestCase):
    """Test cases for Tag model."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_tag_creation(self):
        """Test Tag creation."""
        self.assertIsNotNone(self.tag.id)
        self.assertEqual(self.tag.name, 'Pakistani Food')
        self.assertEqual(self.tag.slug, 'pakistani-food')
        self.assertEqual(self.tag.description, 'Traditional Pakistani cuisine')
        self.assertEqual(self.tag.icon_url, 'https://example.com/icon.png')
        self.assertEqual(self.tag.color, '#FF5733')
        self.assertEqual(self.tag.category, 'FOOD')
        self.assertEqual(self.tag.sort_order, 1)
        self.assertEqual(self.tag.vendor_count, 1)
        self.assertEqual(self.tag.search_count, 100)
        self.assertTrue(self.tag.is_active)
    
    def test_tag_str_representation(self):
        """Test string representation."""
        self.assertEqual(str(self.tag), 'Pakistani Food')
    
    def test_tag_categories(self):
        """Test different tag categories."""
        categories = ['FOOD', 'SHOPPING', 'ENTERTAINMENT', 'SERVICES', 'TRAVEL']
        
        for category in categories:
            tag = Tag.objects.create(
                name=f'Test {category}',
                slug=f'test-{category.lower()}',
                category=category,
                sort_order=0
            )
            self.assertEqual(tag.category, category)
    
    def test_tag_color_formats(self):
        """Test different color formats."""
        colors = ['#FF5733', '#00FF00', '#0000FF', '#FF0000']
        
        for color in colors:
            tag = Tag.objects.create(
                name=f'Color Test {color}',
                slug=f'color-test-{color[1:]}',
                color=color,
                category='TEST',
                sort_order=0
            )
            self.assertEqual(tag.color, color)
    
    def test_tag_sorting(self):
        """Test tag sorting by sort_order."""
        # Create tags with different sort orders
        tag1 = Tag.objects.create(
            name='First Tag',
            slug='first-tag',
            category='TEST',
            sort_order=3
        )
        tag2 = Tag.objects.create(
            name='Second Tag',
            slug='second-tag',
            category='TEST',
            sort_order=1
        )
        tag3 = Tag.objects.create(
            name='Third Tag',
            slug='third-tag',
            category='TEST',
            sort_order=2
        )
        
        # Query tags ordered by sort_order
        tags = Tag.objects.filter(category='TEST').order_by('sort_order')
        
        self.assertEqual(tags[0], tag2)  # sort_order=1
        self.assertEqual(tags[1], tag3)  # sort_order=2
        self.assertEqual(tags[2], tag1)  # sort_order=3


class UserPortalConfigModelTest(TestCase):
    """Test cases for UserPortalConfig model."""
    
    def setUp(self):
        """Set up test data."""
        self.config = UserPortalConfig.objects.create(
            key='max_search_radius',
            value={'default_radius': 5000, 'max_radius': 10000},
            description='Maximum search radius settings'
        )
    
    def test_config_creation(self):
        """Test UserPortalConfig creation."""
        self.assertIsNotNone(self.config.id)
        self.assertEqual(self.config.key, 'max_search_radius')
        self.assertEqual(self.config.value, {'default_radius': 5000, 'max_radius': 10000})
        self.assertEqual(self.config.description, 'Maximum search radius settings')
        self.assertIsNotNone(self.config.created_at)
        self.assertIsNotNone(self.config.updated_at)
    
    def test_config_str_representation(self):
        """Test string representation."""
        expected = "max_search_radius: Maximum search radius settings"
        self.assertEqual(str(self.config), expected)
    
    def test_get_config_class_method(self):
        """Test get_config class method."""
        # Get existing config
        config = UserPortalConfig.get_config('max_search_radius')
        self.assertEqual(config, {'default_radius': 5000, 'max_radius': 10000})
        
        # Get non-existent config with default
        config = UserPortalConfig.get_config('non_existent', {'default': 'value'})
        self.assertEqual(config, {'default': 'value'})
        
        # Get non-existent config without default
        config = UserPortalConfig.get_config('non_existent')
        self.assertIsNone(config)
    
    def test_set_config_class_method(self):
        """Test set_config class method."""
        # Create new config
        config = UserPortalConfig.set_config(
            key='new_setting',
            value={'enabled': True, 'limit': 100},
            description='New setting description'
        )
        
        self.assertEqual(config.key, 'new_setting')
        self.assertEqual(config.value, {'enabled': True, 'limit': 100})
        self.assertEqual(config.description, 'New setting description')
        
        # Update existing config
        updated_config = UserPortalConfig.set_config(
            key='new_setting',
            value={'enabled': False, 'limit': 200},
            description='Updated description'
        )
        
        self.assertEqual(updated_config.key, 'new_setting')
        self.assertEqual(updated_config.value, {'enabled': False, 'limit': 200})
        self.assertEqual(updated_config.description, 'Updated description')
        
        # Verify only one record exists
        configs = UserPortalConfig.objects.filter(key='new_setting')
        self.assertEqual(configs.count(), 1)
    
    def test_config_json_value_types(self):
        """Test different JSON value types."""
        test_cases = [
            ('string_value', 'simple_string', 'String value test'),
            ('integer_value', 42, 'Integer value test'),
            ('float_value', 3.14, 'Float value test'),
            ('boolean_value', True, 'Boolean value test'),
            ('list_value', [1, 2, 3], 'List value test'),
            ('dict_value', {'nested': 'value'}, 'Dictionary value test'),
        ]
        
        for key, value, description in test_cases:
            config = UserPortalConfig.objects.create(
                key=key,
                value=value,
                description=description
            )
            self.assertEqual(config.value, value)
            self.assertEqual(config.description, description)
    
    def test_config_key_uniqueness(self):
        """Test config key uniqueness constraint."""
        # Create first config
        UserPortalConfig.objects.create(
            key='unique_key',
            value={'test': 'value1'},
            description='First config'
        )
        
        # Try to create duplicate key (should raise exception)
        with self.assertRaises(Exception):  # Should be IntegrityError
            UserPortalConfig.objects.create(
                key='unique_key',
                value={'test': 'value2'},
                description='Second config'
            )
    
    def test_config_ordering(self):
        """Test config ordering by key."""
        # Clear any existing configs
        UserPortalConfig.objects.all().delete()
        
        # Create configs with different keys
        config1 = UserPortalConfig.objects.create(
            key='z_config',
            value={'test': 'z'},
            description='Z config'
        )
        config2 = UserPortalConfig.objects.create(
            key='a_config',
            value={'test': 'a'},
            description='A config'
        )
        config3 = UserPortalConfig.objects.create(
            key='m_config',
            value={'test': 'm'},
            description='M config'
        )
        
        # Query configs ordered by key
        configs = list(UserPortalConfig.objects.all())
        
        # Check actual ordering
        keys = [config.key for config in configs]
        
        # Verify alphabetical ordering
        self.assertEqual(keys, ['a_config', 'm_config', 'z_config'])
