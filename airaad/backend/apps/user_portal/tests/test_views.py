"""
Unit tests for User Portal API views.
"""

import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache

from ..models import Promotion, VendorReel, Tag, City, Vendor
from ..views import NearbyVendorsView, ARMarkersView, VendorDetailView, SearchView
from apps.customer_auth.models import CustomerUser, GuestToken

User = get_user_model()


class UserPortalViewTest(APITestCase):
    """Base test case for User Portal views."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        
        # Create test vendor (now using simple coordinates)
        self.vendor = Vendor.objects.create(
            name='Test Restaurant',
            category='RESTAURANT',
            tier='GOLD',
            is_active=True,
            is_verified=True,
            lat=24.8607,
            lng=67.0011,
            address='123 Test St',
            phone='+1234567890',
            email='test@restaurant.com',
            popularity_score=85.5,
            interaction_count=150
        )
        
        # Create test promotion
        self.promotion = Promotion.objects.create(
            vendor_id=self.vendor.id,
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
            vendor_id=self.vendor.id,
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
        
        # Create authenticated user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Create guest token
        self.guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
            ip_address='192.168.1.1',
        )
        
        # Test coordinates
        self.test_lat = 24.8607
        self.test_lng = 67.0011
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def authenticate_user(self):
        """Authenticate test user."""
        self.client.force_authenticate(user=self.user)
        return self.user
    
    def set_guest_token(self):
        """Set guest token header."""
        self.client.credentials(
            HTTP_X_GUEST_TOKEN=str(self.guest_token.token)
        )


class NearbyVendorsViewTest(UserPortalViewTest):
    """Test cases for NearbyVendorsView."""
    
    def test_nearby_vendors_authenticated_user(self):
        """Test nearby vendors with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000,
            'limit': 50
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('vendors', data['data'])
        self.assertIn('count', data['data'])
        self.assertIn('search_params', data['data'])
        
        vendors = data['data']['vendors']
        self.assertIsInstance(vendors, list)
        
        if vendors:
            vendor = vendors[0]
            self.assertIn('vendor_id', vendor)
            self.assertIn('final_score', vendor)
            self.assertIn('distance_m', vendor)
    
    def test_nearby_vendors_guest_user(self):
        """Test nearby vendors with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('vendors', data['data'])
    
    def test_nearby_vendors_unauthenticated(self):
        """Test nearby vendors without authentication."""
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_nearby_vendors_missing_coordinates(self):
        """Test nearby vendors with missing coordinates."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Latitude and longitude are required', data['error']['message'])
    
    def test_nearby_vendors_invalid_coordinates(self):
        """Test nearby vendors with invalid coordinates."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': 'invalid',
            'lng': self.test_lng,
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_nearby_vendors_invalid_radius(self):
        """Test nearby vendors with invalid radius."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 'invalid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_nearby_vendors_with_category_filter(self):
        """Test nearby vendors with category filter."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000,
            'category': 'RESTAURANT'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('vendors', data['data'])
    
    def test_nearby_vendors_with_limit(self):
        """Test nearby vendors with limit parameter."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000,
            'limit': 10
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertLessEqual(len(data['data']['vendors']), 10)


class ARMarkersViewTest(UserPortalViewTest):
    """Test cases for ARMarkersView."""
    
    def test_ar_markers_authenticated_user(self):
        """Test AR markers with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:ar_markers')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 500
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('markers', data['data'])
        self.assertIn('count', data['data'])
        
        markers = data['data']['markers']
        self.assertIsInstance(markers, list)
        
        if markers:
            marker = markers[0]
            self.assertIn('id', marker)
            self.assertIn('name', marker)
            self.assertIn('category', marker)
            self.assertIn('tier', marker)
            self.assertIn('lat', marker)
            self.assertIn('lng', marker)
            self.assertIn('distance_m', marker)
            self.assertIn('tier_color', marker)
    
    def test_ar_markers_guest_user(self):
        """Test AR markers with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:ar_markers')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 500
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('markers', data['data'])
    
    def test_ar_markers_unauthenticated(self):
        """Test AR markers without authentication."""
        url = reverse('user_portal:ar_markers')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 500
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_ar_markers_missing_coordinates(self):
        """Test AR markers with missing coordinates."""
        self.authenticate_user()
        
        url = reverse('user_portal:ar_markers')
        response = self.client.get(url, {
            'radius': 500
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_ar_markers_large_radius(self):
        """Test AR markers with radius exceeding limit."""
        self.authenticate_user()
        
        url = reverse('user_portal:ar_markers')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000  # Exceeds 2km limit
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VendorDetailViewTest(UserPortalViewTest):
    """Test cases for VendorDetailView."""
    
    def test_vendor_detail_authenticated_user(self):
        """Test vendor detail with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': self.vendor.id})
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)
        
        vendor_data = data['data']
        self.assertIn('id', vendor_data)
        self.assertIn('name', vendor_data)
        self.assertIn('category', vendor_data)
        self.assertIn('tier', vendor_data)
        self.assertIn('promotions', vendor_data)
        self.assertIn('reels', vendor_data)
        self.assertIn('navigation_urls', vendor_data)
        self.assertIn('distance_m', vendor_data)
        
        # Check promotions structure
        promotions = vendor_data['promotions']
        self.assertIsInstance(promotions, list)
        if promotions:
            promo = promotions[0]
            self.assertIn('id', promo)
            self.assertIn('title', promo)
            self.assertIn('discount_percent', promo)
            self.assertIn('is_flash_deal', promo)
        
        # Check reels structure
        reels = vendor_data['reels']
        self.assertIsInstance(reels, list)
        if reels:
            reel = reels[0]
            self.assertIn('id', reel)
            self.assertIn('title', reel)
            self.assertIn('video_url', reel)
            self.assertIn('completion_rate', reel)
    
    def test_vendor_detail_guest_user(self):
        """Test vendor detail with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': self.vendor.id})
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('data', data)
    
    def test_vendor_detail_unauthenticated(self):
        """Test vendor detail without authentication."""
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': self.vendor.id})
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_vendor_detail_not_found(self):
        """Test vendor detail with non-existent vendor."""
        self.authenticate_user()
        
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': uuid.uuid4()})
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Vendor not found', data['error']['message'])
    
    def test_vendor_detail_without_location(self):
        """Test vendor detail without user location."""
        self.authenticate_user()
        
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': self.vendor.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        vendor_data = data['data']
        self.assertIsNone(vendor_data['distance_m'])


class SearchViewTest(UserPortalViewTest):
    """Test cases for SearchView."""
    
    def test_search_authenticated_user(self):
        """Test search with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': 'restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000,
            'limit': 20
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('results', data['data'])
        self.assertIn('query', data['data'])
        self.assertIn('search_params', data['data'])
        
        results = data['data']['results']
        self.assertIsInstance(results, list)
        
        if results:
            result = results[0]
            self.assertIn('id', result)
            self.assertIn('name', result)
            self.assertIn('category', result)
            self.assertIn('relevance_score', result)
            self.assertIn('extracted_intent', result)
    
    def test_search_guest_user(self):
        """Test search with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': 'restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data['data'])
    
    def test_search_unauthenticated(self):
        """Test search without authentication."""
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': 'restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_search_missing_query(self):
        """Test search with missing query."""
        self.authenticate_user()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Search query is required', data['error']['message'])
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        self.authenticate_user()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': '',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_search_without_location(self):
        """Test search without location parameters."""
        self.authenticate_user()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': 'restaurant'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        results = data['data']['results']
        self.assertIsInstance(results, list)
    
    def test_search_intent_extraction(self):
        """Test search intent extraction."""
        self.authenticate_user()
        
        url = reverse('user_portal:search')
        response = self.client.get(url, {
            'q': 'pakistani restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        results = data['data']['results']
        
        if results:
            result = results[0]
            intent = result['extracted_intent']
            self.assertIn('category', intent)
            self.assertEqual(intent['category'], 'RESTAURANT')


class VoiceSearchViewTest(UserPortalViewTest):
    """Test cases for VoiceSearchView."""
    
    def test_voice_search_authenticated_user(self):
        """Test voice search with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:voice_search')
        response = self.client.post(url, {
            'transcript': 'pakistani restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000,
            'limit': 20
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('results', data['data'])
        self.assertIn('transcript', data['data'])
        
        self.assertEqual(data['data']['transcript'], 'pakistani restaurant')
    
    def test_voice_search_guest_user(self):
        """Test voice search with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:voice_search')
        response = self.client.post(url, {
            'transcript': 'restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data['data'])
    
    def test_voice_search_unauthenticated(self):
        """Test voice search without authentication."""
        url = reverse('user_portal:voice_search')
        response = self.client.post(url, {
            'transcript': 'restaurant',
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_voice_search_missing_transcript(self):
        """Test voice search with missing transcript."""
        self.authenticate_user()
        
        url = reverse('user_portal:voice_search')
        response = self.client.post(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Voice transcript is required', data['error']['message'])


class TagsViewTest(UserPortalViewTest):
    """Test cases for TagsView."""
    
    def test_tags_authenticated_user(self):
        """Test tags with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:tags')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('tags', data['data'])
        self.assertIn('count', data['data'])
        
        tags = data['data']['tags']
        self.assertIsInstance(tags, list)
    
    def test_tags_guest_user(self):
        """Test tags with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:tags')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('tags', data['data'])
    
    def test_tags_unauthenticated(self):
        """Test tags without authentication."""
        url = reverse('user_portal:tags')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tags_with_category_filter(self):
        """Test tags with category filter."""
        self.authenticate_user()
        
        url = reverse('user_portal:tags')
        response = self.client.get(url, {
            'category': 'FOOD'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        tags = data['data']['tags']
        self.assertIsInstance(tags, list)


class CitiesViewTest(UserPortalViewTest):
    """Test cases for CitiesView."""
    
    def test_cities_authenticated_user(self):
        """Test cities with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:cities')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('cities', data['data'])
        self.assertIn('count', data['data'])
        
        cities = data['data']['cities']
        self.assertIsInstance(cities, list)
    
    def test_cities_guest_user(self):
        """Test cities with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:cities')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('cities', data['data'])
    
    def test_cities_unauthenticated(self):
        """Test cities without authentication."""
        url = reverse('user_portal:cities')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PromotionsStripViewTest(UserPortalViewTest):
    """Test cases for PromotionsStripView."""
    
    def test_promotions_strip_authenticated_user(self):
        """Test promotions strip with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:promotions_strip')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000,
            'limit': 20
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('promotions', data['data'])
        self.assertIn('count', data['data'])
        
        promotions = data['data']['promotions']
        self.assertIsInstance(promotions, list)
    
    def test_promotions_strip_guest_user(self):
        """Test promotions strip with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:promotions_strip')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('promotions', data['data'])
    
    def test_promotions_strip_unauthenticated(self):
        """Test promotions strip without authentication."""
        url = reverse('user_portal:promotions_strip')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FlashDealsViewTest(UserPortalViewTest):
    """Test cases for FlashDealsView."""
    
    def test_flash_deals_authenticated_user(self):
        """Test flash deals with authenticated user."""
        self.authenticate_user()
        
        # Create flash deal
        flash_promotion = Promotion.objects.create(
            vendor=self.vendor,
            title='Flash Deal 50% Off',
            discount_type='PERCENTAGE',
            discount_percent=50,
            is_flash_deal=True,
            start_time=timezone.now() - timedelta(minutes=30),
            end_time=timezone.now() + timedelta(minutes=30),
            is_active=True
        )
        
        url = reverse('user_portal:flash_deals')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('flash_deals', data['data'])
        self.assertIn('count', data['data'])
        
        flash_deals = data['data']['flash_deals']
        self.assertIsInstance(flash_deals, list)
    
    def test_flash_deals_guest_user(self):
        """Test flash deals with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:flash_deals')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('flash_deals', data['data'])
    
    def test_flash_deals_unauthenticated(self):
        """Test flash deals without authentication."""
        url = reverse('user_portal:flash_deals')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 5000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_flash_deals_missing_coordinates(self):
        """Test flash deals with missing coordinates."""
        self.authenticate_user()
        
        url = reverse('user_portal:flash_deals')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NearbyReelsViewTest(UserPortalViewTest):
    """Test cases for NearbyReelsView."""
    
    def test_nearby_reels_authenticated_user(self):
        """Test nearby reels with authenticated user."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_reels')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 2000,
            'limit': 20
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('reels', data['data'])
        self.assertIn('count', data['data'])
        
        reels = data['data']['reels']
        self.assertIsInstance(reels, list)
    
    def test_nearby_reels_guest_user(self):
        """Test nearby reels with guest user."""
        self.set_guest_token()
        
        url = reverse('user_portal:nearby_reels')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 2000
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('reels', data['data'])
    
    def test_nearby_reels_unauthenticated(self):
        """Test nearby reels without authentication."""
        url = reverse('user_portal:nearby_reels')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 2000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserPortalViewErrorTest(UserPortalViewTest):
    """Test cases for error handling in views."""
    
    def test_404_not_found(self):
        """Test 404 error handling."""
        self.authenticate_user()
        
        url = reverse('user_portal:vendor_detail', kwargs={'vendor_id': uuid.uuid4()})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('message', data['error'])
        self.assertIn('error_code', data['error'])
    
    def test_400_bad_request(self):
        """Test 400 error handling."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': 'invalid',
            'lng': self.test_lng,
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('message', data['error'])
    
    def test_401_unauthorized(self):
        """Test 401 error handling."""
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        data = response.json()
        self.assertIn('error', data)
    
    def test_500_server_error(self):
        """Test 500 error handling."""
        self.authenticate_user()
        
        # Mock service to raise exception
        with patch('apps.user_portal.services.DiscoveryService.get_nearby_vendors') as mock_service:
            mock_service.side_effect = Exception("Database error")
            
            url = reverse('user_portal:nearby_vendors')
            response = self.client.get(url, {
                'lat': self.test_lat,
                'lng': self.test_lng,
                'radius': 1000
            })
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('message', data['error'])


class UserPortalViewRateLimitTest(UserPortalViewTest):
    """Test cases for rate limiting in views."""
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        
        # Make multiple requests to trigger rate limit
        for i in range(65):  # Exceed limit of 60
            response = self.client.get(url, {
                'lat': self.test_lat,
                'lng': self.test_lng,
                'radius': 1000
            })
            
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                data = response.json()
                self.assertIn('error', data)
                self.assertIn('Rate limit exceeded', data['error']['message'])
                self.assertIn('retry_after', data['error']['details'])
                break
        else:
            self.fail("Rate limit not triggered")
    
    def test_rate_limit_headers(self):
        """Test rate limiting headers."""
        self.authenticate_user()
        
        url = reverse('user_portal:nearby_vendors')
        response = self.client.get(url, {
            'lat': self.test_lat,
            'lng': self.test_lng,
            'radius': 1000
        })
        
        # Should have rate limiting headers
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)
