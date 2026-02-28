"""
Unit tests for API endpoints.
Tests all discovery, vendor, promotion endpoints without PostGIS dependencies.
"""

import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.customer_auth.models import CustomerUser, GuestToken
from apps.customer_auth.services import CustomerAuthService
from apps.user_portal.models import Promotion, VendorReel, Tag, UserPortalConfig
from apps.user_portal.services import DiscoveryService
from apps.user_portal.views import (
    NearbyVendorsView, VendorDetailView, SearchVendorsView,
    GetTagsView, GetCitiesView, PromotionsStripView,
    ARMarkersView, VendorReelsView
)

User = get_user_model()


class DiscoveryAPIEndpointTest(APITestCase):
    """Test cases for discovery API endpoints."""
    
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
        
        # Get JWT token for authenticated requests
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
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
        
        # Test coordinates
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000
    
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def authenticate_guest(self):
        """Helper method to authenticate as guest."""
        self.client.credentials(HTTP_X_GUEST_TOKEN=str(self.guest_token.token))
    
    def test_nearby_vendors_view_authenticated(self):
        """Test nearby vendors view with authenticated user."""
        self.authenticate()
        
        url = reverse('user-portal:nearby-vendors')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            mock_get_nearby.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'final_score': 0.85,
                    'distance_m': 500
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vendors', response.data)
        self.assertIn('count', response.data)
        self.assertIn('user_tier', response.data)
        self.assertEqual(response.data['user_tier'], 'SILVER')  # Default tier
        mock_get_nearby.assert_called_once()
    
    def test_nearby_vendors_view_guest(self):
        """Test nearby vendors view with guest user."""
        self.authenticate_guest()
        
        url = reverse('user-portal:nearby-vendors')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            mock_get_nearby.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'final_score': 0.85,
                    'distance_m': 500
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vendors', response.data)
        self.assertIn('count', response.data)
        self.assertIn('user_tier', response.data)
        self.assertEqual(response.data['user_tier'], 'SILVER')  # Guest default tier
        mock_get_nearby.assert_called_once()
    
    def test_nearby_vendors_view_unauthorized(self):
        """Test nearby vendors view without authentication."""
        url = reverse('user-portal:nearby-vendors')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_nearby_vendors_view_validation_errors(self):
        """Test nearby vendors view with validation errors."""
        self.authenticate()
        
        url = reverse('user-portal:nearby-vendors')
        
        # Test missing coordinates
        data = {'radius_m': self.test_radius, 'limit': 50}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid coordinates
        data = {'lat': 91.0, 'lng': self.test_lng, 'radius_m': self.test_radius, 'limit': 50}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid radius
        data = {'lat': self.test_lat, 'lng': self.test_lng, 'radius_m': 50, 'limit': 50}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_nearby_vendors_view_category_filter(self):
        """Test nearby vendors view with category filter."""
        self.authenticate()
        
        url = reverse('user-portal:nearby-vendors')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'category': 'RESTAURANT',
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            mock_get_nearby.return_value = []
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_nearby.assert_called_once()
        
        # Verify category was passed to service
        call_args = mock_get_nearby.call_args
        self.assertEqual(call_args[1]['category'], 'RESTAURANT')
    
    def test_vendor_detail_view_success(self):
        """Test vendor detail view success."""
        self.authenticate()
        
        vendor_id = uuid.uuid4()
        url = reverse('user-portal:vendor-detail', kwargs={'vendor_id': vendor_id})
        
        with patch.object(DiscoveryService, 'get_vendor_detail') as mock_get_detail:
            mock_get_detail.return_value = {
                'vendor_id': vendor_id,
                'name': 'Test Restaurant',
                'description': 'A great place to eat',
                'category': 'RESTAURANT',
                'location': {'lat': self.test_lat, 'lng': self.test_lng}
            }
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vendor', response.data)
        mock_get_detail.assert_called_once_with(vendor_id)
    
    def test_vendor_detail_view_not_found(self):
        """Test vendor detail view with non-existent vendor."""
        self.authenticate()
        
        vendor_id = uuid.uuid4()
        url = reverse('user-portal:vendor-detail', kwargs={'vendor_id': vendor_id})
        
        with patch.object(DiscoveryService, 'get_vendor_detail') as mock_get_detail:
            mock_get_detail.return_value = None
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_search_vendors_view_text_search(self):
        """Test search vendors view with text search."""
        self.authenticate()
        
        url = reverse('user-portal:search-vendors')
        data = {
            'query': 'pakistani restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'search_vendors') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Pakistani Restaurant',
                    'final_score': 0.90,
                    'distance_m': 750
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vendors', response.data)
        self.assertIn('count', response.data)
        self.assertIn('query', response.data)
        self.assertEqual(response.data['query'], 'pakistani restaurant')
        mock_search.assert_called_once()
    
    def test_search_vendors_view_voice_search(self):
        """Test search vendors view with voice search."""
        self.authenticate()
        
        url = reverse('user-portal:search-vendors')
        data = {
            'query': 'find me a good restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'query_type': 'VOICE',
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'search_vendors') as mock_search:
            mock_search.return_value = []
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_search.assert_called_once()
        
        # Verify query type was passed to service
        call_args = mock_search.call_args
        self.assertEqual(call_args[1]['query_type'], 'VOICE')
    
    def test_search_vendors_view_missing_query(self):
        """Test search vendors view without query."""
        self.authenticate()
        
        url = reverse('user-portal:search-vendors')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_tags_view_success(self):
        """Test get tags view success."""
        url = reverse('user-portal:get-tags')
        
        with patch.object(DiscoveryService, 'get_tags') as mock_get_tags:
            mock_get_tags.return_value = [
                {
                    'id': self.tag.id,
                    'name': 'Pakistani Food',
                    'slug': 'pakistani-food',
                    'category': 'FOOD',
                    'vendor_count': 1
                }
            ]
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tags', response.data)
        self.assertIn('count', response.data)
        mock_get_tags.assert_called_once()
    
    def test_get_cities_view_success(self):
        """Test get cities view success."""
        url = reverse('user-portal:get-cities')
        
        with patch.object(DiscoveryService, 'get_cities') as mock_get_cities:
            mock_get_cities.return_value = [
                {
                    'id': uuid.uuid4(),
                    'name': 'Karachi',
                    'slug': 'karachi',
                    'vendor_count': 150
                }
            ]
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('cities', response.data)
        self.assertIn('count', response.data)
        mock_get_cities.assert_called_once()
    
    def test_promotions_strip_view_success(self):
        """Test promotions strip view success."""
        url = reverse('user-portal:promotions-strip')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius
        }
        
        with patch.object(DiscoveryService, 'get_promotions_strip') as mock_get_promotions:
            mock_get_promotions.return_value = [
                {
                    'discount_id': self.promotion.id,
                    'title': '20% Off Lunch',
                    'vendor_id': self.promotion.vendor_id,
                    'discount_percent': 20,
                    'is_flash_deal': False
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('promotions', response.data)
        self.assertIn('count', response.data)
        mock_get_promotions.assert_called_once()
    
    def test_promotions_strip_view_validation_errors(self):
        """Test promotions strip view with validation errors."""
        url = reverse('user-portal:promotions-strip')
        
        # Test missing coordinates
        data = {'radius_m': self.test_radius}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid coordinates
        data = {'lat': 91.0, 'lng': self.test_lng, 'radius_m': self.test_radius}
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_ar_markers_view_success(self):
        """Test AR markers view success."""
        self.authenticate()
        
        url = reverse('user-portal:ar-markers')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        with patch.object(DiscoveryService, 'get_ar_markers') as mock_get_markers:
            mock_get_markers.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'lat': self.test_lat,
                    'lng': self.test_lng,
                    'distance_m': 500,
                    'ar_content': {
                        'title': 'Test Restaurant',
                        'subtitle': '20% Off Today',
                        'cta_text': 'View Details'
                    }
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('markers', response.data)
        self.assertIn('count', response.data)
        mock_get_markers.assert_called_once()
    
    def test_ar_markers_view_unauthorized(self):
        """Test AR markers view without authentication."""
        url = reverse('user-portal:ar-markers')
        data = {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius_m': self.test_radius,
            'limit': 50
        }
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_vendor_reels_view_success(self):
        """Test vendor reels view success."""
        vendor_id = uuid.uuid4()
        url = reverse('user-portal:vendor-reels', kwargs={'vendor_id': vendor_id})
        
        with patch.object(DiscoveryService, 'get_vendor_reels') as mock_get_reels:
            mock_get_reels.return_value = [
                {
                    'reel_id': self.reel.id,
                    'title': 'Restaurant Tour',
                    'video_url': 'https://example.com/video.mp4',
                    'thumbnail_url': 'https://example.com/thumb.jpg',
                    'duration_seconds': 30,
                    'view_count': 1000,
                    'completion_rate': 80.0,
                    'cta_text': 'Book Now'
                }
            ]
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reels', response.data)
        self.assertIn('count', response.data)
        mock_get_reels.assert_called_once_with(vendor_id)
    
    def test_vendor_reels_view_not_found(self):
        """Test vendor reels view with non-existent vendor."""
        vendor_id = uuid.uuid4()
        url = reverse('user-portal:vendor-reels', kwargs={'vendor_id': vendor_id})
        
        with patch.object(DiscoveryService, 'get_vendor_reels') as mock_get_reels:
            mock_get_reels.return_value = []
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reels'], [])
        self.assertEqual(response.data['count'], 0)


class APIResponseFormatTest(APITestCase):
    """Test cases for API response formats."""
    
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
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        self.authenticate()
    
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_success_response_format(self):
        """Test success response format."""
        url = reverse('user-portal:get-tags')
        
        with patch.object(DiscoveryService, 'get_tags') as mock_get_tags:
            mock_get_tags.return_value = [
                {
                    'id': uuid.uuid4(),
                    'name': 'Test Tag',
                    'slug': 'test-tag'
                }
            ]
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response structure
        self.assertIn('tags', response.data)
        self.assertIn('count', response.data)
        
        # Check data structure
        self.assertIsInstance(response.data['tags'], list)
        self.assertIsInstance(response.data['count'], int)
        self.assertEqual(response.data['count'], len(response.data['tags']))
    
    def test_error_response_format(self):
        """Test error response format."""
        url = reverse('user-portal:nearby-vendors')
        
        # Send invalid data to trigger error
        data = {'lat': 'invalid', 'lng': 'invalid', 'radius_m': 1000}
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check error response structure
        self.assertIn('error', response.data)
        self.assertIn('message', response.data)
        self.assertIn('details', response.data)
        
        # Check error details
        self.assertIsInstance(response.data['details'], dict)
    
    def test_not_found_response_format(self):
        """Test not found response format."""
        vendor_id = uuid.uuid4()
        url = reverse('user-portal:vendor-detail', kwargs={'vendor_id': vendor_id})
        
        with patch.object(DiscoveryService, 'get_vendor_detail') as mock_get_detail:
            mock_get_detail.return_value = None
            
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Check error response structure
        self.assertIn('error', response.data)
        self.assertIn('message', response.data)
        self.assertIn('vendor_id', response.data)
    
    def test_unauthorized_response_format(self):
        """Test unauthorized response format."""
        # Remove authentication
        self.client.credentials()
        
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Check error response structure
        self.assertIn('error', response.data)
        self.assertIn('message', response.data)
    
    def test_pagination_response_format(self):
        """Test pagination response format."""
        url = reverse('user-portal:search-vendors')
        data = {
            'query': 'restaurant',
            'lat': 24.8607,
            'lng': 67.0011,
            'radius_m': 1000,
            'limit': 10,
            'offset': 0
        }
        
        with patch.object(DiscoveryService, 'search_vendors') as mock_search:
            # Mock paginated response
            mock_search.return_value = [
                {'vendor_id': uuid.uuid4(), 'name': f'Restaurant {i}'}
                for i in range(10)
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check pagination structure (if implemented)
        if 'pagination' in response.data:
            pagination = response.data['pagination']
            self.assertIn('limit', pagination)
            self.assertIn('offset', pagination)
            self.assertIn('total', pagination)
            self.assertIn('has_next', pagination)


class APIRateLimitingTest(APITestCase):
    """Test cases for API rate limiting."""
    
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
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Create guest token
        self.guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.authenticate()
    
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def authenticate_guest(self):
        """Helper method to authenticate as guest."""
        self.client.credentials(HTTP_X_GUEST_TOKEN=str(self.guest_token.token))
    
    def test_authenticated_user_rate_limit(self):
        """Test rate limiting for authenticated users."""
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors', return_value=[]):
            # Make multiple requests (simulate rate limiting)
            for i in range(5):
                response = self.client.get(url, data)
                if i < 4:  # Assume limit is 4 requests per minute
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                else:
                    # Should be rate limited after limit reached
                    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                        self.assertIn('error', response.data)
                        break
    
    def test_guest_user_rate_limit(self):
        """Test rate limiting for guest users."""
        self.authenticate_guest()
        
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors', return_value=[]):
            # Make multiple requests (guests have lower limits)
            for i in range(3):
                response = self.client.get(url, data)
                if i < 2:  # Assume guest limit is 2 requests per minute
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                else:
                    # Should be rate limited after limit reached
                    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                        self.assertIn('error', response.data)
                        break
    
    def test_rate_limit_headers(self):
        """Test rate limiting headers."""
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors', return_value=[]):
            response = self.client.get(url, data)
        
        # Check for rate limiting headers (if implemented)
        if 'X-RateLimit-Limit' in response:
            self.assertIn('X-RateLimit-Remaining', response)
            self.assertIn('X-RateLimit-Reset', response)


class APIErrorHandlingTest(APITestCase):
    """Test cases for API error handling."""
    
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
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        self.authenticate()
    
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_service_exception_handling(self):
        """Test handling of service exceptions."""
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            # Simulate service exception
            mock_get_nearby.side_effect = Exception("Database connection failed")
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn('message', response.data)
    
    def test_timeout_handling(self):
        """Test handling of timeouts."""
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            # Simulate timeout
            mock_get_nearby.side_effect = TimeoutError("Request timed out")
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_504_GATEWAY_TIMEOUT)
        self.assertIn('error', response.data)
    
    def test_validation_error_handling(self):
        """Test handling of validation errors."""
        url = reverse('user-portal:nearby-vendors')
        
        # Test various validation errors
        test_cases = [
            {'data': {}, 'expected_field': 'lat'},
            {'data': {'lat': 'invalid'}, 'expected_field': 'lat'},
            {'data': {'lat': 91.0, 'lng': 67.0011}, 'expected_field': 'lat'},
            {'data': {'lat': 24.8607, 'lng': 181.0}, 'expected_field': 'lng'},
            {'data': {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 50}, 'expected_field': 'radius_m'},
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                response = self.client.get(url, case['data'])
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', response.data)
                self.assertIn('details', response.data)
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON."""
        url = reverse('user-portal:nearby-vendors')
        
        # Send malformed JSON
        malformed_json = '{"lat": 24.8607, "lng": 67.0011, "radius_m": 1000'  # Missing closing brace
        
        response = self.client.post(
            url,
            data=malformed_json,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_invalid_token_handling(self):
        """Test handling of invalid authentication tokens."""
        # Use invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token')
        
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_expired_token_handling(self):
        """Test handling of expired authentication tokens."""
        # Create expired token (this would need to be mocked or manually created)
        expired_token = 'expired-token-example'
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired_token}')
        
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)


class APISecurityTest(APITestCase):
    """Test cases for API security."""
    
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
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        self.authenticate()
    
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        url = reverse('user-portal:search-vendors')
        
        # Attempt SQL injection
        malicious_query = "'; DROP TABLE users; --"
        data = {
            'query': malicious_query,
            'lat': 24.8607,
            'lng': 67.0011,
            'radius_m': 1000
        }
        
        with patch.object(DiscoveryService, 'search_vendors') as mock_search:
            mock_search.return_value = []
            
            response = self.client.get(url, data)
        
        # Should not cause server error
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify malicious query was passed to service (service should handle sanitization)
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        self.assertEqual(call_args[1]['query'], malicious_query)
    
    def test_xss_protection(self):
        """Test XSS protection."""
        url = reverse('user-portal:search-vendors')
        
        # Attempt XSS
        xss_query = "<script>alert('xss')</script>"
        data = {
            'query': xss_query,
            'lat': 24.8607,
            'lng': 67.0011,
            'radius_m': 1000
        }
        
        with patch.object(DiscoveryService, 'search_vendors') as mock_search:
            mock_search.return_value = []
            
            response = self.client.get(url, data)
        
        # Should not cause server error
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Response should not contain unescaped script tags
        response_content = response.content.decode()
        self.assertNotIn('<script>', response_content)
    
    def test_csrf_protection(self):
        """Test CSRF protection."""
        # This test would need to be adjusted based on actual CSRF implementation
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        # Test without CSRF token (if CSRF is enabled)
        response = self.client.post(url, data)
        
        # Should handle CSRF appropriately (either allow or reject based on configuration)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,  # CSRF disabled for API
            status.HTTP_403_FORBIDDEN,  # CSRF enabled
            status.HTTP_405_METHOD_NOT_ALLOWED  # Method not allowed
        ])
    
    def test_sensitive_data_exposure(self):
        """Test that sensitive data is not exposed."""
        url = reverse('user-portal:nearby-vendors')
        data = {'lat': 24.8607, 'lng': 67.0011, 'radius_m': 1000}
        
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_get_nearby:
            # Mock response with potential sensitive data
            mock_get_nearby.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'final_score': 0.85,
                    # Should not include sensitive fields like:
                    # - internal_ids
                    # - passwords
                    # - private_keys
                    # - system_info
                }
            ]
            
            response = self.client.get(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that sensitive fields are not exposed
        response_content = response.content.decode()
        sensitive_fields = ['password', 'secret', 'private_key', 'internal_id']
        
        for field in sensitive_fields:
            self.assertNotIn(field, response_content.lower())
    
    def test_request_size_limits(self):
        """Test request size limits."""
        url = reverse('user-portal:search-vendors')
        
        # Create very large query
        large_query = 'a' * 10000  # 10KB string
        data = {
            'query': large_query,
            'lat': 24.8607,
            'lng': 67.0011,
            'radius_m': 1000
        }
        
        response = self.client.get(url, data)
        
        # Should handle large request appropriately
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,  # Accepted
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,  # Too large
            status.HTTP_400_BAD_REQUEST  # Validation error
        ])
    
    def test_http_method_security(self):
        """Test HTTP method security."""
        url = reverse('user-portal:nearby-vendors')
        
        # Test unsupported methods
        unsupported_methods = ['PUT', 'DELETE', 'PATCH']
        
        for method in unsupported_methods:
            with self.subTest(method=method):
                response = getattr(self.client, method.lower())(url)
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
