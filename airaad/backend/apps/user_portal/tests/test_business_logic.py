"""
Unit tests for Business Logic.
Tests promotions, flash deals, and tier gating functionality.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.customer_auth.models import CustomerUser
from apps.user_portal.models import Promotion, VendorReel, Tag, UserPortalConfig
from apps.user_portal.services import (
    PromotionService, FlashDealService, TierService,
    BusinessLogicService, PricingService
)

User = get_user_model()


class PromotionServiceTest(TestCase):
    """Test cases for PromotionService."""
    
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
        
        # Create test vendor ID
        self.vendor_id = uuid.uuid4()
        
        # Create test promotions
        self.active_promotion = Promotion.objects.create(
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
        
        self.expired_promotion = Promotion.objects.create(
            vendor_id=self.vendor_id,
            title='Expired Deal',
            description='This deal has expired',
            discount_type='PERCENTAGE',
            discount_percent=15,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(days=5),
            end_time=timezone.now() - timedelta(days=1),
            is_active=True
        )
    
    def test_get_active_promotions(self):
        """Test getting active promotions."""
        active_promotions = PromotionService.get_active_promotions()
        
        self.assertIsInstance(active_promotions, list)
        self.assertGreater(len(active_promotions), 0)
        
        # Should include active promotion and flash deal
        promotion_ids = [p['discount_id'] for p in active_promotions]
        self.assertIn(self.active_promotion.id, promotion_ids)
        self.assertIn(self.flash_deal.id, promotion_ids)
        
        # Should not include expired promotion
        self.assertNotIn(self.expired_promotion.id, promotion_ids)
    
    def test_get_promotions_by_vendor(self):
        """Test getting promotions by vendor."""
        vendor_promotions = PromotionService.get_promotions_by_vendor(self.vendor_id)
        
        self.assertIsInstance(vendor_promotions, list)
        self.assertEqual(len(vendor_promotions), 3)  # All promotions for this vendor
        
        # Check structure
        for promotion in vendor_promotions:
            self.assertIn('discount_id', promotion)
            self.assertIn('title', promotion)
            self.assertIn('discount_type', promotion)
            self.assertIn('is_currently_active', promotion)
    
    def test_get_flash_deals(self):
        """Test getting flash deals."""
        flash_deals = PromotionService.get_flash_deals()
        
        self.assertIsInstance(flash_deals, list)
        self.assertEqual(len(flash_deals), 1)  # Only one active flash deal
        
        # Check structure
        flash_deal = flash_deals[0]
        self.assertIn('discount_id', flash_deal)
        self.assertIn('title', flash_deal)
        self.assertIn('flash_duration_minutes', flash_deal)
        self.assertIn('time_remaining_minutes', flash_deal)
        self.assertTrue(flash_deal['is_flash_deal'])
    
    def test_calculate_discount_percentage(self):
        """Test percentage discount calculation."""
        original_price = Decimal('100.00')
        discount_percent = 20
        
        discounted_price = PromotionService.calculate_discount(
            original_price=original_price,
            discount_type='PERCENTAGE',
            discount_percent=discount_percent
        )
        
        expected_price = Decimal('80.00')  # 100 - 20% of 100
        self.assertEqual(discounted_price, expected_price)
    
    def test_calculate_discount_fixed(self):
        """Test fixed amount discount calculation."""
        original_price = Decimal('100.00')
        discount_amount = Decimal('15.00')
        
        discounted_price = PromotionService.calculate_discount(
            original_price=original_price,
            discount_type='FIXED',
            discount_amount=discount_amount
        )
        
        expected_price = Decimal('85.00')  # 100 - 15
        self.assertEqual(discounted_price, expected_price)
    
    def test_calculate_discount_bogo(self):
        """Test BOGO discount calculation."""
        original_price = Decimal('100.00')
        
        discounted_price = PromotionService.calculate_discount(
            original_price=original_price,
            discount_type='BOGO'
        )
        
        # BOGO should give 50% off (buy one get one free)
        expected_price = Decimal('50.00')
        self.assertEqual(discounted_price, expected_price)
    
    def test_calculate_discount_free_item(self):
        """Test free item discount calculation."""
        original_price = Decimal('100.00')
        free_item_value = Decimal('25.00')
        
        discounted_price = PromotionService.calculate_discount(
            original_price=original_price,
            discount_type='FREE_ITEM',
            free_item_value=free_item_value
        )
        
        expected_price = Decimal('75.00')  # 100 - 25
        self.assertEqual(discounted_price, expected_price)
    
    def test_validate_promotion_eligibility(self):
        """Test promotion eligibility validation."""
        # Test eligible promotion
        is_eligible = PromotionService.validate_promotion_eligibility(
            promotion_id=self.active_promotion.id,
            user=self.customer_user
        )
        self.assertTrue(is_eligible)
        
        # Test expired promotion
        is_eligible_expired = PromotionService.validate_promotion_eligibility(
            promotion_id=self.expired_promotion.id,
            user=self.customer_user
        )
        self.assertFalse(is_eligible_expired)
        
        # Test non-existent promotion
        fake_id = uuid.uuid4()
        is_eligible_fake = PromotionService.validate_promotion_eligibility(
            promotion_id=fake_id,
            user=self.customer_user
        )
        self.assertFalse(is_eligible_fake)
    
    def test_apply_promotion_usage(self):
        """Test applying promotion usage."""
        initial_usage = self.active_promotion.usage_count
        
        # Apply promotion
        success = PromotionService.apply_promotion_usage(
            promotion_id=self.active_promotion.id,
            user=self.customer_user
        )
        
        self.assertTrue(success)
        
        # Check usage count increased
        self.active_promotion.refresh_from_db()
        self.assertEqual(self.active_promotion.usage_count, initial_usage + 1)
    
    def test_get_promotion_analytics(self):
        """Test promotion analytics."""
        analytics = PromotionService.get_promotion_analytics(
            promotion_id=self.active_promotion.id,
            days=30
        )
        
        self.assertIsInstance(analytics, dict)
        self.assertIn('usage_count', analytics)
        self.assertIn('unique_users', analytics)
        self.assertIn('conversion_rate', analytics)
        self.assertIn('daily_usage', analytics)
    
    def test_promotion_expiration_handling(self):
        """Test promotion expiration handling."""
        # Create promotion that will expire soon
        soon_expiring = Promotion.objects.create(
            vendor_id=self.vendor_id,
            title='Soon Expiring',
            description='Expires in 1 hour',
            discount_type='PERCENTAGE',
            discount_percent=10,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        
        # Check if it's detected as expiring soon
        expiring_soon = PromotionService.get_expiring_promotions(hours=2)
        
        expiring_ids = [p['discount_id'] for p in expiring_soon]
        self.assertIn(soon_expiring.id, expiring_ids)


class FlashDealServiceTest(TestCase):
    """Test cases for FlashDealService."""
    
    def setUp(self):
        """Set up test data."""
        self.vendor_id = uuid.uuid4()
        
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
    
    def test_create_flash_deal(self):
        """Test flash deal creation."""
        flash_deal_data = {
            'vendor_id': self.vendor_id,
            'title': 'New Flash Deal',
            'description': 'New flash deal description',
            'discount_type': 'PERCENTAGE',
            'discount_percent': 30,
            'flash_duration_minutes': 120
        }
        
        new_flash_deal = FlashDealService.create_flash_deal(**flash_deal_data)
        
        self.assertIsInstance(new_flash_deal, Promotion)
        self.assertTrue(new_flash_deal.is_flash_deal)
        self.assertEqual(new_flash_deal.title, 'New Flash Deal')
        self.assertEqual(new_flash_deal.flash_duration_minutes, 120)
        self.assertTrue(new_flash_deal.is_active)
    
    def test_extend_flash_deal(self):
        """Test flash deal extension."""
        original_end_time = self.flash_deal.end_time
        
        # Extend by 30 minutes
        extended_deal = FlashDealService.extend_flash_deal(
            flash_deal_id=self.flash_deal.id,
            additional_minutes=30
        )
        
        self.flash_deal.refresh_from_db()
        self.assertGreater(self.flash_deal.end_time, original_end_time)
        self.assertEqual(
            self.flash_deal.end_time - original_end_time,
            timedelta(minutes=30)
        )
    
    def test_end_flash_deal_early(self):
        """Test ending flash deal early."""
        # End flash deal early
        success = FlashDealService.end_flash_deal_early(self.flash_deal.id)
        
        self.assertTrue(success)
        
        self.flash_deal.refresh_from_db()
        self.assertLess(self.flash_deal.end_time, timezone.now())
        self.assertFalse(self.flash_deal.is_active)
    
    def test_get_flash_deal_status(self):
        """Test flash deal status."""
        status = FlashDealService.get_flash_deal_status(self.flash_deal.id)
        
        self.assertIsInstance(status, dict)
        self.assertIn('is_active', status)
        self.assertIn('time_remaining_minutes', status)
        self.assertIn('time_remaining_seconds', status)
        self.assertIn('usage_count', status)
        self.assertIn('max_usage', status)
        self.assertTrue(status['is_active'])
        self.assertGreater(status['time_remaining_minutes'], 0)
    
    def test_get_flash_deal_participants(self):
        """Test getting flash deal participants."""
        participants = FlashDealService.get_flash_deal_participants(self.flash_deal.id)
        
        self.assertIsInstance(participants, list)
        # Should be empty initially since no usage recorded yet
    
    def test_flash_deal_notification_trigger(self):
        """Test flash deal notification trigger."""
        with patch.object(FlashDealService, '_send_flash_deal_notification') as mock_notify:
            mock_notify.return_value = True
            
            success = FlashDealService.trigger_flash_deal_notification(
                flash_deal_id=self.flash_deal.id,
                notification_type='STARTED'
            )
        
        self.assertTrue(success)
        mock_notify.assert_called_once()
    
    def test_flash_deal_analytics(self):
        """Test flash deal analytics."""
        analytics = FlashDealService.get_flash_deal_analytics(self.flash_deal.id)
        
        self.assertIsInstance(analytics, dict)
        self.assertIn('total_usage', analytics)
        self.assertIn('unique_participants', analytics)
        self.assertIn('participation_rate', analytics)
        self.assertIn('peak_usage_time', analytics)
        self.assertIn('usage_timeline', analytics)


class TierServiceTest(TestCase):
    """Test cases for TierService."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users with different tiers
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
        
        self.diamond_user = User.objects.create_user(
            username='diamond@example.com',
            email='diamond@example.com',
            password='testpass123'
        )
        self.diamond_customer = CustomerUser.objects.create(
            user=self.diamond_user,
            display_name='Diamond User',
            subscription_tier='DIAMOND'
        )
        
        self.platinum_user = User.objects.create_user(
            username='platinum@example.com',
            email='platinum@example.com',
            password='testpass123'
        )
        self.platinum_customer = CustomerUser.objects.create(
            user=self.platinum_user,
            display_name='Platinum User',
            subscription_tier='PLATINUM'
        )
    
    def test_get_tier_limits(self):
        """Test tier limits."""
        # Test Silver tier limits
        silver_limits = TierService.get_tier_limits('SILVER')
        self.assertIn('max_search_radius', silver_limits)
        self.assertIn('max_results_per_search', silver_limits)
        self.assertIn('max_flash_deals_per_day', silver_limits)
        self.assertIn('has_voice_search', silver_limits)
        self.assertIn('has_advanced_filters', silver_limits)
        
        # Test Gold tier limits (should be higher than Silver)
        gold_limits = TierService.get_tier_limits('GOLD')
        self.assertGreaterEqual(
            gold_limits['max_results_per_search'],
            silver_limits['max_results_per_search']
        )
        self.assertTrue(gold_limits['has_voice_search'])
        
        # Test Diamond tier limits (should be higher than Gold)
        diamond_limits = TierService.get_tier_limits('DIAMOND')
        self.assertGreaterEqual(
            diamond_limits['max_results_per_search'],
            gold_limits['max_results_per_search']
        )
        
        # Test Platinum tier limits (highest)
        platinum_limits = TierService.get_tier_limits('PLATINUM')
        self.assertGreaterEqual(
            platinum_limits['max_results_per_search'],
            diamond_limits['max_results_per_search']
        )
    
    def test_check_tier_permission(self):
        """Test tier permission checking."""
        # Test Silver user permissions
        self.assertTrue(TierService.check_tier_permission(
            self.silver_customer, 'basic_search'
        ))
        self.assertFalse(TierService.check_tier_permission(
            self.silver_customer, 'voice_search'
        ))
        
        # Test Gold user permissions
        self.assertTrue(TierService.check_tier_permission(
            self.gold_customer, 'basic_search'
        ))
        self.assertTrue(TierService.check_tier_permission(
            self.gold_customer, 'voice_search'
        ))
        self.assertFalse(TierService.check_tier_permission(
            self.gold_customer, 'advanced_analytics'
        ))
        
        # Test Diamond user permissions
        self.assertTrue(TierService.check_tier_permission(
            self.diamond_customer, 'advanced_analytics'
        ))
        self.assertTrue(TierService.check_tier_permission(
            self.diamond_customer, 'bulk_operations'
        ))
        
        # Test Platinum user permissions (should have all)
        self.assertTrue(TierService.check_tier_permission(
            self.platinum_customer, 'bulk_operations'
        ))
        self.assertTrue(TierService.check_tier_permission(
            self.platinum_customer, 'api_access'
        ))
    
    def test_upgrade_tier(self):
        """Test tier upgrade."""
        # Upgrade Silver to Gold
        upgraded_user = TierService.upgrade_tier(
            self.silver_customer,
            new_tier='GOLD',
            payment_method='credit_card'
        )
        
        self.assertEqual(upgraded_user.subscription_tier, 'GOLD')
        self.assertIsNotNone(upgraded_user.tier_upgraded_at)
        
        # Should have new permissions
        self.assertTrue(TierService.check_tier_permission(
            upgraded_user, 'voice_search'
        ))
    
    def test_downgrade_tier(self):
        """Test tier downgrade."""
        # Downgrade Platinum to Gold
        downgraded_user = TierService.downgrade_tier(
            self.platinum_customer,
            new_tier='GOLD'
        )
        
        self.assertEqual(downgraded_user.subscription_tier, 'GOLD')
        self.assertIsNotNone(downgraded_user.tier_downgraded_at)
        
        # Should lose some permissions
        self.assertFalse(TierService.check_tier_permission(
            downgraded_user, 'api_access'
        ))
    
    def test_get_tier_benefits(self):
        """Test tier benefits."""
        benefits = TierService.get_tier_benefits()
        
        self.assertIsInstance(benefits, dict)
        self.assertIn('SILVER', benefits)
        self.assertIn('GOLD', benefits)
        self.assertIn('DIAMOND', benefits)
        self.assertIn('PLATINUM', benefits)
        
        # Check benefit structure
        silver_benefits = benefits['SILVER']
        self.assertIsInstance(silver_benefits, list)
        self.assertGreater(len(silver_benefits), 0)
        
        # Higher tiers should have more benefits
        self.assertGreaterEqual(
            len(benefits['GOLD']),
            len(benefits['SILVER'])
        )
        self.assertGreaterEqual(
            len(benefits['DIAMOND']),
            len(benefits['GOLD'])
        )
        self.assertGreaterEqual(
            len(benefits['PLATINUM']),
            len(benefits['DIAMOND'])
        )
    
    def test_tier_usage_tracking(self):
        """Test tier usage tracking."""
        # Track usage for Silver user
        TierService.track_tier_usage(
            self.silver_customer,
            feature='basic_search',
            usage_count=1
        )
        
        # Get usage statistics
        usage_stats = TierService.get_tier_usage_stats(
            self.silver_customer,
            days=30
        )
        
        self.assertIsInstance(usage_stats, dict)
        self.assertIn('total_usage', usage_stats)
        self.assertIn('feature_breakdown', usage_stats)
        self.assertIn('daily_usage', usage_stats)
    
    def test_tier_limit_enforcement(self):
        """Test tier limit enforcement."""
        # Test Silver user limit enforcement
        with patch.object(TierService, '_check_daily_limit') as mock_limit:
            mock_limit.return_value = False  # Limit exceeded
            
            success = TierService.enforce_tier_limit(
                self.silver_customer,
                feature='basic_search',
                increment=1
            )
            
            self.assertFalse(success)
        
        # Test within limits
        with patch.object(TierService, '_check_daily_limit') as mock_limit:
            mock_limit.return_value = True  # Within limits
            
            success = TierService.enforce_tier_limit(
                self.silver_customer,
                feature='basic_search',
                increment=1
            )
            
            self.assertTrue(success)


class BusinessLogicServiceTest(TestCase):
    """Test cases for BusinessLogicService."""
    
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
        
        # Create test vendor ID
        self.vendor_id = uuid.uuid4()
        
        # Create test promotion
        self.promotion = Promotion.objects.create(
            vendor_id=self.vendor_id,
            title='Test Promotion',
            description='Test description',
            discount_type='PERCENTAGE',
            discount_percent=20,
            is_flash_deal=False,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True
        )
    
    def test_calculate_vendor_ranking_score(self):
        """Test vendor ranking score calculation."""
        vendor_data = {
            'vendor_id': self.vendor_id,
            'popularity_score': 85.5,
            'interaction_count': 150,
            'tier': 'GOLD',
            'has_active_promotion': True,
            'average_rating': 4.2,
            'review_count': 50,
            'recent_activity_score': 0.8
        }
        
        ranking_score = BusinessLogicService.calculate_vendor_ranking_score(vendor_data)
        
        self.assertIsInstance(ranking_score, float)
        self.assertGreaterEqual(ranking_score, 0)
        self.assertLessEqual(ranking_score, 1.0)
    
    def test_determine_user_personalization(self):
        """Test user personalization determination."""
        user_behavior = {
            'search_history': ['restaurant', 'cafe', 'bakery'],
            'preferred_categories': ['FOOD'],
            'price_range_preference': 'MID',
            'location_preference': 'near_me',
            'time_of_day_preference': 'lunch'
        }
        
        personalization = BusinessLogicService.determine_user_personalization(
            self.customer_user,
            user_behavior
        )
        
        self.assertIsInstance(personalization, dict)
        self.assertIn('recommended_categories', personalization)
        self.assertIn('price_range_boost', personalization)
        self.assertIn('location_boost', personalization)
        self.assertIn('time_boost', personalization)
    
    def test_apply_business_rules(self):
        """Test business rules application."""
        search_request = {
            'query': 'restaurant',
            'lat': 24.8607,
            'lng': 67.0011,
            'radius_m': 1000,
            'user_tier': 'GOLD',
            'limit': 50
        }
        
        processed_request = BusinessLogicService.apply_business_rules(search_request)
        
        self.assertIsInstance(processed_request, dict)
        self.assertIn('adjusted_radius', processed_request)
        self.assertIn('adjusted_limit', processed_request)
        self.assertIn('boosted_categories', processed_request)
        self.assertIn('filtered_results', processed_request)
    
    def test_calculate_promotion_effectiveness(self):
        """Test promotion effectiveness calculation."""
        promotion_metrics = {
            'usage_count': 100,
            'unique_users': 80,
            'vendor_views': 500,
            'conversion_rate': 0.16,  # 80/500
            'revenue_impact': 2500.00,
            'cost': 500.00
        }
        
        effectiveness = BusinessLogicService.calculate_promotion_effectiveness(
            self.promotion.id,
            promotion_metrics
        )
        
        self.assertIsInstance(effectiveness, dict)
        self.assertIn('roi', effectiveness)
        self.assertIn('effectiveness_score', effectiveness)
        self.assertIn('engagement_rate', effectiveness)
        self.assertIn('conversion_quality', effectiveness)
    
    def test_recommend_content_to_user(self):
        """Test content recommendation to user."""
        recommendations = BusinessLogicService.recommend_content_to_user(
            self.customer_user,
            content_type='vendors',
            limit=10
        )
        
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 10)
        
        if recommendations:
            recommendation = recommendations[0]
            self.assertIn('content_id', recommendation)
            self.assertIn('relevance_score', recommendation)
            self.assertIn('recommendation_reason', recommendation)
    
    def test_detect_fraud_patterns(self):
        """Test fraud pattern detection."""
        user_activity = {
            'login_attempts': 5,
            'failed_logins': 3,
            'api_calls_per_minute': 150,
            'unusual_locations': ['New York', 'London', 'Tokyo'],
            'rapid_searches': 50,
            'suspicious_behavior': True
        }
        
        fraud_analysis = BusinessLogicService.detect_fraud_patterns(
            self.customer_user,
            user_activity
        )
        
        self.assertIsInstance(fraud_analysis, dict)
        self.assertIn('risk_score', fraud_analysis)
        self.assertIn('risk_level', fraud_analysis)
        self.assertIn('flagged_behaviors', fraud_analysis)
        self.assertIn('recommended_action', fraud_analysis)
    
    def test_optimize_search_results(self):
        """Test search result optimization."""
        raw_results = [
            {
                'vendor_id': uuid.uuid4(),
                'name': 'Restaurant A',
                'base_score': 0.8,
                'category': 'RESTAURANT'
            },
            {
                'vendor_id': uuid.uuid4(),
                'name': 'Restaurant B',
                'base_score': 0.7,
                'category': 'RESTAURANT'
            }
        ]
        
        user_context = {
            'user_tier': 'GOLD',
            'preferred_categories': ['RESTAURANT'],
            'past_interactions': [raw_results[0]['vendor_id']],
            'search_query': 'restaurant'
        }
        
        optimized_results = BusinessLogicService.optimize_search_results(
            raw_results,
            user_context
        )
        
        self.assertIsInstance(optimized_results, list)
        self.assertEqual(len(optimized_results), len(raw_results))
        
        # Results should have optimized scores
        for result in optimized_results:
            self.assertIn('optimized_score', result)
            self.assertIn('boost_factors', result)
    
    def test_calculate_user_engagement_score(self):
        """Test user engagement score calculation."""
        user_metrics = {
            'daily_active_days': 25,
            'searches_per_day': 5.2,
            'vendor_interactions': 150,
            'promotion_redemptions': 12,
            'session_duration_avg': 300,  # 5 minutes
            'feature_usage': {
                'search': 100,
                'ar_view': 45,
                'voice_search': 30,
                'favorites': 20
            }
        }
        
        engagement_score = BusinessLogicService.calculate_user_engagement_score(
            self.customer_user,
            user_metrics
        )
        
        self.assertIsInstance(engagement_score, dict)
        self.assertIn('overall_score', engagement_score)
        self.assertIn('engagement_level', engagement_score)
        self.assertIn('category_breakdown', engagement_score)
        self.assertIn('trend_analysis', engagement_score)


class PricingServiceTest(TestCase):
    """Test cases for PricingService."""
    
    def setUp(self):
        """Set up test data."""
        # Create pricing tiers
        self.pricing_tiers = {
            'SILVER': {
                'monthly_price': Decimal('9.99'),
                'annual_price': Decimal('99.99'),
                'features': ['basic_search', 'limited_promotions']
            },
            'GOLD': {
                'monthly_price': Decimal('19.99'),
                'annual_price': Decimal('199.99'),
                'features': ['advanced_search', 'unlimited_promotions', 'voice_search']
            },
            'DIAMOND': {
                'monthly_price': Decimal('49.99'),
                'annual_price': Decimal('499.99'),
                'features': ['all_features', 'analytics', 'priority_support']
            },
            'PLATINUM': {
                'monthly_price': Decimal('99.99'),
                'annual_price': Decimal('999.99'),
                'features': ['all_features', 'api_access', 'custom_integrations']
            }
        }
    
    def test_calculate_subscription_price(self):
        """Test subscription price calculation."""
        # Test monthly pricing
        monthly_price = PricingService.calculate_subscription_price(
            tier='GOLD',
            billing_cycle='monthly'
        )
        
        self.assertEqual(monthly_price, Decimal('19.99'))
        
        # Test annual pricing
        annual_price = PricingService.calculate_subscription_price(
            tier='GOLD',
            billing_cycle='annual'
        )
        
        self.assertEqual(annual_price, Decimal('199.99'))
        
        # Test annual discount (should be cheaper than 12x monthly)
        monthly_total = Decimal('19.99') * 12
        self.assertLess(annual_price, monthly_total)
    
    def test_calculate_proration_amount(self):
        """Test proration amount calculation."""
        # Test mid-month upgrade
        proration = PricingService.calculate_proration_amount(
            current_tier='SILVER',
            new_tier='GOLD',
            billing_cycle_start=timezone.now() - timedelta(days=15),
            billing_cycle_end=timezone.now() + timedelta(days=15),
            billing_cycle='monthly'
        )
        
        self.assertIsInstance(proration, Decimal)
        self.assertGreater(proration, 0)
        
        # Should be approximately half the monthly price difference
        expected_approx = (Decimal('19.99') - Decimal('9.99')) / 2
        self.assertAlmostEqual(float(proration), float(expected_approx), delta=1.0)
    
    def test_apply_discount_code(self):
        """Test discount code application."""
        # Create discount code
        discount_code = {
            'code': 'SAVE20',
            'discount_type': 'PERCENTAGE',
            'discount_value': 20,
            'applicable_tiers': ['GOLD', 'DIAMOND', 'PLATINUM'],
            'max_uses': 100,
            'expires_at': timezone.now() + timedelta(days=30)
        }
        
        # Apply to Gold subscription
        original_price = Decimal('19.99')
        discounted_price = PricingService.apply_discount_code(
            original_price=original_price,
            discount_code=discount_code,
            tier='GOLD'
        )
        
        expected_price = Decimal('19.99') * Decimal('0.8')  # 20% off
        self.assertEqual(discounted_price, expected_price)
        
        # Test invalid tier
        with self.assertRaises(ValueError):
            PricingService.apply_discount_code(
                original_price=original_price,
                discount_code=discount_code,
                tier='SILVER'  # Not in applicable_tiers
            )
    
    def test_calculate_refund_amount(self):
        """Test refund amount calculation."""
        # Test refund within grace period
        refund = PricingService.calculate_refund_amount(
            tier='GOLD',
            paid_amount=Decimal('19.99'),
            subscription_start=timezone.now() - timedelta(days=7),
            refund_requested_at=timezone.now(),
            billing_cycle='monthly'
        )
        
        self.assertIsInstance(refund, dict)
        self.assertIn('refund_amount', refund)
        self.assertIn('refund_percentage', refund)
        self.assertIn('refund_reason', refund)
        
        # Should get partial refund
        self.assertGreater(refund['refund_amount'], 0)
        self.assertLess(refund['refund_amount'], Decimal('19.99'))
    
    def test_get_upgrade_cost(self):
        """Test upgrade cost calculation."""
        upgrade_cost = PricingService.calculate_upgrade_cost(
            current_tier='SILVER',
            target_tier='GOLD',
            billing_cycle='monthly',
            days_remaining_in_cycle=15
        )
        
        self.assertIsInstance(upgrade_cost, dict)
        self.assertIn('prorated_cost', upgrade_cost)
        self.assertIn('full_cycle_cost', upgrade_cost)
        self.assertIn('recommendation', upgrade_cost)
        
        # Prorated cost should be less than full cycle cost
        self.assertLess(
            upgrade_cost['prorated_cost'],
            upgrade_cost['full_cycle_cost']
        )
    
    def test_validate_pricing_rules(self):
        """Test pricing rule validation."""
        # Test valid pricing
        valid_pricing = {
            'tier': 'GOLD',
            'monthly_price': Decimal('19.99'),
            'annual_price': Decimal('199.99')
        }
        
        is_valid = PricingService.validate_pricing_rules(valid_pricing)
        self.assertTrue(is_valid)
        
        # Test invalid pricing (annual more expensive than 12x monthly)
        invalid_pricing = {
            'tier': 'GOLD',
            'monthly_price': Decimal('19.99'),
            'annual_price': Decimal('300.00')  # Too expensive
        }
        
        is_invalid = PricingService.validate_pricing_rules(invalid_pricing)
        self.assertFalse(is_invalid)
    
    def test_get_revenue_projections(self):
        """Test revenue projections."""
        projections = PricingService.get_revenue_projections(
            months=12,
            user_growth_rate=0.05,  # 5% monthly growth
            churn_rate=0.02,  # 2% monthly churn
            tier_distribution={
                'SILVER': 0.4,
                'GOLD': 0.35,
                'DIAMOND': 0.20,
                'PLATINUM': 0.05
            }
        )
        
        self.assertIsInstance(projections, dict)
        self.assertIn('monthly_projections', projections)
        self.assertIn('total_annual_revenue', projections)
        self.assertIn('average_revenue_per_user', projections)
        
        monthly_projections = projections['monthly_projections']
        self.assertEqual(len(monthly_projections), 12)
        
        # Each month should have revenue data
        for month_data in monthly_projections:
            self.assertIn('month', month_data)
            self.assertIn('projected_revenue', month_data)
            self.assertIn('projected_users', month_data)
