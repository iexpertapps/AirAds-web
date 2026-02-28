from django.db import connection, models
from django.core.cache import cache
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta
import math
import uuid

from .models import Vendor, Promotion, VendorReel, Tag, City, Area


class DiscoveryService:
    """
    Service layer for vendor discovery with ranking algorithm.
    Implements the exact ranking formula from the plan.
    """
    
    # Exact ranking formula weights from plan
    RANKING_WEIGHTS = {
        'relevance': 0.30,
        'distance': 0.25,
        'offer': 0.15,
        'popularity': 0.15,
        'tier': 0.15,
    }
    
    # Tier scores (normalized 0-1) from plan
    TIER_SCORES = {
        'SILVER': 0.25,
        'GOLD': 0.50,
        'DIAMOND': 0.75,
        'PLATINUM': 1.00,
    }
    
    # System tag boosts (applied AFTER weighted formula)
    SYSTEM_TAG_BOOSTS = {
        'new_vendor_boost': 0.10,
        'trending': 0.05,
        'verified': 0.03,
    }
    
    # Cache timeouts
    CACHE_TIMEOUTS = {
        'nearby_vendors': 300,      # 5 minutes
        'ar_markers': 30,           # 30 seconds (real-time)
        'vendor_detail': 600,       # 10 minutes
        'promotions': 180,          # 3 minutes
        'tags': 3600,               # 1 hour
        'cities': 86400,            # 24 hours
    }
    
    @classmethod
    def get_nearby_vendors(cls, lat, lng, radius_m, user_tier='SILVER', 
                          category=None, limit=50, user_preferences=None):
        """
        Get nearby vendors with ranking algorithm.
        Implements exact formula: Relevance×0.30 + Distance×0.25 + Offer×0.15 + Popularity×0.15 + Tier×0.15
        """
        # Generate cache key
        cache_key = f"nearby_vendors_{lat:.4f}_{lng:.4f}_{radius_m}_{user_tier}_{category or 'all'}_{limit}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Create user point
        user_point = Point(lng, lat, srid=4326)
        
        # Base queryset with spatial query
        vendors = Vendor.objects.filter(
            is_active=True,
            location__distance_lte=(user_point, radius_m)
        ).annotate(
            distance_m=Distance('location', user_point) * 111320  # Convert to meters
        )
        
        # Filter by category if specified
        if category:
            vendors = vendors.filter(category=category)
        
        # Apply tier-based limits
        tier_limits = {
            'SILVER': 50,
            'GOLD': 100,
            'DIAMOND': 200,
            'PLATINUM': 500,
        }
        max_results = min(limit, tier_limits.get(user_tier, 50))
        
        # Get all vendors and calculate scores
        vendors_data = []
        for vendor in vendors[:max_results * 2]:  # Get more than needed for ranking
            score_data = cls._calculate_vendor_score(vendor, user_point, user_preferences)
            vendors_data.append(score_data)
        
        # Sort by score (descending) and limit
        vendors_data.sort(key=lambda x: x['final_score'], reverse=True)
        vendors_data = vendors_data[:max_results]
        
        # Cache the result
        cache.set(cache_key, vendors_data, timeout=cls.CACHE_TIMEOUTS['nearby_vendors'])
        
        return vendors_data
    
    @classmethod
    def get_ar_markers(cls, lat, lng, radius_m, user_tier='SILVER'):
        """
        Get AR markers for nearby vendors.
        Optimized for real-time AR experience.
        """
        # Generate cache key
        cache_key = f"ar_markers_{lat:.4f}_{lng:.4f}_{radius_m}_{user_tier}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Create user point
        user_point = Point(lng, lat, srid=4326)
        
        # Tier-based limits for AR
        tier_limits = {
            'SILVER': 10,
            'GOLD': 25,
            'DIAMOND': 50,
            'PLATINUM': 100,
        }
        limit = tier_limits.get(user_tier, 10)
        
        # Get nearby vendors with spatial query
        vendors = Vendor.objects.filter(
            is_active=True,
            location__distance_lte=(user_point, radius_m)
        ).annotate(
            distance_m=Distance('location', user_point) * 111320
        ).order_by('distance_m')[:limit]
        
        # Format for AR markers
        markers = []
        for vendor in vendors:
            markers.append({
                'id': str(vendor.id),
                'name': vendor.name,
                'category': vendor.category,
                'tier': vendor.tier,
                'lat': vendor.lat,
                'lng': vendor.lng,
                'distance_m': round(vendor.distance_m.m, 1),
                'logo_url': vendor.logo_url,
                'has_promotion': vendor.promotions.filter(
                    is_active=True,
                    start_time__lte=timezone.now(),
                    end_time__gte=timezone.now()
                ).exists(),
                'tier_color': cls._get_tier_color(vendor.tier),
            })
        
        # Cache for short duration (AR needs fresh data)
        cache.set(cache_key, markers, timeout=cls.CACHE_TIMEOUTS['ar_markers'])
        
        return markers
    
    @classmethod
    def get_vendor_detail(cls, vendor_id, user_lat=None, user_lng=None):
        """
        Get detailed vendor information.
        """
        # Generate cache key
        cache_key = f"vendor_detail_{vendor_id}_{user_lat}_{user_lng}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            vendor = Vendor.objects.get(id=vendor_id, is_active=True)
        except Vendor.DoesNotExist:
            return None
        
        # Calculate distance if user location provided
        distance_m = None
        if user_lat and user_lng:
            user_point = Point(user_lng, user_lat, srid=4326)
            distance_m = vendor.location.distance(user_point) * 111320
        
        # Get active promotions
        promotions = vendor.get_active_promotions()
        
        # Get approved reels
        reels = vendor.reels.filter(
            is_active=True,
            is_approved=True
        ).order_by('-view_count')[:5]
        
        # Build response
        vendor_data = {
            'id': str(vendor.id),
            'name': vendor.name,
            'description': vendor.description,
            'category': vendor.category,
            'subcategory': vendor.subcategory,
            'tags': vendor.tags,
            'tier': vendor.tier,
            'is_verified': vendor.is_verified,
            'address': vendor.address,
            'phone': vendor.phone,
            'email': vendor.email,
            'website': vendor.website,
            'business_hours': vendor.business_hours,
            'logo_url': vendor.logo_url,
            'cover_image_url': vendor.cover_image_url,
            'location': {
                'lat': vendor.lat,
                'lng': vendor.lng,
            },
            'distance_m': round(distance_m, 1) if distance_m else None,
            'popularity_score': vendor.popularity_score,
            'promotions': [
                {
                    'id': str(promo.id),
                    'title': promo.title,
                    'description': promo.description,
                    'discount_type': promo.discount_type,
                    'discount_percent': promo.discount_percent,
                    'discount_amount': float(promo.discount_amount) if promo.discount_amount else None,
                    'is_flash_deal': promo.is_flash_deal,
                    'start_time': promo.start_time.isoformat(),
                    'end_time': promo.end_time.isoformat(),
                    'image_url': promo.image_url,
                    'remaining_uses': promo.get_remaining_uses(),
                }
                for promo in promotions
            ],
            'reels': [
                {
                    'id': str(reel.id),
                    'title': reel.title,
                    'description': reel.description,
                    'video_url': reel.video_url,
                    'thumbnail_url': reel.thumbnail_url,
                    'duration_seconds': reel.duration_seconds,
                    'view_count': reel.view_count,
                    'completion_rate': reel.completion_rate,
                    'cta_text': reel.cta_text,
                    'cta_url': reel.cta_url,
                }
                for reel in reels
            ],
            'navigation_urls': cls._get_navigation_urls(vendor),
        }
        
        # Cache the result
        cache.set(cache_key, vendor_data, timeout=cls.CACHE_TIMEOUTS['vendor_detail'])
        
        return vendor_data
    
    @classmethod
    def search_vendors(cls, query_text, lat=None, lng=None, radius_m=5000, 
                      user_tier='SILVER', limit=20):
        """
        Search vendors by text query with NLP processing.
        """
        # Generate cache key
        cache_key = f"search_{query_text}_{lat}_{lng}_{radius_m}_{user_tier}_{limit}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Extract intent from query (simplified NLP)
        extracted_intent = cls._extract_search_intent(query_text)
        
        # Base queryset
        vendors = Vendor.objects.filter(is_active=True)
        
        # Apply filters based on extracted intent
        if extracted_intent['category']:
            vendors = vendors.filter(category__icontains=extracted_intent['category'])
        
        if extracted_intent['price_range']:
            # This would integrate with vendor pricing tiers
            pass
        
        # Apply location filter if provided
        if lat and lng:
            user_point = Point(lng, lat, srid=4326)
            vendors = vendors.filter(
                location__distance_lte=(user_point, radius_m)
            ).annotate(
                distance_m=Distance('location', user_point) * 111320
            )
        
        # Text search
        vendors = vendors.filter(
            models.Q(name__icontains=query_text) |
            models.Q(description__icontains=query_text) |
            models.Q(tags__contains=[query_text])
        )
        
        # Limit results
        vendors = vendors[:limit]
        
        # Calculate scores and format results
        results = []
        user_point = Point(lng, lat, srid=4326) if lat and lng else None
        
        for vendor in vendors:
            vendor_data = {
                'id': str(vendor.id),
                'name': vendor.name,
                'category': vendor.category,
                'subcategory': vendor.subcategory,
                'tier': vendor.tier,
                'is_verified': vendor.is_verified,
                'logo_url': vendor.logo_url,
                'location': {
                    'lat': vendor.lat,
                    'lng': vendor.lng,
                },
                'distance_m': round(vendor.distance_m.m, 1) if hasattr(vendor, 'distance_m') else None,
                'relevance_score': cls._calculate_relevance_score(vendor, query_text),
                'extracted_intent': extracted_intent,
            }
            
            # Calculate final score if location provided
            if user_point:
                score_data = cls._calculate_vendor_score(vendor, user_point)
                vendor_data['final_score'] = score_data['final_score']
            
            results.append(vendor_data)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('final_score', x['relevance_score']), reverse=True)
        
        # Cache the result
        cache.set(cache_key, results, timeout=300)  # 5 minutes
        
        return results
    
    @classmethod
    def get_tags(cls, category=None):
        """
        Get available tags for browsing.
        """
        cache_key = f"tags_{category or 'all'}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        tags = Tag.objects.filter(is_active=True)
        
        if category:
            tags = tags.filter(category=category)
        
        tags_data = [
            {
                'id': str(tag.id),
                'name': tag.name,
                'slug': tag.slug,
                'description': tag.description,
                'icon_url': tag.icon_url,
                'color': tag.color,
                'category': tag.category,
                'vendor_count': tag.vendor_count,
            }
            for tag in tags.order_by('category', 'sort_order', 'name')
        ]
        
        cache.set(cache_key, tags_data, timeout=cls.CACHE_TIMEOUTS['tags'])
        
        return tags_data
    
    @classmethod
    def get_cities(cls):
        """
        Get available cities with vendor counts.
        """
        cache_key = "cities"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        cities = City.objects.filter(is_active=True).order_by('sort_order', 'name')
        
        cities_data = []
        for city in cities:
            # Get areas for this city
            areas = city.areas.filter(is_active=True).order_by('sort_order', 'name')
            
            cities_data.append({
                'id': str(city.id),
                'name': city.name,
                'slug': city.slug,
                'location': {
                    'lat': city.lat,
                    'lng': city.lng,
                },
                'vendor_count': city.vendor_count,
                'areas': [
                    {
                        'id': str(area.id),
                        'name': area.name,
                        'slug': area.slug,
                        'location': {
                            'lat': area.lat,
                            'lng': area.lng,
                        },
                        'vendor_count': area.vendor_count,
                    }
                    for area in areas
                ],
            })
        
        cache.set(cache_key, cities_data, timeout=cls.CACHE_TIMEOUTS['cities'])
        
        return cities_data
    
    @classmethod
    def get_promotions_strip(cls, lat=None, lng=None, radius_m=5000, limit=20):
        """
        Get promotions strip (all active promotions, not just flash deals).
        """
        cache_key = f"promotions_strip_{lat}_{lng}_{radius_m}_{limit}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        promotions = Promotion.objects.filter(
            is_active=True,
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).select_related('vendor')
        
        # Apply location filter if provided
        if lat and lng:
            user_point = Point(lng, lat, srid=4326)
            promotions = promotions.filter(
                vendor__location__distance_lte=(user_point, radius_m)
            )
        
        promotions = promotions.order_by('-is_flash_deal', '-discount_percent')[:limit]
        
        promotions_data = [
            {
                'id': str(promo.id),
                'title': promo.title,
                'description': promo.description,
                'discount_type': promo.discount_type,
                'discount_percent': promo.discount_percent,
                'discount_amount': float(promo.discount_amount) if promo.discount_amount else None,
                'is_flash_deal': promo.is_flash_deal,
                'vendor': {
                    'id': str(promo.vendor.id),
                    'name': promo.vendor.name,
                    'category': promo.vendor.category,
                    'logo_url': promo.vendor.logo_url,
                    'location': {
                        'lat': promo.vendor.lat,
                        'lng': promo.vendor.lng,
                    },
                },
                'start_time': promo.start_time.isoformat(),
                'end_time': promo.end_time.isoformat(),
                'image_url': promo.image_url,
                'remaining_uses': promo.get_remaining_uses(),
            }
            for promo in promotions
        ]
        
        cache.set(cache_key, promotions_data, timeout=cls.CACHE_TIMEOUTS['promotions'])
        
        return promotions_data
    
    # Private helper methods
    
    @classmethod
    def _calculate_vendor_score(cls, vendor, user_point, user_preferences=None):
        """
        Calculate vendor score using exact ranking formula.
        Formula: Relevance×0.30 + Distance×0.25 + Offer×0.15 + Popularity×0.15 + Tier×0.15
        """
        # 1. Relevance Score (0-1)
        relevance_score = cls._calculate_relevance_score(vendor, user_preferences)
        
        # 2. Distance Score (0-1, closer is better)
        distance_m = vendor.location.distance(user_point) * 111320
        distance_score = cls._calculate_distance_score(distance_m)
        
        # 3. Offer Score (0-1)
        offer_score = cls._calculate_offer_score(vendor)
        
        # 4. Popularity Score (0-1, normalized)
        popularity_score = cls._calculate_popularity_score(vendor)
        
        # 5. Tier Score (0-1, from plan)
        tier_score = cls.TIER_SCORES.get(vendor.tier, 0.25)
        
        # Apply weighted formula
        weighted_score = (
            relevance_score * cls.RANKING_WEIGHTS['relevance'] +
            distance_score * cls.RANKING_WEIGHTS['distance'] +
            offer_score * cls.RANKING_WEIGHTS['offer'] +
            popularity_score * cls.RANKING_WEIGHTS['popularity'] +
            tier_score * cls.RANKING_WEIGHTS['tier']
        )
        
        # Apply system tag boosts AFTER weighted formula
        final_score = weighted_score
        for tag in vendor.system_tags:
            if tag in cls.SYSTEM_TAG_BOOSTS:
                final_score += cls.SYSTEM_TAG_BOOSTS[tag]
        
        # Cap score at 1.0
        final_score = min(final_score, 1.0)
        
        return {
            'vendor_id': str(vendor.id),
            'relevance_score': relevance_score,
            'distance_score': distance_score,
            'offer_score': offer_score,
            'popularity_score': popularity_score,
            'tier_score': tier_score,
            'weighted_score': weighted_score,
            'final_score': final_score,
            'distance_m': round(distance_m, 1),
        }
    
    @classmethod
    def _calculate_relevance_score(cls, vendor, user_preferences=None):
        """
        Calculate relevance score based on user preferences.
        """
        base_score = 0.5  # Base relevance
        
        # Boost for verified vendors
        if vendor.is_verified:
            base_score += 0.2
        
        # Boost based on user preferences
        if user_preferences:
            # Category preference
            preferred_categories = user_preferences.get('preferred_category_slugs', [])
            if vendor.category in preferred_categories:
                base_score += 0.2
            
            # Price range preference
            preferred_price_range = user_preferences.get('price_range', 'MID')
            # This would integrate with vendor pricing tiers
            if preferred_price_range == 'BUDGET' and vendor.tier in ['SILVER', 'GOLD']:
                base_score += 0.1
            elif preferred_price_range == 'PREMIUM' and vendor.tier in ['DIAMOND', 'PLATINUM']:
                base_score += 0.1
        
        return min(base_score, 1.0)
    
    @classmethod
    def _calculate_distance_score(cls, distance_m):
        """
        Calculate distance score (closer is better).
        """
        # Very close (0-100m): 1.0
        if distance_m <= 100:
            return 1.0
        # Close (100-500m): 0.8-1.0
        elif distance_m <= 500:
            return 1.0 - (distance_m - 100) / 400 * 0.2
        # Medium (500m-2km): 0.4-0.8
        elif distance_m <= 2000:
            return 0.8 - (distance_m - 500) / 1500 * 0.4
        # Far (2km-5km): 0.1-0.4
        elif distance_m <= 5000:
            return 0.4 - (distance_m - 2000) / 3000 * 0.3
        # Very far (>5km): 0.1
        else:
            return 0.1
    
    @classmethod
    def _calculate_offer_score(cls, vendor):
        """
        Calculate offer score based on active promotions.
        """
        active_promotions = vendor.get_active_promotions()
        
        if not active_promotions:
            return 0.0
        
        # Highest discount percentage
        max_discount = max([p.discount_percent or 0 for p in active_promotions])
        
        # Flash deals get extra boost
        has_flash_deal = any([p.is_flash_deal for p in active_promotions])
        
        # Base score from discount percentage
        score = min(max_discount / 100, 0.8)
        
        # Flash deal boost
        if has_flash_deal:
            score += 0.2
        
        return min(score, 1.0)
    
    @classmethod
    def _calculate_popularity_score(cls, vendor):
        """
        Calculate normalized popularity score.
        """
        if vendor.popularity_score <= 0:
            return 0.0
        
        # Normalize popularity score (assuming max 100)
        return min(vendor.popularity_score / 100, 1.0)
    
    @classmethod
    def _extract_search_intent(cls, query_text):
        """
        Extract search intent using rule-based NLP.
        """
        query_lower = query_text.lower()
        
        # Category keywords
        category_keywords = {
            'restaurant': 'RESTAURANT',
            'food': 'RESTAURANT',
            'cafe': 'CAFE',
            'coffee': 'CAFE',
            'shopping': 'SHOPPING',
            'retail': 'SHOPPING',
            'grocery': 'GROCERY',
            'supermarket': 'GROCERY',
            'pharmacy': 'PHARMACY',
            'medical': 'PHARMACY',
            'gas': 'GAS_STATION',
            'fuel': 'GAS_STATION',
            'bank': 'BANK',
            'atm': 'BANK',
            'gym': 'GYM',
            'fitness': 'GYM',
            'beauty': 'BEAUTY',
            'salon': 'BEAUTY',
            'hotel': 'HOTEL',
            'lodging': 'HOTEL',
        }
        
        # Price range keywords
        price_keywords = {
            'cheap': 'BUDGET',
            'budget': 'BUDGET',
            'affordable': 'BUDGET',
            'expensive': 'PREMIUM',
            'premium': 'PREMIUM',
            'luxury': 'PREMIUM',
            'mid': 'MID',
            'moderate': 'MID',
        }
        
        extracted_category = None
        for keyword, category in category_keywords.items():
            if keyword in query_lower:
                extracted_category = category
                break
        
        extracted_price_range = None
        for keyword, price_range in price_keywords.items():
            if keyword in query_lower:
                extracted_price_range = price_range
                break
        
        return {
            'category': extracted_category,
            'price_range': extracted_price_range,
            'query_text': query_text,
        }
    
    @classmethod
    def _get_tier_color(cls, tier):
        """
        Get color for vendor tier.
        """
        tier_colors = {
            'SILVER': '#C0C0C0',
            'GOLD': '#FFD700',
            'DIAMOND': '#B9F2FF',
            'PLATINUM': '#E5E4E2',
        }
        return tier_colors.get(tier, '#CCCCCC')
    
    @classmethod
    def _get_navigation_urls(cls, vendor):
        """
        Generate navigation URLs for vendor.
        """
        if not vendor.lat or not vendor.lng:
            return {}
        
        lat, lng = vendor.lat, vendor.lng
        name = vendor.name.replace(' ', '+')
        
        return {
            'google_maps_app': f'comgooglemaps://?q={name}&center={lat},{lng}',
            'google_maps_web': f'https://maps.google.com/?q={name}&center={lat},{lng}',
            'apple_maps': f'http://maps.apple.com/?q={name}&sll={lat},{lng}',
        }
