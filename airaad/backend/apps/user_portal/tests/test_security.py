"""
Unit tests for Security functionality.
Tests input validation, authorization, and rate limiting.
"""

import uuid
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.customer_auth.models import CustomerUser, GuestToken
from apps.customer_auth.services import CustomerAuthService, SecurityService
from apps.user_portal.models import Promotion, VendorReel, Tag
from apps.user_portal.services import ValidationService, AuthorizationService, RateLimitService

User = get_user_model()


class ValidationServiceTest(TestCase):
    """Test cases for ValidationService."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_phone = '+1234567890'
        self.test_coordinates = {'lat': 24.8607, 'lng': 67.0011}
    
    def test_validate_email_format(self):
        """Test email format validation."""
        # Valid emails
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                is_valid = ValidationService.validate_email(email)
                self.assertTrue(is_valid)
        
        # Invalid emails
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user..name@example.com',
            'user@.example.com',
            'user@example.',
            ''
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                is_valid = ValidationService.validate_email(email)
                self.assertFalse(is_valid)
    
    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = [
            '+1234567890',
            '+44 20 7946 0958',
            '+1 (555) 123-4567',
            '+92-300-1234567'
        ]
        
        for phone in valid_phones:
            with self.subTest(phone=phone):
                is_valid = ValidationService.validate_phone_number(phone)
                self.assertTrue(is_valid)
        
        # Invalid phone numbers
        invalid_phones = [
            '1234567890',  # Missing country code
            '+123',         # Too short
            'invalid-phone',
            '',
            None
        ]
        
        for phone in invalid_phones:
            with self.subTest(phone=phone):
                is_valid = ValidationService.validate_phone_number(phone)
                self.assertFalse(is_valid)
    
    def test_validate_coordinates(self):
        """Test coordinate validation."""
        # Valid coordinates
        valid_coords = [
            {'lat': 24.8607, 'lng': 67.0011},  # Karachi
            {'lat': 40.7128, 'lng': -74.0060}, # New York
            {'lat': -33.8688, 'lng': 151.2093}, # Sydney
            {'lat': 0, 'lng': 0},             # Null Island
        ]
        
        for coords in valid_coords:
            with self.subTest(coords=coords):
                is_valid = ValidationService.validate_coordinates(coords['lat'], coords['lng'])
                self.assertTrue(is_valid)
        
        # Invalid coordinates
        invalid_coords = [
            {'lat': 91, 'lng': 0},    # Invalid latitude
            {'lat': -91, 'lng': 0},   # Invalid latitude
            {'lat': 0, 'lng': 181},   # Invalid longitude
            {'lat': 0, 'lng': -181},  # Invalid longitude
            {'lat': 'invalid', 'lng': 67.0011},  # Invalid type
            {'lat': 24.8607, 'lng': 'invalid'},   # Invalid type
        ]
        
        for coords in invalid_coords:
            with self.subTest(coords=coords):
                is_valid = ValidationService.validate_coordinates(coords['lat'], coords['lng'])
                self.assertFalse(is_valid)
    
    def test_validate_search_query(self):
        """Test search query validation."""
        # Valid queries
        valid_queries = [
            'restaurant near me',
            'cafe with wifi',
            'cheap food',
            'bakery',
            'restaurant in Karachi'
        ]
        
        for query in valid_queries:
            with self.subTest(query=query):
                is_valid = ValidationService.validate_search_query(query)
                self.assertTrue(is_valid)
        
        # Invalid queries
        invalid_queries = [
            '',                    # Empty
            '   ',                 # Whitespace only
            'a' * 1001,           # Too long
            None,                  # None
            '<script>alert("xss")</script>',  # XSS attempt
            "'; DROP TABLE users; --",         # SQL injection attempt
        ]
        
        for query in invalid_queries:
            with self.subTest(query=query):
                is_valid = ValidationService.validate_search_query(query)
                self.assertFalse(is_valid)
    
    def test_validate_radius(self):
        """Test radius validation."""
        # Valid radii
        valid_radii = [100, 500, 1000, 5000, 10000]
        
        for radius in valid_radii:
            with self.subTest(radius=radius):
                is_valid = ValidationService.validate_radius(radius)
                self.assertTrue(is_valid)
        
        # Invalid radii
        invalid_radii = [
            50,      # Too small
            15000,   # Too large
            0,       # Zero
            -100,    # Negative
            'invalid', # Invalid type
            None,     # None
        ]
        
        for radius in invalid_radii:
            with self.subTest(radius=radius):
                is_valid = ValidationService.validate_radius(radius)
                self.assertFalse(is_valid)
    
    def test_validate_pagination_params(self):
        """Test pagination parameter validation."""
        # Valid parameters
        valid_params = [
            {'limit': 10, 'offset': 0},
            {'limit': 50, 'offset': 100},
            {'limit': 100, 'offset': 500},
        ]
        
        for params in valid_params:
            with self.subTest(params=params):
                is_valid = ValidationService.validate_pagination_params(
                    params['limit'], params['offset']
                )
                self.assertTrue(is_valid)
        
        # Invalid parameters
        invalid_params = [
            {'limit': 0, 'offset': 0},      # Zero limit
            {'limit': 1001, 'offset': 0},    # Limit too high
            {'limit': -10, 'offset': 0},     # Negative limit
            {'limit': 10, 'offset': -1},     # Negative offset
            {'limit': 'invalid', 'offset': 0}, # Invalid type
        ]
        
        for params in invalid_params:
            with self.subTest(params=params):
                is_valid = ValidationService.validate_pagination_params(
                    params['limit'], params['offset']
                )
                self.assertFalse(is_valid)
    
    def test_validate_user_data(self):
        """Test user data validation."""
        # Valid user data
        valid_data = {
            'email': 'test@example.com',
            'display_name': 'Test User',
            'phone_number': '+1234567890',
            'preferred_categories': ['food', 'cafe'],
            'search_radius': 1000
        }
        
        is_valid, errors = ValidationService.validate_user_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid user data
        invalid_data = {
            'email': 'invalid-email',
            'display_name': '',  # Empty
            'phone_number': '123',  # Invalid format
            'preferred_categories': 'not-a-list',  # Wrong type
            'search_radius': 50000  # Too large
        }
        
        is_valid, errors = ValidationService.validate_user_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Check error structure
        for error in errors:
            self.assertIn('field', error)
            self.assertIn('message', error)
            self.assertIn('code', error)
    
    def test_validate_vendor_data(self):
        """Test vendor data validation."""
        # Valid vendor data
        valid_data = {
            'name': 'Test Restaurant',
            'description': 'A great place to eat',
            'category': 'RESTAURANT',
            'subcategory': 'Pakistani',
            'address': '123 Test St',
            'phone': '+1234567890',
            'email': 'restaurant@example.com',
            'location': {'lat': 24.8607, 'lng': 67.0011}
        }
        
        is_valid, errors = ValidationService.validate_vendor_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid vendor data
        invalid_data = {
            'name': '',  # Empty
            'description': 'A' * 1001,  # Too long
            'category': 'INVALID_CATEGORY',
            'address': '',  # Empty
            'phone': 'invalid',
            'email': 'invalid-email',
            'location': {'lat': 'invalid', 'lng': 'invalid'}
        }
        
        is_valid, errors = ValidationService.validate_vendor_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_validate_promotion_data(self):
        """Test promotion data validation."""
        # Valid promotion data
        valid_data = {
            'title': '20% Off Lunch',
            'description': 'Get 20% off on lunch items',
            'discount_type': 'PERCENTAGE',
            'discount_percent': 20,
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(days=1),
            'is_active': True
        }
        
        is_valid, errors = ValidationService.validate_promotion_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid promotion data
        invalid_data = {
            'title': '',  # Empty
            'description': 'A' * 501,  # Too long
            'discount_type': 'INVALID_TYPE',
            'discount_percent': 150,  # Over 100%
            'start_time': timezone.now() + timedelta(days=1),  # Future start
            'end_time': timezone.now() - timedelta(days=1),   # Past end
        }
        
        is_valid, errors = ValidationService.validate_promotion_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Test XSS prevention
        xss_input = '<script>alert("xss")</script>restaurant'
        sanitized = ValidationService.sanitize_input(xss_input)
        self.assertNotIn('<script>', sanitized)
        self.assertIn('restaurant', sanitized)
        
        # Test SQL injection prevention
        sql_input = "'; DROP TABLE users; --restaurant"
        sanitized = ValidationService.sanitize_input(sql_input)
        self.assertNotIn('DROP TABLE', sanitized)
        self.assertNotIn('--', sanitized)
        
        # Test normal input (should remain unchanged)
        normal_input = 'restaurant near me'
        sanitized = ValidationService.sanitize_input(normal_input)
        self.assertEqual(sanitized, normal_input)
    
    def test_validate_file_upload(self):
        """Test file upload validation."""
        # Valid file data
        valid_file = {
            'name': 'image.jpg',
            'size': 1024 * 1024,  # 1MB
            'content_type': 'image/jpeg',
            'content': b'fake_image_data'
        }
        
        is_valid, errors = ValidationService.validate_file_upload(
            valid_file,
            allowed_types=['image/jpeg', 'image/png'],
            max_size=5 * 1024 * 1024  # 5MB
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid file data
        invalid_file = {
            'name': 'malware.exe',
            'size': 10 * 1024 * 1024,  # 10MB
            'content_type': 'application/octet-stream',
            'content': b'fake_malware'
        }
        
        is_valid, errors = ValidationService.validate_file_upload(
            invalid_file,
            allowed_types=['image/jpeg', 'image/png'],
            max_size=5 * 1024 * 1024  # 5MB
        )
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class AuthorizationServiceTest(TestCase):
    """Test cases for AuthorizationService."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users with different roles/tiers
        self.silver_user = User.objects.create_user(
            username='silver@example.com',
            email='silver@example.com',
            password='testpass123'
        )
        self.silver_customer = CustomerUser.objects.create(
            user=self.silver_user,
            display_name='Silver User',
            subscription_tier='SILVER'
        )
        
        self.gold_user = User.objects.create_user(
            username='gold@example.com',
            email='gold@example.com',
            password='testpass123'
        )
        self.gold_customer = CustomerUser.objects.create(
            user=self.gold_user,
            display_name='Gold User',
            subscription_tier='GOLD'
        )
        
        # Create guest token
        self.guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
    
    def test_check_user_permission(self):
        """Test user permission checking."""
        # Test Silver user permissions
        self.assertTrue(AuthorizationService.check_user_permission(
            self.silver_customer,
            'basic_search'
        ))
        self.assertFalse(AuthorizationService.check_user_permission(
            self.silver_customer,
            'voice_search'
        ))
        
        # Test Gold user permissions
        self.assertTrue(AuthorizationService.check_user_permission(
            self.gold_customer,
            'voice_search'
        ))
        self.assertFalse(AuthorizationService.check_user_permission(
            self.gold_customer,
            'advanced_analytics'
        ))
    
    def test_check_guest_permission(self):
        """Test guest permission checking."""
        # Test guest permissions
        self.assertTrue(AuthorizationService.check_guest_permission(
            self.guest_token.token,
            'basic_search'
        ))
        self.assertFalse(AuthorizationService.check_guest_permission(
            self.guest_token.token,
            'voice_search'
        ))
    
    def test_check_resource_ownership(self):
        """Test resource ownership checking."""
        # Create resource owned by user
        resource_id = uuid.uuid4()
        owner_id = self.silver_customer.id
        
        # Test ownership
        self.assertTrue(AuthorizationService.check_resource_ownership(
            user=self.silver_customer,
            resource_id=resource_id,
            owner_id=owner_id
        ))
        
        # Test non-ownership
        self.assertFalse(AuthorizationService.check_resource_ownership(
            user=self.gold_customer,
            resource_id=resource_id,
            owner_id=owner_id
        ))
    
    def test_check_tier_limits(self):
        """Test tier limit checking."""
        # Test Silver tier limits
        self.assertTrue(AuthorizationService.check_tier_limits(
            self.silver_customer,
            'max_search_radius',
            500  # Within limit
        ))
        self.assertFalse(AuthorizationService.check_tier_limits(
            self.silver_customer,
            'max_search_radius',
            5000  # Exceeds limit
        ))
        
        # Test Gold tier limits (higher)
        self.assertTrue(AuthorizationService.check_tier_limits(
            self.gold_customer,
            'max_search_radius',
            5000  # Within Gold limit
        ))
    
    def test_check_rate_limits(self):
        """Test rate limit checking."""
        # Test within limits
        self.assertTrue(AuthorizationService.check_rate_limits(
            user=self.silver_customer,
            endpoint='search',
            current_usage=50,
            time_window=3600  # 1 hour
        ))
        
        # Test exceeding limits
        self.assertFalse(AuthorizationService.check_rate_limits(
            user=self.silver_customer,
            endpoint='search',
            current_usage=1000,  # Exceeds typical limit
            time_window=3600
        ))
    
    def test_check_ip_whitelist(self):
        """Test IP whitelist checking."""
        # Test whitelisted IP
        self.assertTrue(AuthorizationService.check_ip_whitelist(
            ip_address='192.168.1.1',
            whitelist=['192.168.1.0/24', '10.0.0.0/8']
        ))
        
        # Test non-whitelisted IP
        self.assertFalse(AuthorizationService.check_ip_whitelist(
            ip_address='203.0.113.1',
            whitelist=['192.168.1.0/24', '10.0.0.0/8']
        ))
    
    def test_check_geo_restrictions(self):
        """Test geographic restrictions."""
        # Test allowed country
        self.assertTrue(AuthorizationService.check_geo_restrictions(
            country_code='PK',
            allowed_countries=['PK', 'US', 'GB']
        ))
        
        # Test restricted country
        self.assertFalse(AuthorizationService.check_geo_restrictions(
            country_code='XX',
            allowed_countries=['PK', 'US', 'GB']
        ))
    
    def test_check_feature_access(self):
        """Test feature access checking."""
        # Test feature access by tier
        self.assertTrue(AuthorizationService.check_feature_access(
            user=self.gold_customer,
            feature='voice_search'
        ))
        
        self.assertFalse(AuthorizationService.check_feature_access(
            user=self.silver_customer,
            feature='voice_search'
        ))
        
        # Test feature access for guest
        self.assertTrue(AuthorizationService.check_feature_access(
            guest_token=self.guest_token.token,
            feature='basic_search'
        ))
        
        self.assertFalse(AuthorizationService.check_feature_access(
            guest_token=self.guest_token.token,
            feature='voice_search'
        ))
    
    def test_check_admin_access(self):
        """Test admin access checking."""
        # Test non-admin user
        self.assertFalse(AuthorizationService.check_admin_access(
            user=self.silver_customer
        ))
        
        # Test with admin role (mocked)
        with patch.object(AuthorizationService, '_is_admin_user', return_value=True):
            self.assertTrue(AuthorizationService.check_admin_access(
                user=self.silver_customer
            ))
    
    def test_get_user_permissions(self):
        """Test getting user permissions."""
        silver_permissions = AuthorizationService.get_user_permissions(
            self.silver_customer
        )
        
        self.assertIsInstance(silver_permissions, list)
        self.assertIn('basic_search', silver_permissions)
        self.assertNotIn('voice_search', silver_permissions)
        
        gold_permissions = AuthorizationService.get_user_permissions(
            self.gold_customer
        )
        
        self.assertIsInstance(gold_permissions, list)
        self.assertIn('basic_search', gold_permissions)
        self.assertIn('voice_search', gold_permissions)
        # Gold should have more permissions than Silver
        self.assertGreater(len(gold_permissions), len(silver_permissions))
    
    def test_validate_api_key(self):
        """Test API key validation."""
        # Create valid API key
        api_key = 'test-api-key-12345'
        
        with patch.object(AuthorizationService, '_validate_api_key_format', return_value=True):
            is_valid = AuthorizationService.validate_api_key(api_key)
            self.assertTrue(is_valid)
        
        # Test invalid API key
        invalid_key = 'invalid-key'
        
        with patch.object(AuthorizationService, '_validate_api_key_format', return_value=False):
            is_valid = AuthorizationService.validate_api_key(invalid_key)
            self.assertFalse(is_valid)


class RateLimitServiceTest(TestCase):
    """Test cases for RateLimitService."""
    
    def setUp(self):
        """Set up test data."""
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
        
        # Create guest token
        self.guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
    
    def test_check_rate_limit_user(self):
        """Test rate limiting for authenticated users."""
        # Test within limits
        with patch.object(RateLimitService, '_get_user_usage', return_value=10):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                user=self.customer_user,
                endpoint='search',
                limit=100,
                window=3600
            )
            
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 90)
        
        # Test exceeding limits
        with patch.object(RateLimitService, '_get_user_usage', return_value=100):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                user=self.customer_user,
                endpoint='search',
                limit=100,
                window=3600
            )
            
            self.assertFalse(is_allowed)
            self.assertEqual(remaining, 0)
    
    def test_check_rate_limit_guest(self):
        """Test rate limiting for guest users."""
        # Test within guest limits (typically lower)
        with patch.object(RateLimitService, '_get_guest_usage', return_value=5):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                guest_token=self.guest_token.token,
                endpoint='search',
                limit=10,  # Lower limit for guests
                window=3600
            )
            
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 5)
        
        # Test exceeding guest limits
        with patch.object(RateLimitService, '_get_guest_usage', return_value=10):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                guest_token=self.guest_token.token,
                endpoint='search',
                limit=10,
                window=3600
            )
            
            self.assertFalse(is_allowed)
            self.assertEqual(remaining, 0)
    
    def test_check_rate_limit_ip(self):
        """Test IP-based rate limiting."""
        # Test within IP limits
        with patch.object(RateLimitService, '_get_ip_usage', return_value=50):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                ip_address='192.168.1.1',
                endpoint='search',
                limit=200,
                window=3600
            )
            
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 150)
        
        # Test exceeding IP limits
        with patch.object(RateLimitService, '_get_ip_usage', return_value=200):
            is_allowed, remaining = RateLimitService.check_rate_limit(
                ip_address='192.168.1.1',
                endpoint='search',
                limit=200,
                window=3600
            )
            
            self.assertFalse(is_allowed)
            self.assertEqual(remaining, 0)
    
    def test_record_usage(self):
        """Test recording usage."""
        # Record user usage
        success = RateLimitService.record_usage(
            user=self.customer_user,
            endpoint='search',
            window=3600
        )
        
        self.assertTrue(success)
        
        # Record guest usage
        success = RateLimitService.record_usage(
            guest_token=self.guest_token.token,
            endpoint='search',
            window=3600
        )
        
        self.assertTrue(success)
        
        # Record IP usage
        success = RateLimitService.record_usage(
            ip_address='192.168.1.1',
            endpoint='search',
            window=3600
        )
        
        self.assertTrue(success)
    
    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        with patch.object(RateLimitService, '_get_usage_stats', return_value={
            'total_requests': 100,
            'unique_users': 25,
            'top_endpoints': [
                {'endpoint': 'search', 'count': 50},
                {'endpoint': 'vendor_detail', 'count': 30}
            ],
            'hourly_breakdown': [10, 15, 20, 25, 30]
        }):
            stats = RateLimitService.get_usage_stats(
                window=3600,
                group_by='endpoint'
            )
            
            self.assertIsInstance(stats, dict)
            self.assertIn('total_requests', stats)
            self.assertIn('unique_users', stats)
            self.assertIn('top_endpoints', stats)
            self.assertIn('hourly_breakdown', stats)
    
    def test_reset_usage(self):
        """Test resetting usage counters."""
        # Reset user usage
        success = RateLimitService.reset_usage(
            user=self.customer_user,
            endpoint='search'
        )
        
        self.assertTrue(success)
        
        # Reset guest usage
        success = RateLimitService.reset_usage(
            guest_token=self.guest_token.token,
            endpoint='search'
        )
        
        self.assertTrue(success)
        
        # Reset IP usage
        success = RateLimitService.reset_usage(
            ip_address='192.168.1.1',
            endpoint='search'
        )
        
        self.assertTrue(success)
    
    def test_cleanup_expired_usage(self):
        """Test cleanup of expired usage records."""
        with patch.object(RateLimitService, '_cleanup_expired_records', return_value=150):
            cleaned_count = RateLimitService.cleanup_expired_usage()
            
            self.assertEqual(cleaned_count, 150)
    
    def test_rate_limit_configuration(self):
        """Test rate limit configuration."""
        config = RateLimitService.get_rate_limit_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn('default_limits', config)
        self.assertIn('tier_limits', config)
        self.assertIn('guest_limits', config)
        self.assertIn('ip_limits', config)
        self.assertIn('endpoints', config)
        
        # Check structure of limits
        for limit_type in ['default_limits', 'tier_limits', 'guest_limits']:
            limits = config[limit_type]
            self.assertIsInstance(limits, dict)
            self.assertIn('search', limits)
            self.assertIn('vendor_detail', limits)
            
            for endpoint_limit in limits.values():
                self.assertIn('requests', endpoint_limit)
                self.assertIn('window', endpoint_limit)
    
    def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting."""
        # Test normal conditions
        is_allowed, remaining = RateLimitService.adaptive_rate_limit(
            user=self.customer_user,
            endpoint='search',
            system_load=0.5,  # 50% load
            base_limit=100
        )
        
        self.assertTrue(is_allowed)
        self.assertGreater(remaining, 0)
        
        # Test high system load (should reduce limits)
        is_allowed, remaining = RateLimitService.adaptive_rate_limit(
            user=self.customer_user,
            endpoint='search',
            system_load=0.9,  # 90% load
            base_limit=100
        )
        
        # Should have reduced limit
        self.assertIsInstance(is_allowed, bool)
        self.assertIsInstance(remaining, int)
    
    def test_rate_limit_bypass(self):
        """Test rate limit bypass conditions."""
        # Test admin bypass
        with patch.object(AuthorizationService, 'check_admin_access', return_value=True):
            is_allowed, remaining = RateLimitService.check_rate_limit_with_bypass(
                user=self.customer_user,
                endpoint='search',
                limit=100,
                window=3600
            )
            
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 999999)  # Unlimited for admin
        
        # Test whitelist bypass
        with patch.object(AuthorizationService, 'check_ip_whitelist', return_value=True):
            is_allowed, remaining = RateLimitService.check_rate_limit_with_bypass(
                ip_address='192.168.1.1',
                endpoint='search',
                limit=100,
                window=3600
            )
            
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 999999)  # Unlimited for whitelisted IP


class SecurityServiceTest(TestCase):
    """Test cases for SecurityService."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_detect_suspicious_activity(self):
        """Test suspicious activity detection."""
        # Normal activity
        normal_activity = {
            'login_attempts': 1,
            'failed_logins': 0,
            'api_calls_per_minute': 10,
            'unique_ips': 1,
            'unusual_locations': 0,
            'rapid_requests': 0
        }
        
        risk_score = SecurityService.detect_suspicious_activity(
            self.customer_user,
            normal_activity
        )
        
        self.assertIsInstance(risk_score, float)
        self.assertLess(risk_score, 0.3)  # Low risk
        
        # Suspicious activity
        suspicious_activity = {
            'login_attempts': 10,
            'failed_logins': 8,
            'api_calls_per_minute': 200,
            'unique_ips': 5,
            'unusual_locations': 3,
            'rapid_requests': 50
        }
        
        risk_score = SecurityService.detect_suspicious_activity(
            self.customer_user,
            suspicious_activity
        )
        
        self.assertIsInstance(risk_score, float)
        self.assertGreater(risk_score, 0.7)  # High risk
    
    def test_check_password_strength(self):
        """Test password strength checking."""
        # Strong passwords
        strong_passwords = [
            'MyStr0ng!P@ssw0rd',
            'C0mpl3x#P@ssw0rd123',
            'SecureP@ss2024!'
        ]
        
        for password in strong_passwords:
            with self.subTest(password=password):
                strength = SecurityService.check_password_strength(password)
                self.assertGreaterEqual(strength, 0.8)  # Strong
        
        # Weak passwords
        weak_passwords = [
            'password',
            '123456',
            'abc',
            'weak',
            ''
        ]
        
        for password in weak_passwords:
            with self.subTest(password=password):
                strength = SecurityService.check_password_strength(password)
                self.assertLess(strength, 0.3)  # Weak
    
    def test_encrypt_sensitive_data(self):
        """Test sensitive data encryption."""
        sensitive_data = 'user_social_security_number_123456789'
        
        encrypted = SecurityService.encrypt_sensitive_data(sensitive_data)
        
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, sensitive_data)
        self.assertGreater(len(encrypted), len(sensitive_data))
        
        # Test decryption
        decrypted = SecurityService.decrypt_sensitive_data(encrypted)
        self.assertEqual(decrypted, sensitive_data)
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        # Test phone number masking
        phone = '+1234567890'
        masked = SecurityService.mask_sensitive_data(phone, data_type='phone')
        self.assertEqual(masked, '+123456****')
        
        # Test email masking
        email = 'test@example.com'
        masked = SecurityService.mask_sensitive_data(email, data_type='email')
        self.assertEqual(masked, 't***@example.com')
        
        # Test credit card masking
        card = '4111111111111111'
        masked = SecurityService.mask_sensitive_data(card, data_type='credit_card')
        self.assertEqual(masked, '****-****-****-1111')
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token = SecurityService.generate_secure_token(length=32)
        
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 32)
        
        # Tokens should be different each time
        token2 = SecurityService.generate_secure_token(length=32)
        self.assertNotEqual(token, token2)
    
    def test_validate_jwt_token(self):
        """Test JWT token validation."""
        # Generate valid token
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Validate token
        is_valid, payload = SecurityService.validate_jwt_token(access_token)
        
        self.assertTrue(is_valid)
        self.assertIsInstance(payload, dict)
        self.assertIn('user_id', payload)
        self.assertEqual(payload['user_id'], self.user.id)
        
        # Test invalid token
        is_valid, payload = SecurityService.validate_jwt_token('invalid-token')
        
        self.assertFalse(is_valid)
        self.assertIsNone(payload)
    
    def test_check_session_security(self):
        """Test session security checking."""
        # Create session data
        session_data = {
            'user_id': self.customer_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...',
            'created_at': timezone.now(),
            'last_activity': timezone.now()
        }
        
        # Valid session
        is_secure, issues = SecurityService.check_session_security(
            session_data,
            current_ip='192.168.1.1',
            current_user_agent='Mozilla/5.0...'
        )
        
        self.assertTrue(is_secure)
        self.assertEqual(len(issues), 0)
        
        # Session with IP change
        is_secure, issues = SecurityService.check_session_security(
            session_data,
            current_ip='203.0.113.1',  # Different IP
            current_user_agent='Mozilla/5.0...'
        )
        
        self.assertFalse(is_secure)
        self.assertGreater(len(issues), 0)
        self.assertIn('ip_address_changed', issues)
    
    def test_log_security_event(self):
        """Test security event logging."""
        event_data = {
            'event_type': 'LOGIN_FAILED',
            'user_id': self.customer_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...',
            'timestamp': timezone.now(),
            'details': {'reason': 'invalid_password'}
        }
        
        success = SecurityService.log_security_event(event_data)
        
        self.assertTrue(success)
    
    def test_get_security_audit_log(self):
        """Test security audit log retrieval."""
        with patch.object(SecurityService, '_get_security_events', return_value=[
            {
                'event_type': 'LOGIN_SUCCESS',
                'user_id': self.customer_user.id,
                'timestamp': timezone.now(),
                'ip_address': '192.168.1.1'
            },
            {
                'event_type': 'LOGIN_FAILED',
                'user_id': None,
                'timestamp': timezone.now() - timedelta(hours=1),
                'ip_address': '192.168.1.1'
            }
        ]):
            audit_log = SecurityService.get_security_audit_log(
                days=7,
                event_types=['LOGIN_SUCCESS', 'LOGIN_FAILED']
            )
            
            self.assertIsInstance(audit_log, list)
            self.assertEqual(len(audit_log), 2)
            
            for event in audit_log:
                self.assertIn('event_type', event)
                self.assertIn('timestamp', event)
                self.assertIn('ip_address', event)
    
    def test_block_malicious_ip(self):
        """Test malicious IP blocking."""
        ip_address = '203.0.113.1'
        
        # Block IP
        success = SecurityService.block_malicious_ip(
            ip_address=ip_address,
            reason='brute_force_attempt',
            duration_hours=24
        )
        
        self.assertTrue(success)
        
        # Check if IP is blocked
        is_blocked = SecurityService.is_ip_blocked(ip_address)
        self.assertTrue(is_blocked)
        
        # Unblock IP
        success = SecurityService.unblock_ip(ip_address)
        self.assertTrue(success)
        
        # Check if IP is unblocked
        is_blocked = SecurityService.is_ip_blocked(ip_address)
        self.assertFalse(is_blocked)
    
    def test_security_health_check(self):
        """Test security health check."""
        health_status = SecurityService.get_security_health_check()
        
        self.assertIsInstance(health_status, dict)
        self.assertIn('overall_status', health_status)
        self.assertIn('checks', health_status)
        self.assertIn('score', health_status)
        self.assertIn('recommendations', health_status)
        
        # Check individual security checks
        checks = health_status['checks']
        self.assertIn('password_policy', checks)
        self.assertIn('session_security', checks)
        self.assertIn('rate_limiting', checks)
        self.assertIn('encryption', checks)
        self.assertIn('audit_logging', checks)
        
        # Each check should have status and details
        for check_name, check_data in checks.items():
            self.assertIn('status', check_data)
            self.assertIn('details', check_data)
            self.assertIn('last_checked', check_data)
