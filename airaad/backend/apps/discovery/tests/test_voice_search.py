"""
Unit tests for Voice Search functionality.
Tests rule-based NLP processing, intent extraction, and keyword mapping.
"""

import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customer_auth.models import CustomerUser
from apps.user_preferences.models import UserPreference

User = get_user_model()


class VoiceSearchIntentExtractionTest(TestCase):
    """Test cases for voice search intent extraction."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
        )
        
        # Test location (Lahore)
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_intent_extraction_cheap_keywords(self):
        """Test extraction of cheap/budget intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            # Test "cheap"
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='cheap restaurant near me'
            )
            
            # Verify search_vendors was called
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], 'cheap restaurant near me')
            # Should have tag_ids for cheap intent
            self.assertIsNotNone(call_kwargs.get('tag_ids'))
    
    def test_intent_extraction_budget_keywords(self):
        """Test extraction of budget intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='budget friendly cafe'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertIsNotNone(call_kwargs.get('tag_ids'))
    
    def test_intent_extraction_premium_keywords(self):
        """Test extraction of premium intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='premium restaurant'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertIsNotNone(call_kwargs.get('tag_ids'))
    
    def test_intent_extraction_luxury_keywords(self):
        """Test extraction of luxury intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='luxury dining experience'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_quick_keywords(self):
        """Test extraction of quick/fast service intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            # Test "quick"
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='quick lunch spot'
            )
            
            self.assertTrue(mock_search.called)
            
            mock_search.reset_mock()
            
            # Test "fast"
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='fast service restaurant'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_healthy_keywords(self):
        """Test extraction of healthy intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='healthy food options'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_halal_keywords(self):
        """Test extraction of halal intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='halal restaurant'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_family_keywords(self):
        """Test extraction of family-friendly intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='family friendly restaurant'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_romantic_keywords(self):
        """Test extraction of romantic intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='romantic dinner spot'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_late_night_keywords(self):
        """Test extraction of late night intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='late night food'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_breakfast_keywords(self):
        """Test extraction of breakfast intent."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='breakfast place'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_intent_extraction_multiple_keywords(self):
        """Test extraction of multiple intents from one query."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query to return multiple tags
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4(), uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='cheap fast food near me'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            # Should extract both "cheap" and "fast" intents
            self.assertIsNotNone(call_kwargs.get('tag_ids'))
    
    def test_intent_extraction_case_insensitive(self):
        """Test that intent extraction is case insensitive."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag') as mock_tag:
            mock_search.return_value = []
            
            # Mock Tag query
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4()]
            mock_tag.objects.filter.return_value = mock_queryset
            
            # Test with uppercase
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='CHEAP RESTAURANT'
            )
            
            self.assertTrue(mock_search.called)
            
            mock_search.reset_mock()
            
            # Test with mixed case
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='ChEaP ReStAuRaNt'
            )
            
            self.assertTrue(mock_search.called)


class VoiceSearchQueryProcessingTest(TestCase):
    """Test cases for voice search query processing."""
    
    def setUp(self):
        """Set up test data."""
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_empty_transcript_handling(self):
        """Test handling of empty transcript."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.nearby_vendors') as mock_nearby:
            mock_nearby.return_value = []
            
            # Test with empty string
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript=''
            )
            
            # Should call nearby_vendors instead of search_vendors
            self.assertTrue(mock_nearby.called)
    
    def test_whitespace_only_transcript(self):
        """Test handling of whitespace-only transcript."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.nearby_vendors') as mock_nearby:
            mock_nearby.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='   '
            )
            
            # Should call nearby_vendors for whitespace
            self.assertTrue(mock_nearby.called)
    
    def test_transcript_trimming(self):
        """Test that transcript is trimmed of leading/trailing whitespace."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='  restaurant near me  '
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            # Query should be trimmed
            self.assertEqual(call_kwargs['query'], 'restaurant near me')
    
    def test_default_radius_usage(self):
        """Test that default radius is used when not specified."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            # Should use default radius (2000m)
            self.assertEqual(call_kwargs['radius'], 2000)
    
    def test_custom_radius_usage(self):
        """Test that custom radius is passed correctly."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant',
                radius=5000
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['radius'], 5000)
    
    def test_location_passed_correctly(self):
        """Test that location coordinates are passed correctly."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['lat'], self.test_lat)
            self.assertEqual(call_kwargs['lng'], self.test_lng)
    
    def test_query_preservation(self):
        """Test that original query is preserved in search call."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            original_query = 'best pakistani restaurant with outdoor seating'
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript=original_query
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], original_query)


class VoiceSearchIntegrationTest(TestCase):
    """Test cases for voice search integration with other services."""
    
    def setUp(self):
        """Set up test data."""
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_voice_search_returns_list(self):
        """Test that voice search returns a list."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = [
                {'id': str(uuid.uuid4()), 'name': 'Test Restaurant', 'score': 85.0}
            ]
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            self.assertIsInstance(result, list)
    
    def test_voice_search_with_results(self):
        """Test voice search with mock results."""
        from apps.discovery.services import voice_search
        
        mock_results = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Test Restaurant',
                'score': 85.0,
                'distance': 500
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Another Cafe',
                'score': 75.0,
                'distance': 800
            }
        ]
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = mock_results
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant near me'
            )
            
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['name'], 'Test Restaurant')
            self.assertEqual(result[1]['name'], 'Another Cafe')
    
    def test_voice_search_with_no_results(self):
        """Test voice search with no results."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='nonexistent cuisine'
            )
            
            self.assertEqual(len(result), 0)
    
    def test_voice_search_tag_filtering(self):
        """Test that voice search applies tag filtering."""
        from apps.discovery.services import voice_search
        
        # Mock Tag model query
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag.objects.filter') as mock_tag_filter:
            
            mock_search.return_value = []
            
            # Mock tag query to return some tag IDs
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = [uuid.uuid4(), uuid.uuid4()]
            mock_tag_filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='cheap restaurant'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            # Should have tag_ids from the query
            self.assertIsNotNone(call_kwargs.get('tag_ids'))
    
    def test_voice_search_without_matching_tags(self):
        """Test voice search when no tags match."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search, \
             patch('apps.tags.models.Tag.objects.filter') as mock_tag_filter:
            
            mock_search.return_value = []
            
            # Mock tag query to return no tags
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = []
            mock_tag_filter.return_value = mock_queryset
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='cheap restaurant'
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            # Should have None for tag_ids when no tags found
            self.assertIsNone(call_kwargs.get('tag_ids'))


class VoiceSearchEdgeCasesTest(TestCase):
    """Test edge cases for voice search."""
    
    def setUp(self):
        """Set up test data."""
        self.test_lat = 31.5204
        self.test_lng = 74.3587
    
    def test_very_long_transcript(self):
        """Test voice search with very long transcript."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            long_transcript = ' '.join(['restaurant'] * 100)  # Very long query
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript=long_transcript
            )
            
            self.assertTrue(mock_search.called)
    
    def test_special_characters_in_transcript(self):
        """Test voice search with special characters."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant @#$%^&*'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_unicode_characters_in_transcript(self):
        """Test voice search with Unicode characters."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='رستوران restaurant café'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_numbers_in_transcript(self):
        """Test voice search with numbers."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant within 5 kilometers'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_invalid_coordinates(self):
        """Test voice search with invalid coordinates."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            # Test with out of range coordinates
            voice_search(
                lat=91.0,  # Invalid latitude
                lng=181.0,  # Invalid longitude
                transcript='restaurant'
            )
            
            # Should still call search_vendors (validation happens there)
            self.assertTrue(mock_search.called)
    
    def test_zero_coordinates(self):
        """Test voice search with zero coordinates."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=0.0,
                lng=0.0,
                transcript='restaurant'
            )
            
            self.assertTrue(mock_search.called)
    
    def test_negative_radius(self):
        """Test voice search with negative radius."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant',
                radius=-1000  # Negative radius
            )
            
            # Should still call search_vendors (validation happens there)
            self.assertTrue(mock_search.called)
    
    def test_very_large_radius(self):
        """Test voice search with very large radius."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant',
                radius=1000000  # 1000km
            )
            
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['radius'], 1000000)
