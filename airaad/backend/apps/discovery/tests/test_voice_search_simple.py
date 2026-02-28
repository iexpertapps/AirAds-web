"""
Simplified unit tests for Voice Search functionality.
Tests core query processing without Tag model dependencies.
"""

import uuid
from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.customer_auth.models import CustomerUser

User = get_user_model()


class VoiceSearchSimpleTest(TestCase):
    """Simple test cases for voice search core functionality."""
    
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
    
    def test_empty_transcript_calls_nearby_vendors(self):
        """Test that empty transcript calls nearby_vendors instead of search."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.nearby_vendors') as mock_nearby:
            mock_nearby.return_value = []
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript=''
            )
            
            # Should call nearby_vendors for empty transcript
            self.assertTrue(mock_nearby.called)
            call_kwargs = mock_nearby.call_args[1] if mock_nearby.call_args[1] else mock_nearby.call_args[0]
            self.assertEqual(len(result), 0)
    
    def test_whitespace_transcript_calls_nearby_vendors(self):
        """Test that whitespace-only transcript calls nearby_vendors."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.nearby_vendors') as mock_nearby:
            mock_nearby.return_value = []
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='   \t\n  '
            )
            
            # Should call nearby_vendors for whitespace
            self.assertTrue(mock_nearby.called)
            self.assertEqual(len(result), 0)
    
    def test_query_without_keywords_calls_search(self):
        """Test query without intent keywords calls search_vendors."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            # Use a query with no intent keywords
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='xyz restaurant abc'  # No intent keywords
            )
            
            # Should call search_vendors
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], 'xyz restaurant abc')
            self.assertIsNone(call_kwargs.get('tag_ids'))  # No tags for non-keyword query
    
    def test_default_radius(self):
        """Test that default radius is used."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['radius'], 2000)  # Default radius
    
    def test_custom_radius(self):
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
            
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['lat'], self.test_lat)
            self.assertEqual(call_kwargs['lng'], self.test_lng)
    
    def test_transcript_trimming(self):
        """Test that transcript is trimmed."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='  restaurant xyz  '
            )
            
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], 'restaurant xyz')  # Trimmed
    
    def test_returns_list(self):
        """Test that voice_search returns a list."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = [
                {'id': str(uuid.uuid4()), 'name': 'Test Restaurant'}
            ]
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
    
    def test_returns_empty_list_no_results(self):
        """Test that voice_search returns empty list when no results."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            result = voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant'
            )
            
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)
    
    def test_special_characters(self):
        """Test voice search with special characters."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant @#$%'
            )
            
            # Should still call search_vendors
            self.assertTrue(mock_search.called)
    
    def test_unicode_characters(self):
        """Test voice search with Unicode characters."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='رستوران restaurant café'
            )
            
            # Should still call search_vendors
            self.assertTrue(mock_search.called)
    
    def test_very_long_transcript(self):
        """Test voice search with very long transcript."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            long_query = ' '.join(['word'] * 100)
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript=long_query
            )
            
            # Should still call search_vendors
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
            
            # Should still call search_vendors
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], 'restaurant within 5 kilometers')
    
    def test_case_preserved_in_query(self):
        """Test that case is preserved in the query passed to search."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='Restaurant XYZ'
            )
            
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['query'], 'Restaurant XYZ')
    
    def test_multiple_calls(self):
        """Test that voice_search can be called multiple times."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            # First call
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='first query'
            )
            
            # Second call
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='second query'
            )
            
            # Should have been called twice
            self.assertEqual(mock_search.call_count, 2)
    
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
            
            # Should still call search_vendors
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['lat'], 0.0)
            self.assertEqual(call_kwargs['lng'], 0.0)
    
    def test_negative_radius(self):
        """Test voice search with negative radius."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant',
                radius=-1000
            )
            
            # Should still call search_vendors (validation happens there)
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['radius'], -1000)
    
    def test_very_large_radius(self):
        """Test voice search with very large radius."""
        from apps.discovery.services import voice_search
        
        with patch('apps.discovery.services.search_vendors') as mock_search:
            mock_search.return_value = []
            
            voice_search(
                lat=self.test_lat,
                lng=self.test_lng,
                transcript='restaurant',
                radius=1000000
            )
            
            # Should still call search_vendors
            self.assertTrue(mock_search.called)
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs['radius'], 1000000)
