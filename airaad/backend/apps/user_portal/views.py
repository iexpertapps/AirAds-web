from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q

from .models import Vendor, Promotion, VendorReel, Tag, City, Area
from .services import DiscoveryService
from .serializers import (
    VendorSerializer,
    VendorDetailSerializer,
    PromotionSerializer,
    VendorReelSerializer,
    TagSerializer,
    CitySerializer,
    SearchQuerySerializer,
)
from common.responses import success_response, error_response
from common.permissions import IsCustomerUser, IsGuestOrAuthenticated


class NearbyVendorsView(APIView):
    """
    Get nearby vendors with ranking algorithm.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get nearby vendors"""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 1000)
            category = request.query_params.get('category')
            limit = request.query_params.get('limit', 50)
            
            if not lat or not lng:
                return error_response(
                    message="Latitude and longitude are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert parameters
            try:
                lat = float(lat)
                lng = float(lng)
                radius = int(radius)
                limit = int(limit)
            except ValueError:
                return error_response(
                    message="Invalid parameter format",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user tier
            user_tier = 'SILVER'  # Default
            if request.user.is_authenticated:
                user_tier = getattr(request.user.customer_profile, 'subscription_tier', 'SILVER')
            
            # Get user preferences if authenticated
            user_preferences = None
            if request.user.is_authenticated:
                from apps.user_preferences.services import UserPreferenceService
                user_preferences = UserPreferenceService.get_preferences(request.user)
            
            # Get nearby vendors
            vendors_data = DiscoveryService.get_nearby_vendors(
                lat=lat,
                lng=lng,
                radius_m=radius,
                user_tier=user_tier,
                category=category,
                limit=limit,
                user_preferences=user_preferences
            )
            
            return success_response(
                data={
                    'vendors': vendors_data,
                    'count': len(vendors_data),
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                        'category': category,
                        'limit': limit,
                    }
                },
                message="Nearby vendors retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve nearby vendors",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ARMarkersView(APIView):
    """
    Get AR markers for nearby vendors.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get AR markers"""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 500)
            
            if not lat or not lng:
                return error_response(
                    message="Latitude and longitude are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert parameters
            try:
                lat = float(lat)
                lng = float(lng)
                radius = int(radius)
            except ValueError:
                return error_response(
                    message="Invalid parameter format",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user tier
            user_tier = 'SILVER'  # Default
            if request.user.is_authenticated:
                user_tier = getattr(request.user.customer_profile, 'subscription_tier', 'SILVER')
            
            # Get AR markers
            markers = DiscoveryService.get_ar_markers(
                lat=lat,
                lng=lng,
                radius_m=radius,
                user_tier=user_tier
            )
            
            return success_response(
                data={
                    'markers': markers,
                    'count': len(markers),
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                    }
                },
                message="AR markers retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve AR markers",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VendorDetailView(APIView):
    """
    Get detailed vendor information.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request, pk):
        """Get vendor details"""
        try:
            # Get user location
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            
            if lat and lng:
                try:
                    lat = float(lat)
                    lng = float(lng)
                except ValueError:
                    lat = lng = None
            
            # Get vendor details
            vendor_data = DiscoveryService.get_vendor_detail(
                vendor_id=pk,
                user_lat=lat,
                user_lng=lng
            )
            
            if not vendor_data:
                return error_response(
                    message="Vendor not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return success_response(
                data=vendor_data,
                message="Vendor details retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve vendor details",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SearchView(APIView):
    """
    Search vendors by text query.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Search vendors"""
        try:
            # Validate required parameters
            query = request.query_params.get('q', '').strip()
            if not query:
                return error_response(
                    message="Search query is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 5000)
            limit = request.query_params.get('limit', 20)
            
            # Convert parameters
            if lat and lng:
                try:
                    lat = float(lat)
                    lng = float(lng)
                    radius = int(radius)
                except ValueError:
                    lat = lng = None
            
            try:
                limit = int(limit)
            except ValueError:
                limit = 20
            
            # Get user tier
            user_tier = 'SILVER'  # Default
            if request.user.is_authenticated:
                user_tier = getattr(request.user.customer_profile, 'subscription_tier', 'SILVER')
            
            # Search vendors
            results = DiscoveryService.search_vendors(
                query_text=query,
                lat=lat,
                lng=lng,
                radius_m=radius,
                user_tier=user_tier,
                limit=limit
            )
            
            # Record search history
            if request.user.is_authenticated:
                from apps.user_preferences.services import SearchHistoryService
                SearchHistoryService.record_search(
                    user_or_guest=request.user,
                    query_text=query,
                    query_type='TEXT',
                    search_lat=lat,
                    search_lng=lng,
                    search_radius_m=radius,
                    result_count=len(results)
                )
            else:
                # Record guest search
                guest_token = request.headers.get('X-Guest-Token')
                if guest_token:
                    from apps.user_preferences.services import SearchHistoryService
                    SearchHistoryService.record_search(
                        user_or_guest=guest_token,
                        query_text=query,
                        query_type='TEXT',
                        search_lat=lat,
                        search_lng=lng,
                        search_radius_m=radius,
                        result_count=len(results)
                    )
            
            return success_response(
                data={
                    'results': results,
                    'count': len(results),
                    'query': query,
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                        'limit': limit,
                    }
                },
                message="Search completed successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Search failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VoiceSearchView(APIView):
    """
    Process voice search query.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def post(self, request):
        """Process voice search"""
        try:
            # Validate required parameters
            transcript = request.data.get('transcript', '').strip()
            if not transcript:
                return error_response(
                    message="Voice transcript is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional parameters
            lat = request.data.get('lat')
            lng = request.data.get('lng')
            radius = request.data.get('radius', 5000)
            limit = request.data.get('limit', 20)
            
            # Convert parameters
            if lat and lng:
                try:
                    lat = float(lat)
                    lng = float(lng)
                    radius = int(radius)
                except ValueError:
                    lat = lng = None
            
            try:
                limit = int(limit)
            except ValueError:
                limit = 20
            
            # Get user tier
            user_tier = 'SILVER'  # Default
            if request.user.is_authenticated:
                user_tier = getattr(request.user.customer_profile, 'subscription_tier', 'SILVER')
            
            # Process voice search (same as text search)
            results = DiscoveryService.search_vendors(
                query_text=transcript,
                lat=lat,
                lng=lng,
                radius_m=radius,
                user_tier=user_tier,
                limit=limit
            )
            
            # Record voice search history
            if request.user.is_authenticated:
                from apps.user_preferences.services import SearchHistoryService
                SearchHistoryService.record_search(
                    user_or_guest=request.user,
                    query_text=transcript,
                    query_type='VOICE',
                    search_lat=lat,
                    search_lng=lng,
                    search_radius_m=radius,
                    result_count=len(results)
                )
            else:
                # Record guest search
                guest_token = request.headers.get('X-Guest-Token')
                if guest_token:
                    from apps.user_preferences.services import SearchHistoryService
                    SearchHistoryService.record_search(
                        user_or_guest=guest_token,
                        query_text=transcript,
                        query_type='VOICE',
                        search_lat=lat,
                        search_lng=lng,
                        search_radius_m=radius,
                        result_count=len(results)
                    )
            
            return success_response(
                data={
                    'results': results,
                    'count': len(results),
                    'transcript': transcript,
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                        'limit': limit,
                    }
                },
                message="Voice search processed successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Voice search failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TagsView(APIView):
    """
    Get available tags for browsing.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get tags"""
        try:
            category = request.query_params.get('category')
            
            tags = DiscoveryService.get_tags(category=category)
            
            return success_response(
                data={
                    'tags': tags,
                    'count': len(tags),
                    'category': category,
                },
                message="Tags retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve tags",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionsStripView(APIView):
    """
    Get promotions strip (all active promotions).
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get promotions strip"""
        try:
            # Optional parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 5000)
            limit = request.query_params.get('limit', 20)
            
            # Convert parameters
            if lat and lng:
                try:
                    lat = float(lat)
                    lng = float(lng)
                    radius = int(radius)
                except ValueError:
                    lat = lng = None
            
            try:
                limit = int(limit)
            except ValueError:
                limit = 20
            
            # Get promotions
            promotions = DiscoveryService.get_promotions_strip(
                lat=lat,
                lng=lng,
                radius_m=radius,
                limit=limit
            )
            
            return success_response(
                data={
                    'promotions': promotions,
                    'count': len(promotions),
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                        'limit': limit,
                    }
                },
                message="Promotions retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve promotions",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CitiesView(APIView):
    """
    Get available cities with areas.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get cities"""
        try:
            cities = DiscoveryService.get_cities()
            
            return success_response(
                data={
                    'cities': cities,
                    'count': len(cities),
                },
                message="Cities retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve cities",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FlashDealsView(APIView):
    """
    Get flash deals for user notifications.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get flash deals"""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 5000)
            
            if not lat or not lng:
                return error_response(
                    message="Latitude and longitude are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert parameters
            try:
                lat = float(lat)
                lng = float(lng)
                radius = int(radius)
            except ValueError:
                return error_response(
                    message="Invalid parameter format",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get flash deals (promotions with is_flash_deal=True)
            from django.utils import timezone
            from datetime import timedelta
            
            now = timezone.now()
            ninety_minutes_ago = now - timedelta(minutes=90)
            
            flash_deals = Promotion.objects.filter(
                is_active=True,
                is_flash_deal=True,
                start_time__gte=ninety_minutes_ago,
                start_time__lte=now,
                end_time__gte=now
            ).select_related('vendor')
            
            # Apply location filter
            if lat and lng:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.db.models.functions import Distance
                
                user_point = Point(lng, lat, srid=4326)
                flash_deals = flash_deals.filter(
                    vendor__location__distance_lte=(user_point, radius)
                ).annotate(
                    distance_m=Distance('vendor__location', user_point) * 111320
                )
            
            # Format results
            deals_data = []
            for deal in flash_deals:
                deals_data.append({
                    'id': str(deal.id),
                    'title': deal.title,
                    'description': deal.description,
                    'discount_percent': deal.discount_percent,
                    'vendor': {
                        'id': str(deal.vendor.id),
                        'name': deal.vendor.name,
                        'category': deal.vendor.category,
                        'logo_url': deal.vendor.logo_url,
                        'location': {
                            'lat': deal.vendor.lat,
                            'lng': deal.vendor.lng,
                        },
                    },
                    'start_time': deal.start_time.isoformat(),
                    'end_time': deal.end_time.isoformat(),
                    'image_url': deal.image_url,
                    'distance_m': round(deal.distance_m.m, 1) if hasattr(deal, 'distance_m') else None,
                })
            
            return success_response(
                data={
                    'flash_deals': deals_data,
                    'count': len(deals_data),
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                    }
                },
                message="Flash deals retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve flash deals",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NearbyReelsView(APIView):
    """
    Get reels from nearby vendors.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get nearby reels"""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            radius = request.query_params.get('radius', 2000)
            limit = request.query_params.get('limit', 20)
            
            if not lat or not lng:
                return error_response(
                    message="Latitude and longitude are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert parameters
            try:
                lat = float(lat)
                lng = float(lng)
                radius = int(radius)
                limit = int(limit)
            except ValueError:
                return error_response(
                    message="Invalid parameter format",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get nearby vendors first
            from django.contrib.gis.geos import Point
            
            user_point = Point(lng, lat, srid=4326)
            nearby_vendors = Vendor.objects.filter(
                is_active=True,
                location__distance_lte=(user_point, radius)
            ).values_list('id', flat=True)
            
            # Get reels from nearby vendors
            reels = VendorReel.objects.filter(
                vendor_id__in=nearby_vendors,
                is_active=True,
                is_approved=True
            ).select_related('vendor').order_by('-view_count')[:limit]
            
            # Format results
            reels_data = []
            for reel in reels:
                reels_data.append({
                    'id': str(reel.id),
                    'title': reel.title,
                    'description': reel.description,
                    'video_url': reel.video_url,
                    'thumbnail_url': reel.thumbnail_url,
                    'duration_seconds': reel.duration_seconds,
                    'vendor': {
                        'id': str(reel.vendor.id),
                        'name': reel.vendor.name,
                        'category': reel.vendor.category,
                        'logo_url': reel.vendor.logo_url,
                    },
                    'view_count': reel.view_count,
                    'completion_rate': reel.completion_rate,
                    'cta_text': reel.cta_text,
                    'cta_url': reel.cta_url,
                })
            
            return success_response(
                data={
                    'reels': reels_data,
                    'count': len(reels_data),
                    'search_params': {
                        'lat': lat,
                        'lng': lng,
                        'radius': radius,
                        'limit': limit,
                    }
                },
                message="Nearby reels retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve nearby reels",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
