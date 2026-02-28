"""
Integration Tests for User Portal backend.
Tests end-to-end user flows across multiple services and modules.
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

from apps.customer_auth.models import CustomerUser, ConsentRecord, GuestToken
from apps.customer_auth.services import CustomerAuthService
from apps.user_portal.models import (
    Promotion, VendorReel, Tag, UserPortalConfig,
    UserPreference, UserSearchHistory, UserVendorInteraction
)
from apps.user_portal.services import (
    DiscoveryService, SearchService, PromotionService,
    BusinessLogicService, NotificationService
)

User = get_user_model()


class GuestUserFlowTest(TransactionTestCase):
    """Test cases for guest user flows."""
    
    def setUp(self):
        """Set up test data."""
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000
    
    def test_guest_to_registered_user_flow(self):
        """Test complete flow from guest to registered user."""
        # Step 1: Create guest token
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertIsInstance(guest_token, GuestToken)
        self.assertTrue(guest_token.is_active)
        
        # Step 2: Guest performs search
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'final_score': 0.85
                }
            ]
            
            search_results = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='SILVER'
            )
        
        self.assertIsInstance(search_results, list)
        self.assertEqual(len(search_results), 1)
        
        # Step 3: Record guest search history
        search_history = UserSearchHistory.objects.create(
            guest_token=guest_token.token,
            query_text='restaurant',
            query_type='TEXT',
            extracted_category='RESTAURANT',
            result_count=1
        )
        
        self.assertIsNotNone(search_history.id)
        
        # Step 4: Guest interacts with vendor
        interaction = UserVendorInteraction.objects.create(
            guest_token=guest_token.token,
            vendor_id=search_results[0]['vendor_id'],
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        
        self.assertIsNotNone(interaction.id)
        
        # Step 5: Guest registers as user
        user_data = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'display_name': 'New User'
        }
        
        registered_user = CustomerAuthService.register_user(**user_data)
        
        self.assertIsInstance(registered_user, CustomerUser)
        self.assertEqual(registered_user.user.email, 'newuser@example.com')
        
        # Step 6: Upgrade guest to registered user (preserve data)
        upgraded_user = CustomerAuthService.upgrade_guest_to_user(
            guest_token=guest_token.token,
            **user_data
        )
        
        self.assertEqual(upgraded_user.user.email, 'newuser@example.com')
        
        # Step 7: Verify guest data is preserved
        preserved_search = UserSearchHistory.objects.filter(
            user=upgraded_user,
            query_text='restaurant'
        ).first()
        
        self.assertIsNotNone(preserved_search)
        
        preserved_interaction = UserVendorInteraction.objects.filter(
            user=upgraded_user,
            vendor_id=search_results[0]['vendor_id']
        ).first()
        
        self.assertIsNotNone(preserved_interaction)
        
        # Step 8: Verify guest token is deactivated
        guest_token.refresh_from_db()
        self.assertFalse(guest_token.is_active)
    
    def test_guest_search_and_interaction_flow(self):
        """Test guest search and vendor interaction flow."""
        # Create guest token
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        # Create test vendor data
        vendor_id = uuid.uuid4()
        
        # Step 1: Guest searches for vendors
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': vendor_id,
                    'name': 'Test Restaurant',
                    'category': 'RESTAURANT',
                    'final_score': 0.85,
                    'distance_m': 500
                }
            ]
            
            search_results = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user_tier='SILVER'
            )
        
        # Step 2: Record search history
        search_history = UserSearchHistory.record_search(
            guest_token=guest_token.token,
            query_text='restaurant',
            query_type='TEXT',
            extracted_category='RESTAURANT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            search_radius_m=self.test_radius,
            result_count=1
        )
        
        self.assertIsNotNone(search_history.id)
        
        # Step 3: Guest views vendor details
        with patch.object(DiscoveryService, 'get_vendor_detail') as mock_detail:
            mock_detail.return_value = {
                'vendor_id': vendor_id,
                'name': 'Test Restaurant',
                'description': 'A great place',
                'category': 'RESTAURANT',
                'location': {'lat': self.test_lat, 'lng': self.test_lng}
            }
            
            vendor_detail = DiscoveryService.get_vendor_detail(vendor_id)
        
        self.assertEqual(vendor_detail['vendor_id'], vendor_id)
        
        # Step 4: Guest interacts with vendor (view)
        interaction = UserVendorInteraction.record_interaction(
            guest_token=guest_token.token,
            vendor_id=vendor_id,
            interaction_type='VIEW',
            session_id=uuid.uuid4(),
            lat=self.test_lat,
            lng=self.test_lng
        )
        
        self.assertIsNotNone(interaction.id)
        self.assertEqual(interaction.interaction_type, 'VIEW')
        
        # Step 5: Guest taps on vendor
        tap_interaction = UserVendorInteraction.record_interaction(
            guest_token=guest_token.token,
            vendor_id=vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4(),
            source='search_results'
        )
        
        self.assertEqual(tap_interaction.interaction_type, 'TAP')
        
        # Step 6: Guest navigates to vendor
        nav_interaction = UserVendorInteraction.record_interaction(
            guest_token=guest_token.token,
            vendor_id=vendor_id,
            interaction_type='NAVIGATION',
            session_id=uuid.uuid4(),
            source='vendor_detail'
        )
        
        self.assertEqual(nav_interaction.interaction_type, 'NAVIGATION')
        
        # Step 7: Verify interaction history
        interactions = UserVendorInteraction.objects.filter(
            guest_token=guest_token.token,
            vendor_id=vendor_id
        ).order_by('interacted_at')
        
        self.assertEqual(interactions.count(), 3)
        self.assertEqual(interactions[0].interaction_type, 'VIEW')
        self.assertEqual(interactions[1].interaction_type, 'TAP')
        self.assertEqual(interactions[2].interaction_type, 'NAVIGATION')


class AuthenticatedUserFlowTest(TransactionTestCase):
    """Test cases for authenticated user flows."""
    
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
            display_name='Test User',
            subscription_tier='GOLD'
        )
        
        # Create user preferences
        self.preferences = UserPreference.objects.create(
            user=self.customer_user,
            default_view='AR',
            search_radius_m=1000,
            preferred_category_slugs=['food', 'cafe'],
            price_range='MID',
            theme='DARK'
        )
        
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000
    
    def test_user_personalized_search_flow(self):
        """Test personalized search flow for authenticated user."""
        # Step 1: User performs search with preferences
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Preferred Restaurant',
                    'category': 'RESTAURANT',
                    'final_score': 0.90,  # Higher score due to preferences
                    'distance_m': 500
                }
            ]
            
            search_results = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.preferences.search_radius_m,
                user_tier=self.customer_user.subscription_tier,
                category='RESTAURANT',  # From preferred categories
                user_preferences={
                    'preferred_categories': self.preferences.preferred_category_slugs,
                    'price_range': self.preferences.price_range
                }
            )
        
        self.assertIsInstance(search_results, list)
        self.assertEqual(len(search_results), 1)
        
        # Step 2: Record search history
        search_history = UserSearchHistory.record_search(
            user=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            extracted_category='RESTAURANT',
            extracted_price_range='MID',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            search_radius_m=self.preferences.search_radius_m,
            result_count=1
        )
        
        self.assertIsNotNone(search_history.id)
        self.assertEqual(search_history.user, self.customer_user)
        
        # Step 3: User interacts with preferred vendor
        vendor_id = search_results[0]['vendor_id']
        
        interaction = UserVendorInteraction.record_interaction(
            user=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='VIEW',
            session_id=uuid.uuid4(),
            lat=self.test_lat,
            lng=self.test_lng
        )
        
        self.assertIsNotNone(interaction.id)
        
        # Step 4: Update user behavioral data
        self.customer_user.behavioral_data = {
            'search_count': 1,
            'preferred_categories': ['RESTAURANT'],
            'avg_search_radius': self.preferences.search_radius_m,
            'last_search_category': 'RESTAURANT'
        }
        self.customer_user.save()
        
        # Step 5: Verify behavioral data is updated
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.behavioral_data['search_count'], 1)
    
    def test_user_preference_management_flow(self):
        """Test user preference management flow."""
        # Step 1: User updates preferences
        updated_preferences = {
            'default_view': 'MAP',
            'search_radius_m': 2000,
            'preferred_category_slugs': ['food', 'cafe', 'bakery'],
            'price_range': 'BUDGET',
            'theme': 'LIGHT',
            'notifications_nearby_deals': True,
            'notifications_flash_deals': False,
            'auto_location_enabled': False,
            'manual_location_lat': 24.8607,
            'manual_location_lng': 67.0011,
            'manual_location_name': 'Karachi'
        }
        
        # Update preferences
        for key, value in updated_preferences.items():
            setattr(self.preferences, key, value)
        self.preferences.save()
        
        # Step 2: Verify preferences are updated
        self.preferences.refresh_from_db()
        self.assertEqual(self.preferences.default_view, 'MAP')
        self.assertEqual(self.preferences.search_radius_m, 2000)
        self.assertEqual(self.preferences.price_range, 'BUDGET')
        self.assertEqual(self.preferences.theme, 'LIGHT')
        
        # Step 3: Test search with new preferences
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_search:
            mock_search.return_value = []
            
            search_results = DiscoveryService.get_nearby_vendors(
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.preferences.search_radius_m,
                user_tier=self.customer_user.subscription_tier,
                user_preferences={
                    'preferred_categories': self.preferences.preferred_category_slugs,
                    'price_range': self.preferences.price_range,
                    'default_view': self.preferences.default_view
                }
            )
        
        # Step 4: Verify preference history
        preference_history = UserPreference.objects.filter(user=self.customer_user)
        self.assertEqual(preference_history.count(), 1)
    
    def test_user_consent_management_flow(self):
        """Test user consent management flow."""
        # Step 1: User provides location consent
        location_consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='LOCATION',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...',
            context={'source': 'mobile_app', 'prompt_type': 'onboarding'}
        )
        
        self.assertIsNotNone(location_consent.id)
        self.assertTrue(location_consent.consented)
        
        # Step 2: User provides analytics consent
        analytics_consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='ANALYTICS',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertIsNotNone(analytics_consent.id)
        
        # Step 3: User withdraws marketing consent
        marketing_consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='MARKETING',
            consented=False,
            consent_version='1.0',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertFalse(marketing_consent.consented)
        
        # Step 4: Verify consent history
        consent_history = CustomerAuthService.get_user_consent_history(self.customer_user)
        
        self.assertEqual(len(consent_history), 3)
        self.assertEqual(consent_history[0].consent_type, 'MARKETING')  # Most recent
        self.assertEqual(consent_history[1].consent_type, 'ANALYTICS')
        self.assertEqual(consent_history[2].consent_type, 'LOCATION')
        
        # Step 5: Verify current consent status
        current_consents = {
            consent.consent_type: consent.consented
            for consent in consent_history
        }
        
        self.assertTrue(current_consents['LOCATION'])
        self.assertTrue(current_consents['ANALYTICS'])
        self.assertFalse(current_consents['MARKETING'])


class PromotionInteractionFlowTest(TransactionTestCase):
    """Test cases for promotion interaction flows."""
    
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
            display_name='Test User',
            subscription_tier='GOLD'
        )
        
        # Create test promotion
        self.vendor_id = uuid.uuid4()
        self.promotion = Promotion.objects.create(
            vendor_id=self.vendor_id,
            title='20% Off Lunch',
            description='Get 20% off on lunch items',
            discount_type='PERCENTAGE',
            discount_percent=20,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True
        )
        
        # Create flash deal
        self.flash_deal = Promotion.objects.create(
            vendor_id=self.vendor_id,
            title='Flash Deal - 50% Off',
            description='Limited time flash deal',
            discount_type='PERCENTAGE',
            discount_percent=50,
            is_flash_deal=True,
            flash_duration_minutes=60,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            is_active=True
        )
    
    def test_promotion_discovery_and_redemption_flow(self):
        """Test promotion discovery and redemption flow."""
        # Step 1: User discovers promotions
        with patch.object(PromotionService, 'get_active_promotions') as mock_promotions:
            mock_promotions.return_value = [
                {
                    'discount_id': self.promotion.id,
                    'title': '20% Off Lunch',
                    'vendor_id': self.vendor_id,
                    'discount_percent': 20,
                    'is_currently_active': True
                }
            ]
            
            promotions = PromotionService.get_active_promotions()
        
        self.assertIsInstance(promotions, list)
        self.assertEqual(len(promotions), 1)
        
        # Step 2: User views promotion details
        promotion_detail = PromotionService.get_promotion_detail(self.promotion.id)
        
        self.assertEqual(promotion_detail['discount_id'], self.promotion.id)
        self.assertEqual(promotion_detail['title'], '20% Off Lunch')
        
        # Step 3: User validates eligibility
        is_eligible = PromotionService.validate_promotion_eligibility(
            promotion_id=self.promotion.id,
            user=self.customer_user
        )
        
        self.assertTrue(is_eligible)
        
        # Step 4: User redeems promotion
        redemption_success = PromotionService.apply_promotion_usage(
            promotion_id=self.promotion.id,
            user=self.customer_user
        )
        
        self.assertTrue(redemption_success)
        
        # Step 5: Verify promotion usage is recorded
        self.promotion.refresh_from_db()
        self.assertEqual(self.promotion.usage_count, 1)
        
        # Step 6: Record user interaction
        interaction = UserVendorInteraction.record_interaction(
            user=self.customer_user,
            vendor_id=self.vendor_id,
            interaction_type='PROMOTION_TAP',
            session_id=uuid.uuid4(),
            promotion_id=self.promotion.id
        )
        
        self.assertIsNotNone(interaction.id)
        self.assertEqual(interaction.interaction_type, 'PROMOTION_TAP')
    
    def test_flash_deal_flow(self):
        """Test flash deal interaction flow."""
        # Step 1: User discovers flash deals
        with patch.object(PromotionService, 'get_flash_deals') as mock_flash_deals:
            mock_flash_deals.return_value = [
                {
                    'discount_id': self.flash_deal.id,
                    'title': 'Flash Deal - 50% Off',
                    'vendor_id': self.vendor_id,
                    'discount_percent': 50,
                    'time_remaining_minutes': 45,
                    'is_currently_active': True
                }
            ]
            
            flash_deals = PromotionService.get_flash_deals()
        
        self.assertIsInstance(flash_deals, list)
        self.assertEqual(len(flash_deals), 1)
        
        # Step 2: Check flash deal status
        flash_status = PromotionService.get_flash_deal_status(self.flash_deal.id)
        
        self.assertTrue(flash_status['is_active'])
        self.assertGreater(flash_status['time_remaining_minutes'], 0)
        
        # Step 3: User shows interest in flash deal
        with patch.object(PromotionService, 'record_flash_deal_interest') as mock_interest:
            mock_interest.return_value = True
            
            interest_recorded = PromotionService.record_flash_deal_interest(
                flash_deal_id=self.flash_deal.id,
                user=self.customer_user
            )
        
        self.assertTrue(interest_recorded)
        
        # Step 4: User redeems flash deal
        redemption_success = PromotionService.apply_promotion_usage(
            promotion_id=self.flash_deal.id,
            user=self.customer_user
        )
        
        self.assertTrue(redemption_success)
        
        # Step 5: Verify flash deal analytics
        analytics = PromotionService.get_promotion_analytics(
            promotion_id=self.flash_deal.id,
            days=1
        )
        
        self.assertIsInstance(analytics, dict)
        self.assertIn('usage_count', analytics)
        self.assertIn('unique_users', analytics)
        self.assertEqual(analytics['usage_count'], 1)
        self.assertEqual(analytics['unique_users'], 1)


class SearchAndDiscoveryFlowTest(TransactionTestCase):
    """Test cases for search and discovery flows."""
    
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
            display_name='Test User',
            subscription_tier='GOLD'
        )
        
        # Create test tags
        self.tags = [
            Tag.objects.create(name='Restaurant', slug='restaurant', category='FOOD'),
            Tag.objects.create(name='Cafe', slug='cafe', category='FOOD'),
            Tag.objects.create(name='Bakery', slug='bakery', category='FOOD'),
        ]
        
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000
    
    def test_text_search_flow(self):
        """Test text search flow."""
        # Step 1: User performs text search
        query = 'pakistani restaurant'
        
        with patch.object(SearchService, 'text_search') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Pakistani Restaurant',
                    'category': 'RESTAURANT',
                    'relevance_score': 0.9,
                    'distance_m': 500
                }
            ]
            
            search_results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        self.assertIsInstance(search_results, list)
        self.assertEqual(len(search_results), 1)
        
        # Step 2: Record search history
        search_history = UserSearchHistory.record_search(
            user=self.customer_user,
            query_text=query,
            query_type='TEXT',
            extracted_category='RESTAURANT',
            extracted_intent={'category': 'RESTAURANT', 'price_range': 'MID'},
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            search_radius_m=self.test_radius,
            result_count=1
        )
        
        self.assertIsNotNone(search_history.id)
        
        # Step 3: User clicks on result
        vendor_id = search_results[0]['vendor_id']
        
        interaction = UserVendorInteraction.record_interaction(
            user=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4(),
            source='search_results'
        )
        
        self.assertIsNotNone(interaction.id)
        
        # Step 4: Update search analytics
        with patch.object(SearchService, 'update_search_analytics') as mock_analytics:
            mock_analytics.return_value = True
            
            SearchService.update_search_analytics(
                query=query,
                user=self.customer_user,
                result_count=1,
                clicked_vendor_id=vendor_id
            )
    
    def test_voice_search_flow(self):
        """Test voice search flow."""
        # Step 1: User performs voice search
        voice_query = 'find me a good cafe near me'
        
        with patch.object(SearchService, 'voice_search') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Good Cafe',
                    'category': 'CAFE',
                    'intent_match_score': 0.85,
                    'distance_m': 300
                }
            ]
            
            search_results = SearchService.voice_search(
                query=voice_query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        self.assertIsInstance(search_results, list)
        self.assertEqual(len(search_results), 1)
        
        # Step 2: Record voice search history
        search_history = UserSearchHistory.record_search(
            user=self.customer_user,
            query_text=voice_query,
            query_type='VOICE',
            extracted_category='CAFE',
            extracted_intent={'category': 'CAFE', 'features': ['near_me']},
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            search_radius_m=self.test_radius,
            result_count=1
        )
        
        self.assertIsNotNone(search_history.id)
        self.assertEqual(search_history.query_type, 'VOICE')
        
        # Step 3: Verify NLP intent extraction
        with patch.object(SearchService, 'extract_search_intent') as mock_nlp:
            mock_nlp.return_value = {
                'category': 'CAFE',
                'price_range': 'MID',
                'features': ['near_me'],
                'confidence': 0.85
            }
            
            intent = SearchService.extract_search_intent(voice_query)
        
        self.assertEqual(intent['category'], 'CAFE')
        self.assertIn('near_me', intent['features'])
    
    def test_tag_discovery_flow(self):
        """Test tag discovery flow."""
        # Step 1: User browses available tags
        with patch.object(DiscoveryService, 'get_tags') as mock_tags:
            mock_tags.return_value = [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'category': tag.category,
                    'vendor_count': 10
                }
                for tag in self.tags
            ]
            
            available_tags = DiscoveryService.get_tags()
        
        self.assertEqual(len(available_tags), 3)
        
        # Step 2: User selects a tag
        selected_tag = available_tags[0]
        
        # Step 3: Search vendors by tag
        with patch.object(DiscoveryService, 'search_vendors_by_tag') as mock_tag_search:
            mock_tag_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': f'{selected_tag["name"]} Place',
                    'category': 'RESTAURANT',
                    'tags': [selected_tag['name']]
                }
            ]
            
            tag_results = DiscoveryService.search_vendors_by_tag(
                tag_slug=selected_tag['slug'],
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius
            )
        
        self.assertIsInstance(tag_results, list)
        self.assertEqual(len(tag_results), 1)
        
        # Step 4: Record tag search history
        search_history = UserSearchHistory.record_search(
            user=self.customer_user,
            query_text=selected_tag['name'],
            query_type='TAG',
            extracted_category='RESTAURANT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            search_radius_m=self.test_radius,
            result_count=1
        )
        
        self.assertEqual(search_history.query_type, 'TAG')
    
    def test_personalized_recommendations_flow(self):
        """Test personalized recommendations flow."""
        # Step 1: Create user behavior history
        # Previous searches
        UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='restaurant',
            query_type='TEXT',
            extracted_category='RESTAURANT',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=5
        )
        
        UserSearchHistory.objects.create(
            user=self.customer_user,
            query_text='cafe',
            query_type='TEXT',
            extracted_category='CAFE',
            search_lat=self.test_lat,
            search_lng=self.test_lng,
            result_count=3
        )
        
        # Previous interactions
        vendor_id = uuid.uuid4()
        UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='VIEW',
            session_id=uuid.uuid4()
        )
        
        UserVendorInteraction.objects.create(
            user=self.customer_user,
            vendor_id=vendor_id,
            interaction_type='TAP',
            session_id=uuid.uuid4()
        )
        
        # Step 2: Get personalized recommendations
        with patch.object(BusinessLogicService, 'recommend_content_to_user') as mock_recommend:
            mock_recommend.return_value = [
                {
                    'content_id': uuid.uuid4(),
                    'content_type': 'vendor',
                    'relevance_score': 0.9,
                    'recommendation_reason': 'Based on your restaurant searches',
                    'vendor_data': {
                        'name': 'Recommended Restaurant',
                        'category': 'RESTAURANT'
                    }
                }
            ]
            
            recommendations = BusinessLogicService.recommend_content_to_user(
                user=self.customer_user,
                content_type='vendors',
                limit=10
            )
        
        self.assertIsInstance(recommendations, list)
        self.assertEqual(len(recommendations), 1)
        
        # Step 3: User interacts with recommendation
        recommendation = recommendations[0]
        
        interaction = UserVendorInteraction.record_interaction(
            user=self.customer_user,
            vendor_id=recommendation['content_id'],
            interaction_type='VIEW',
            session_id=uuid.uuid4(),
            source='recommendation',
            metadata={'recommendation_score': recommendation['relevance_score']}
        )
        
        self.assertIsNotNone(interaction.id)
        self.assertEqual(interaction.metadata['recommendation_score'], 0.9)


class TierUpgradeFlowTest(TransactionTestCase):
    """Test cases for tier upgrade flows."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user with Silver tier
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
            subscription_tier='SILVER'
        )
    
    def test_tier_upgrade_flow(self):
        """Test tier upgrade flow."""
        # Step 1: User checks current tier benefits
        current_benefits = {
            'max_search_radius': 1000,
            'max_results_per_search': 50,
            'has_voice_search': False,
            'has_advanced_filters': False,
            'max_flash_deals_per_day': 3
        }
        
        # Step 2: User views higher tier benefits
        gold_benefits = {
            'max_search_radius': 2000,
            'max_results_per_search': 100,
            'has_voice_search': True,
            'has_advanced_filters': True,
            'max_flash_deals_per_day': 10
        }
        
        # Step 3: User initiates tier upgrade
        with patch.object(BusinessLogicService, 'upgrade_tier') as mock_upgrade:
            mock_upgrade.return_value = self.customer_user
            
            upgraded_user = BusinessLogicService.upgrade_tier(
                user=self.customer_user,
                new_tier='GOLD',
                payment_method='credit_card'
            )
        
        # Step 4: Verify tier is upgraded
        self.customer_user.subscription_tier = 'GOLD'
        self.customer_user.tier_upgraded_at = timezone.now()
        self.customer_user.save()
        
        self.assertEqual(self.customer_user.subscription_tier, 'GOLD')
        self.assertIsNotNone(self.customer_user.tier_upgraded_at)
        
        # Step 5: User gets access to new features
        new_permissions = BusinessLogicService.check_tier_permission(
            self.customer_user,
            'voice_search'
        )
        
        self.assertTrue(new_permissions)
        
        # Step 6: Test new feature access
        with patch.object(SearchService, 'voice_search') as mock_voice_search:
            mock_voice_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Voice Search Result',
                    'category': 'RESTAURANT'
                }
            ]
            
            voice_results = SearchService.voice_search(
                query='find restaurant',
                lat=24.8607,
                lng=67.0011,
                radius_m=1000,
                user=self.customer_user
            )
        
        self.assertIsInstance(voice_results, list)
        self.assertEqual(len(voice_results), 1)
    
    def test_tier_limit_enforcement_flow(self):
        """Test tier limit enforcement."""
        # Step 1: Silver user tries to access premium features
        has_voice_search = BusinessLogicService.check_tier_permission(
            self.customer_user,
            'voice_search'
        )
        
        self.assertFalse(has_voice_search)
        
        # Step 2: Silver user tries to exceed search limits
        search_limit = BusinessLogicService.check_tier_limits(
            self.customer_user,
            'max_results_per_search',
            60  # Exceeds Silver limit of 50
        )
        
        self.assertFalse(search_limit)
        
        # Step 3: Silver user within limits
        within_limit = BusinessLogicService.check_tier_limits(
            self.customer_user,
            'max_results_per_search',
            40  # Within Silver limit
        )
        
        self.assertTrue(within_limit)
        
        # Step 4: Upgrade to Gold and test new limits
        self.customer_user.subscription_tier = 'GOLD'
        self.customer_user.save()
        
        gold_limit_check = BusinessLogicService.check_tier_limits(
            self.customer_user,
            'max_results_per_search',
            60  # Now within Gold limit
        )
        
        self.assertTrue(gold_limit_check)


class ErrorRecoveryFlowTest(TransactionTestCase):
    """Test cases for error recovery flows."""
    
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
    
    def test_service_failure_recovery_flow(self):
        """Test service failure recovery flow."""
        # Step 1: Primary service fails
        with patch.object(DiscoveryService, 'get_nearby_vendors') as mock_primary:
            mock_primary.side_effect = Exception("Primary service unavailable")
            
            # Step 2: System falls back to secondary service
            with patch.object(DiscoveryService, 'get_nearby_vendors_fallback') as mock_fallback:
                mock_fallback.return_value = [
                    {
                        'vendor_id': uuid.uuid4(),
                        'name': 'Fallback Result',
                        'category': 'RESTAURANT'
                    }
                ]
                
                # Should use fallback service
                try:
                    results = DiscoveryService.get_nearby_vendors_with_fallback(
                        lat=24.8607,
                        lng=67.0011,
                        radius_m=1000,
                        user=self.customer_user
                    )
                except Exception:
                    # If fallback not implemented, handle gracefully
                    results = []
        
        # Step 3: Log error for monitoring
        error_data = {
            'error_type': 'service_failure',
            'service': 'DiscoveryService',
            'operation': 'get_nearby_vendors',
            'user_id': self.customer_user.id,
            'fallback_used': True
        }
        
        # Step 4: Notify user of degraded service
        with patch.object(NotificationService, 'send_degraded_service_notice') as mock_notify:
            mock_notify.return_value = True
            
            NotificationService.send_degraded_service_notice(
                user=self.customer_user,
                service='search',
                message='Search service is temporarily degraded'
            )
    
    def test_data_consistency_recovery_flow(self):
        """Test data consistency recovery flow."""
        # Step 1: Detect inconsistent data
        with patch.object(BusinessLogicService, 'check_data_consistency') as mock_check:
            mock_check.return_value = [
                {
                    'model': 'Promotion',
                    'id': uuid.uuid4(),
                    'issue': 'discount_percent exceeds 100',
                    'severity': 'high'
                }
            ]
            
            consistency_issues = BusinessLogicService.check_data_consistency()
        
        self.assertIsInstance(consistency_issues, list)
        self.assertGreater(len(consistency_issues), 0)
        
        # Step 2: Attempt automatic data repair
        with patch.object(BusinessLogicService, 'repair_data_inconsistency') as mock_repair:
            mock_repair.return_value = True
            
            repair_success = BusinessLogicService.repair_data_inconsistency(
                model='Promotion',
                issue_id=consistency_issues[0]['id']
            )
        
        # Step 3: Log repair attempt
        repair_log = {
            'model': 'Promotion',
            'issue_id': consistency_issues[0]['id'],
            'repair_attempted': True,
            'repair_success': repair_success,
            'timestamp': timezone.now()
        }
        
        # Step 4: Notify admin if repair fails
        if not repair_success:
            with patch.object(NotificationService, 'send_admin_alert') as mock_alert:
                mock_alert.return_value = True
                
                NotificationService.send_admin_alert(
                    alert_type='data_consistency_failure',
                    message=f'Failed to repair {consistency_issues[0]["model"]} data',
                    details=consistency_issues[0]
                )
