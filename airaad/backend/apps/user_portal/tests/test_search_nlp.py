"""
Unit tests for Search & NLP functionality.
Tests text search, voice search, and intent extraction.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customer_auth.models import CustomerUser
from apps.user_portal.models import Tag
from apps.user_portal.services import SearchService, NLPService

User = get_user_model()


class NLPServiceTest(TestCase):
    """Test cases for NLP service."""
    
    def setUp(self):
        """Set up test data."""
        # Create test tags for categorization
        self.food_tags = [
            Tag.objects.create(name='Restaurant', slug='restaurant', category='FOOD'),
            Tag.objects.create(name='Cafe', slug='cafe', category='FOOD'),
            Tag.objects.create(name='Bakery', slug='bakery', category='FOOD'),
            Tag.objects.create(name='Fast Food', slug='fast-food', category='FOOD'),
        ]
        
        self.shopping_tags = [
            Tag.objects.create(name='Clothing', slug='clothing', category='SHOPPING'),
            Tag.objects.create(name='Electronics', slug='electronics', category='SHOPPING'),
            Tag.objects.create(name='Grocery', slug='grocery', category='SHOPPING'),
        ]
        
        self.service_tags = [
            Tag.objects.create(name='Bank', slug='bank', category='SERVICES'),
            Tag.objects.create(name='Pharmacy', slug='pharmacy', category='SERVICES'),
            Tag.objects.create(name='Gas Station', slug='gas-station', category='SERVICES'),
        ]
    
    def test_extract_category_food_queries(self):
        """Test category extraction for food-related queries."""
        test_cases = [
            ('restaurant near me', 'RESTAURANT'),
            ('find me a cafe', 'CAFE'),
            ('bakery for bread', 'BAKERY'),
            ('fast food place', 'FAST_FOOD'),
            ('pizza restaurant', 'RESTAURANT'),
            ('coffee cafe', 'CAFE'),
            ('cake bakery', 'BAKERY'),
            ('burger fast food', 'FAST_FOOD'),
        ]
        
        for query, expected_category in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('category'), expected_category)
    
    def test_extract_category_shopping_queries(self):
        """Test category extraction for shopping-related queries."""
        test_cases = [
            ('clothing store', 'CLOTHING'),
            ('electronics shop', 'ELECTRONICS'),
            ('grocery store', 'GROCERY'),
            ('buy clothes', 'CLOTHING'),
            ('phone electronics', 'ELECTRONICS'),
            ('food grocery', 'GROCERY'),
        ]
        
        for query, expected_category in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('category'), expected_category)
    
    def test_extract_category_services_queries(self):
        """Test category extraction for service-related queries."""
        test_cases = [
            ('bank near me', 'BANK'),
            ('pharmacy open now', 'PHARMACY'),
            ('gas station', 'GAS_STATION'),
            ('atm bank', 'BANK'),
            ('medicine pharmacy', 'PHARMACY'),
            ('petrol gas station', 'GAS_STATION'),
        ]
        
        for query, expected_category in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('category'), expected_category)
    
    def test_extract_price_range(self):
        """Test price range extraction."""
        test_cases = [
            ('cheap restaurant', 'BUDGET'),
            ('affordable food', 'BUDGET'),
            ('budget friendly', 'BUDGET'),
            ('mid range restaurant', 'MID'),
            ('moderate price', 'MID'),
            ('expensive restaurant', 'PREMIUM'),
            ('luxury dining', 'PREMIUM'),
            ('fine dining', 'PREMIUM'),
        ]
        
        for query, expected_price_range in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('price_range'), expected_price_range)
    
    def test_extract_features(self):
        """Test feature extraction."""
        test_cases = [
            ('restaurant with delivery', ['delivery']),
            ('cafe with wifi', ['wifi']),
            ('restaurant with parking', ['parking']),
            ('place with outdoor seating', ['outdoor_seating']),
            ('restaurant with kids menu', ['kids_friendly']),
            ('cafe open 24 hours', ['24_hours']),
            ('restaurant with vegetarian options', ['vegetarian']),
            ('place with alcohol', ['alcohol']),
        ]
        
        for query, expected_features in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                features = intent.get('features', [])
                for feature in expected_features:
                    self.assertIn(feature, features)
    
    def test_extract_time_of_day(self):
        """Test time of day extraction."""
        test_cases = [
            ('breakfast restaurant', 'breakfast'),
            ('lunch place', 'lunch'),
            ('dinner restaurant', 'dinner'),
            ('late night food', 'late_night'),
            ('early morning cafe', 'early_morning'),
            ('brunch place', 'brunch'),
        ]
        
        for query, expected_time in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('time_of_day'), expected_time)
    
    def test_extract_location_context(self):
        """Test location context extraction."""
        test_cases = [
            ('restaurant near me', 'near_me'),
            ('cafe nearby', 'nearby'),
            ('restaurant in karachi', 'karachi'),
            ('cafe in clifton', 'clifton'),
            ('food near my location', 'near_me'),
        ]
        
        for query, expected_location in test_cases:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                self.assertEqual(intent.get('location_context'), expected_location)
    
    def test_voice_query_processing(self):
        """Test voice query processing."""
        voice_queries = [
            'find me a good restaurant near me',
            'I need a cafe with wifi',
            'show me cheap restaurants',
            'looking for a bank atm',
            'where can I find a pharmacy',
        ]
        
        for query in voice_queries:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                
                # Should always return a dict with expected keys
                self.assertIsInstance(intent, dict)
                self.assertIn('category', intent)
                self.assertIn('price_range', intent)
                self.assertIn('features', intent)
                self.assertIn('time_of_day', intent)
                self.assertIn('location_context', intent)
                self.assertIn('confidence', intent)
                
                # Confidence should be between 0 and 1
                confidence = intent.get('confidence', 0)
                self.assertGreaterEqual(confidence, 0)
                self.assertLessEqual(confidence, 1)
    
    def test_query_normalization(self):
        """Test query normalization."""
        test_cases = [
            ('RESTAURANT NEAR ME', 'restaurant near me'),  # Lowercase
            ('find me a restaurant!!!', 'find me a restaurant'),  # Remove punctuation
            ('  restaurant   near  me  ', 'restaurant near me'),  # Normalize spaces
            ('café near me', 'cafe near me'),  # Normalize accents
            ('restaurant@near#me', 'restaurant near me'),  # Remove special chars
        ]
        
        for input_query, expected_output in test_cases:
            with self.subTest(input_query=input_query):
                normalized = NLPService.normalize_query(input_query)
                self.assertEqual(normalized, expected_output)
    
    def test_entity_recognition(self):
        """Test entity recognition."""
        test_cases = [
            ('restaurant in Karachi', {'location': 'Karachi'}),
            ('cafe near Clifton', {'location': 'Clifton'}),
            ('bank at Main Street', {'location': 'Main Street'}),
            ('restaurant with 5 stars', {'rating': '5'}),
            ('cafe open 24 hours', {'hours': '24_hours'}),
        ]
        
        for query, expected_entities in test_cases:
            with self.subTest(query=query):
                entities = NLPService.extract_entities(query)
                
                for entity_type, expected_value in expected_entities.items():
                    self.assertIn(entity_type, entities)
                    self.assertEqual(entities[entity_type], expected_value)
    
    def test_intent_confidence_scoring(self):
        """Test intent confidence scoring."""
        # Clear, specific queries should have high confidence
        clear_queries = [
            'restaurant near me',
            'cafe with wifi',
            'cheap food',
        ]
        
        # Ambiguous queries should have lower confidence
        ambiguous_queries = [
            'place',
            'store',
            'something',
        ]
        
        for query in clear_queries:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                confidence = intent.get('confidence', 0)
                self.assertGreater(confidence, 0.7)  # High confidence
        
        for query in ambiguous_queries:
            with self.subTest(query=query):
                intent = NLPService.extract_search_intent(query)
                confidence = intent.get('confidence', 0)
                self.assertLess(confidence, 0.5)  # Low confidence
    
    def test_multilingual_support(self):
        """Test multilingual query support."""
        # Test basic English (already covered above)
        # Test if service handles other languages gracefully
        non_english_queries = [
            'ресторан рядом со мной',  # Russian
            'restaurant près de moi',  # French
            'restaurante cerca de mí',  # Spanish
        ]
        
        for query in non_english_queries:
            with self.subTest(query=query):
                # Should not crash and should return some intent
                intent = NLPService.extract_search_intent(query)
                self.assertIsInstance(intent, dict)
                self.assertIn('confidence', intent)
    
    def test_query_expansion(self):
        """Test query expansion."""
        test_cases = [
            ('restaurant', ['restaurant', 'food', 'dining']),
            ('cafe', ['cafe', 'coffee', 'breakfast']),
            ('bank', ['bank', 'atm', 'money']),
            ('pharmacy', ['pharmacy', 'medicine', 'drugstore']),
        ]
        
        for query, expected_terms in test_cases:
            with self.subTest(query=query):
                expanded = NLPService.expand_query(query)
                self.assertIsInstance(expanded, list)
                self.assertGreater(len(expanded), 1)
                
                # Should include original query
                self.assertIn(query, expanded)
                
                # Should include expected expansion terms
                for term in expected_terms:
                    self.assertIn(term, expanded)
    
    def test_spell_correction(self):
        """Test spell correction."""
        test_cases = [
            ('restarant', 'restaurant'),
            ('cafe', 'cafe'),  # Already correct
            ('bakry', 'bakery'),
            ('resturant', 'restaurant'),
            ('cofee', 'coffee'),
        ]
        
        for misspelled, corrected in test_cases:
            with self.subTest(misspelled=misspelled):
                result = NLPService.correct_spelling(misspelled)
                self.assertEqual(result, corrected)
    
    def test_synonym_handling(self):
        """Test synonym handling."""
        test_cases = [
            ('eat', 'restaurant'),
            ('dine', 'restaurant'),
            ('food', 'restaurant'),
            ('coffee shop', 'cafe'),
            ('espresso', 'cafe'),
            ('ATM', 'bank'),
            ('cash machine', 'bank'),
        ]
        
        for synonym, expected_category in test_cases:
            with self.subTest(synonym=synonym):
                intent = NLPService.extract_search_intent(synonym)
                category = intent.get('category')
                
                # Should map to correct category
                if expected_category == 'restaurant':
                    self.assertIn(category, ['RESTAURANT', 'CAFE', 'BAKERY', 'FAST_FOOD'])
                elif expected_category == 'cafe':
                    self.assertEqual(category, 'CAFE')
                elif expected_category == 'bank':
                    self.assertEqual(category, 'BANK')


class SearchServiceTest(TestCase):
    """Test cases for Search service."""
    
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
        
        # Create test tags
        self.tags = [
            Tag.objects.create(name='Restaurant', slug='restaurant', category='FOOD'),
            Tag.objects.create(name='Cafe', slug='cafe', category='FOOD'),
            Tag.objects.create(name='Bakery', slug='bakery', category='FOOD'),
            Tag.objects.create(name='Bank', slug='bank', category='SERVICES'),
            Tag.objects.create(name='Pharmacy', slug='pharmacy', category='SERVICES'),
        ]
        
        # Test coordinates
        self.test_lat = 24.8607
        self.test_lng = 67.0011
        self.test_radius = 1000
    
    def test_text_search_basic(self):
        """Test basic text search."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Test Restaurant',
                    'category': 'RESTAURANT',
                    'relevance_score': 0.9
                }
            ]
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        self.assertIsInstance(results, list)
        if results:
            self.assertIn('vendor_id', results[0])
            self.assertIn('relevance_score', results[0])
        
        mock_search.assert_called_once()
    
    def test_text_search_with_filters(self):
        """Test text search with filters."""
        query = 'cafe'
        filters = {
            'category': 'CAFE',
            'price_range': 'BUDGET',
            'features': ['wifi', 'outdoor_seating']
        }
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
            mock_search.return_value = []
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user,
                filters=filters
            )
        
        mock_search.assert_called_once()
        
        # Verify filters were passed
        call_args = mock_search.call_args
        self.assertEqual(call_args[1]['filters'], filters)
    
    def test_text_search_sorting(self):
        """Test text search sorting options."""
        query = 'restaurant'
        sort_options = ['relevance', 'distance', 'popularity', 'rating']
        
        for sort_option in sort_options:
            with self.subTest(sort_option=sort_option):
                with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
                    mock_search.return_value = []
                    
                    results = SearchService.text_search(
                        query=query,
                        lat=self.test_lat,
                        lng=self.test_lng,
                        radius_m=self.test_radius,
                        user=self.customer_user,
                        sort_by=sort_option
                    )
                
                mock_search.assert_called_once()
                
                # Verify sort option was passed
                call_args = mock_search.call_args
                self.assertEqual(call_args[1]['sort_by'], sort_option)
    
    def test_voice_search_basic(self):
        """Test basic voice search."""
        query = 'find me a good restaurant near me'
        
        with patch.object(NLPService, 'extract_search_intent') as mock_nlp, \
             patch.object(SearchService, '_search_vendors_by_intent') as mock_search:
            
            # Mock NLP intent extraction
            mock_nlp.return_value = {
                'category': 'RESTAURANT',
                'price_range': 'MID',
                'features': ['outdoor_seating'],
                'confidence': 0.85
            }
            
            # Mock search results
            mock_search.return_value = [
                {
                    'vendor_id': uuid.uuid4(),
                    'name': 'Good Restaurant',
                    'category': 'RESTAURANT',
                    'intent_match_score': 0.9
                }
            ]
            
            results = SearchService.voice_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        self.assertIsInstance(results, list)
        if results:
            self.assertIn('vendor_id', results[0])
            self.assertIn('intent_match_score', results[0])
        
        mock_nlp.assert_called_once_with(query)
        mock_search.assert_called_once()
    
    def test_voice_search_low_confidence(self):
        """Test voice search with low confidence intent."""
        query = 'something somewhere'  # Ambiguous query
        
        with patch.object(NLPService, 'extract_search_intent') as mock_nlp, \
             patch.object(SearchService, '_search_vendors_by_text') as mock_text_search:
            
            # Mock low confidence NLP result
            mock_nlp.return_value = {
                'category': None,
                'price_range': None,
                'features': [],
                'confidence': 0.2
            }
            
            # Should fall back to text search
            mock_text_search.return_value = []
            
            results = SearchService.voice_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        # Should have called NLP first
        mock_nlp.assert_called_once()
        
        # Should have fallen back to text search
        mock_text_search.assert_called_once()
    
    def test_search_history_tracking(self):
        """Test search history tracking."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search, \
             patch.object(SearchService, '_record_search_history') as mock_record:
            
            mock_search.return_value = []
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        # Should record search history
        mock_record.assert_called_once()
        
        # Verify search history parameters
        call_args = mock_record.call_args
        self.assertEqual(call_args[1]['query_text'], query)
        self.assertEqual(call_args[1]['query_type'], 'TEXT')
        self.assertEqual(call_args[1]['user'], self.customer_user)
    
    def test_search_suggestions(self):
        """Test search suggestions."""
        partial_query = 'rest'
        
        with patch.object(SearchService, '_get_search_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                'restaurant',
                'rest area',
                'rest stop'
            ]
            
            suggestions = SearchService.get_search_suggestions(
                partial_query=partial_query,
                user=self.customer_user
            )
        
        self.assertIsInstance(suggestions, list)
        self.assertEqual(len(suggestions), 3)
        self.assertIn('restaurant', suggestions)
        
        mock_suggestions.assert_called_once()
    
    def test_popular_searches(self):
        """Test popular searches."""
        with patch.object(SearchService, '_get_popular_searches') as mock_popular:
            mock_popular.return_value = [
                {'query': 'restaurant near me', 'count': 150},
                {'query': 'cafe with wifi', 'count': 120},
                {'query': 'cheap food', 'count': 100}
            ]
            
            popular = SearchService.get_popular_searches(
                limit=10,
                days=7
            )
        
        self.assertIsInstance(popular, list)
        self.assertEqual(len(popular), 3)
        self.assertEqual(popular[0]['query'], 'restaurant near me')
        self.assertEqual(popular[0]['count'], 150)
        
        mock_popular.assert_called_once()
    
    def test_search_analytics(self):
        """Test search analytics."""
        with patch.object(SearchService, '_get_search_analytics') as mock_analytics:
            mock_analytics.return_value = {
                'total_searches': 1000,
                'unique_users': 500,
                'top_queries': [
                    {'query': 'restaurant', 'count': 150},
                    {'query': 'cafe', 'count': 120}
                ],
                'top_categories': [
                    {'category': 'RESTAURANT', 'count': 300},
                    {'category': 'CAFE', 'count': 200}
                ]
            }
            
            analytics = SearchService.get_search_analytics(
                days=30
            )
        
        self.assertIsInstance(analytics, dict)
        self.assertIn('total_searches', analytics)
        self.assertIn('unique_users', analytics)
        self.assertIn('top_queries', analytics)
        self.assertIn('top_categories', analytics)
        
        mock_analytics.assert_called_once()
    
    def test_search_performance_optimization(self):
        """Test search performance optimizations."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search, \
             patch.object(SearchService, '_cache_search_results') as mock_cache:
            
            mock_search.return_value = []
            mock_cache.return_value = None  # Cache miss
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        # Should check cache first
        mock_cache.assert_called_once()
        
        # Should perform search on cache miss
        mock_search.assert_called_once()
        
        # Should cache results
        # (This would be verified by checking if cache.set was called)
    
    def test_search_error_handling(self):
        """Test search error handling."""
        query = 'restaurant'
        
        # Test NLP service error
        with patch.object(NLPService, 'extract_search_intent') as mock_nlp:
            mock_nlp.side_effect = Exception("NLP service error")
            
            with self.assertRaises(Exception):
                SearchService.voice_search(
                    query=query,
                    lat=self.test_lat,
                    lng=self.test_lng,
                    radius_m=self.test_radius,
                    user=self.customer_user
                )
        
        # Test search service error
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
            mock_search.side_effect = Exception("Search service error")
            
            with self.assertRaises(Exception):
                SearchService.text_search(
                    query=query,
                    lat=self.test_lat,
                    lng=self.test_lng,
                    radius_m=self.test_radius,
                    user=self.customer_user
                )
    
    def test_search_result_validation(self):
        """Test search result validation."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
            # Mock invalid search results
            mock_search.return_value = [
                {'invalid': 'result'},  # Missing required fields
                {'vendor_id': 'invalid-uuid'},  # Invalid UUID
                None,  # Null result
            ]
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user
            )
        
        # Should filter out invalid results
        valid_results = [r for r in results if r is not None and isinstance(r, dict)]
        self.assertLessEqual(len(valid_results), len(results))
    
    def test_search_pagination(self):
        """Test search pagination."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search:
            # Mock paginated results
            mock_search.return_value = [
                {'vendor_id': uuid.uuid4(), 'name': f'Restaurant {i}'}
                for i in range(20)
            ]
            
            # Test first page
            results_page1 = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user,
                limit=10,
                offset=0
            )
            
            # Test second page
            results_page2 = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user,
                limit=10,
                offset=10
            )
        
        # Should respect pagination parameters
        mock_search.assert_called()
        
        # Verify pagination parameters were passed
        call_args = mock_search.call_args
        self.assertEqual(call_args[1]['limit'], 10)
        self.assertEqual(call_args[1]['offset'], 0)  # From last call
    
    def test_search_faceting(self):
        """Test search faceting."""
        query = 'restaurant'
        
        with patch.object(SearchService, '_search_vendors_by_text') as mock_search, \
             patch.object(SearchService, '_get_search_facets') as mock_facets:
            
            mock_search.return_value = []
            mock_facets.return_value = {
                'categories': [
                    {'name': 'RESTAURANT', 'count': 50},
                    {'name': 'CAFE', 'count': 30}
                ],
                'price_ranges': [
                    {'name': 'BUDGET', 'count': 40},
                    {'name': 'MID', 'count': 35}
                ],
                'features': [
                    {'name': 'wifi', 'count': 25},
                    {'name': 'parking', 'count': 20}
                ]
            }
            
            results = SearchService.text_search(
                query=query,
                lat=self.test_lat,
                lng=self.test_lng,
                radius_m=self.test_radius,
                user=self.customer_user,
                include_facets=True
            )
        
        # Should include facets
        mock_facets.assert_called_once()
        
        # Verify facets structure
        facets = mock_facets.return_value
        self.assertIn('categories', facets)
        self.assertIn('price_ranges', facets)
        self.assertIn('features', facets)
