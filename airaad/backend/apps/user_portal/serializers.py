from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
import re

from .models import Vendor, Promotion, VendorReel, Tag, City, Area


class VendorSerializer(serializers.ModelSerializer):
    """
    Serializer for Vendor model (basic info).
    """
    lat = serializers.ReadOnlyField()
    lng = serializers.ReadOnlyField()
    tier_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Vendor
        fields = [
            'id',
            'name',
            'description',
            'category',
            'subcategory',
            'tags',
            'tier',
            'is_verified',
            'address',
            'phone',
            'email',
            'website',
            'business_hours',
            'logo_url',
            'cover_image_url',
            'lat',
            'lng',
            'popularity_score',
            'system_tags',
            'tier_score',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'popularity_score',
            'system_tags',
            'created_at',
            'updated_at',
        ]


class VendorDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed vendor information.
    """
    lat = serializers.ReadOnlyField()
    lng = serializers.ReadOnlyField()
    tier_score = serializers.ReadOnlyField()
    promotions = serializers.SerializerMethodField()
    reels = serializers.SerializerMethodField()
    navigation_urls = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            'id',
            'name',
            'description',
            'category',
            'subcategory',
            'tags',
            'tier',
            'is_verified',
            'address',
            'phone',
            'email',
            'website',
            'business_hours',
            'logo_url',
            'cover_image_url',
            'lat',
            'lng',
            'popularity_score',
            'system_tags',
            'tier_score',
            'promotions',
            'reels',
            'navigation_urls',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'popularity_score',
            'system_tags',
            'created_at',
            'updated_at',
        ]
    
    def get_promotions(self, obj):
        """Get active promotions."""
        promotions = obj.get_active_promotions()
        return PromotionSerializer(promotions, many=True).data
    
    def get_reels(self, obj):
        """Get approved reels."""
        reels = obj.reels.filter(
            is_active=True,
            is_approved=True
        ).order_by('-view_count')[:5]
        return VendorReelSerializer(reels, many=True).data
    
    def get_navigation_urls(self, obj):
        """Get navigation URLs."""
        if not obj.lat or not obj.lng:
            return {}
        
        lat, lng = obj.lat, obj.lng
        name = obj.name.replace(' ', '+')
        
        return {
            'google_maps_app': f'comgooglemaps://?q={name}&center={lat},{lng}',
            'google_maps_web': f'https://maps.google.com/?q={name}&center={lat},{lng}',
            'apple_maps': f'http://maps.apple.com/?q={name}&sll={lat},{lng}',
        }


class PromotionSerializer(serializers.ModelSerializer):
    """
    Serializer for Promotion model.
    """
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_category = serializers.CharField(source='vendor.category', read_only=True)
    vendor_logo_url = serializers.URLField(source='vendor.logo_url', read_only=True)
    vendor_location = serializers.SerializerMethodField()
    is_currently_active = serializers.ReadOnlyField()
    remaining_uses = serializers.ReadOnlyField()
    
    class Meta:
        model = Promotion
        fields = [
            'id',
            'vendor_name',
            'vendor_category',
            'vendor_logo_url',
            'vendor_location',
            'title',
            'description',
            'discount_type',
            'discount_percent',
            'discount_amount',
            'is_flash_deal',
            'flash_duration_minutes',
            'start_time',
            'end_time',
            'is_active',
            'is_currently_active',
            'usage_limit',
            'usage_count',
            'remaining_uses',
            'image_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'usage_count',
            'created_at',
            'updated_at',
        ]
    
    def get_vendor_location(self, obj):
        """Get vendor location."""
        if obj.vendor.lat and obj.vendor.lng:
            return {
                'lat': obj.vendor.lat,
                'lng': obj.vendor.lng,
            }
        return None


class VendorReelSerializer(serializers.ModelSerializer):
    """
    Serializer for VendorReel model.
    """
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_category = serializers.CharField(source='vendor.category', read_only=True)
    vendor_logo_url = serializers.URLField(source='vendor.logo_url', read_only=True)
    completion_rate = serializers.ReadOnlyField()
    cta_tap_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = VendorReel
        fields = [
            'id',
            'vendor_name',
            'vendor_category',
            'vendor_logo_url',
            'title',
            'description',
            'video_url',
            'thumbnail_url',
            'duration_seconds',
            'view_count',
            'cta_tap_count',
            'completion_count',
            'completion_rate',
            'cta_tap_rate',
            'cta_text',
            'cta_url',
            'is_active',
            'is_approved',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'view_count',
            'cta_tap_count',
            'completion_count',
            'created_at',
            'updated_at',
        ]


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for Tag model.
    """
    
    class Meta:
        model = Tag
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'icon_url',
            'color',
            'category',
            'sort_order',
            'vendor_count',
            'search_count',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'vendor_count',
            'search_count',
            'created_at',
            'updated_at',
        ]


class CitySerializer(serializers.ModelSerializer):
    """
    Serializer for City model.
    """
    lat = serializers.ReadOnlyField()
    lng = serializers.ReadOnlyField()
    areas = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = [
            'id',
            'name',
            'slug',
            'lat',
            'lng',
            'bounds_north',
            'bounds_south',
            'bounds_east',
            'bounds_west',
            'country',
            'is_active',
            'sort_order',
            'vendor_count',
            'areas',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'vendor_count',
            'created_at',
            'updated_at',
        ]
    
    def get_areas(self, obj):
        """Get areas for this city."""
        areas = obj.areas.filter(is_active=True).order_by('sort_order', 'name')
        return AreaSerializer(areas, many=True).data


class AreaSerializer(serializers.ModelSerializer):
    """
    Serializer for Area model.
    """
    lat = serializers.ReadOnlyField()
    lng = serializers.ReadOnlyField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = Area
        fields = [
            'id',
            'city',
            'city_name',
            'name',
            'slug',
            'lat',
            'lng',
            'bounds_north',
            'bounds_south',
            'bounds_east',
            'bounds_west',
            'is_active',
            'sort_order',
            'vendor_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'vendor_count',
            'created_at',
            'updated_at',
        ]


class SearchQuerySerializer(serializers.Serializer):
    """
    Serializer for search queries.
    """
    q = serializers.CharField(
        required=True,
        min_length=1,
        max_length=200,
        error_messages={
            'required': 'Search query is required',
            'min_length': 'Search query cannot be empty',
            'max_length': 'Search query is too long',
        }
    )
    lat = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    radius = serializers.IntegerField(
        required=False,
        default=5000,
        min_value=100,
        max_value=50000,
        error_messages={
            'min_value': 'Search radius must be at least 100 meters',
            'max_value': 'Search radius cannot exceed 50km',
        }
    )
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        error_messages={
            'min_value': 'Limit must be at least 1',
            'max_value': 'Limit cannot exceed 100',
        }
    )
    
    def validate_lat(self, value):
        """Validate latitude range."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        """Validate longitude range."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class VoiceSearchSerializer(serializers.Serializer):
    """
    Serializer for voice search queries.
    """
    transcript = serializers.CharField(
        required=True,
        min_length=1,
        max_length=500,
        error_messages={
            'required': 'Voice transcript is required',
            'min_length': 'Voice transcript cannot be empty',
            'max_length': 'Voice transcript is too long',
        }
    )
    lat = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    radius = serializers.IntegerField(
        required=False,
        default=5000,
        min_value=100,
        max_value=50000,
        error_messages={
            'min_value': 'Search radius must be at least 100 meters',
            'max_value': 'Search radius cannot exceed 50km',
        }
    )
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        error_messages={
            'min_value': 'Limit must be at least 1',
            'max_value': 'Limit cannot exceed 100',
        }
    )
    
    def validate_lat(self, value):
        """Validate latitude range."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        """Validate longitude range."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class NearbyVendorsSerializer(serializers.Serializer):
    """
    Serializer for nearby vendors request.
    """
    lat = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
        error_messages={
            'required': 'Latitude is required',
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    lng = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
        error_messages={
            'required': 'Longitude is required',
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    radius = serializers.IntegerField(
        required=False,
        default=1000,
        min_value=100,
        max_value=10000,
        error_messages={
            'min_value': 'Search radius must be at least 100 meters',
            'max_value': 'Search radius cannot exceed 10km',
        }
    )
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        error_messages={
            'max_length': 'Category name is too long',
        }
    )
    limit = serializers.IntegerField(
        required=False,
        default=50,
        min_value=1,
        max_value=200,
        error_messages={
            'min_value': 'Limit must be at least 1',
            'max_value': 'Limit cannot exceed 200',
        }
    )
    
    def validate_lat(self, value):
        """Validate latitude range."""
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        """Validate longitude range."""
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class ARMarkersSerializer(serializers.Serializer):
    """
    Serializer for AR markers request.
    """
    lat = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
        error_messages={
            'required': 'Latitude is required',
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    lng = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
        error_messages={
            'required': 'Longitude is required',
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    radius = serializers.IntegerField(
        required=False,
        default=500,
        min_value=100,
        max_value=2000,
        error_messages={
            'min_value': 'Search radius must be at least 100 meters',
            'max_value': 'AR search radius cannot exceed 2km',
        }
    )
    
    def validate_lat(self, value):
        """Validate latitude range."""
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        """Validate longitude range."""
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class VendorDetailRequestSerializer(serializers.Serializer):
    """
    Serializer for vendor detail request.
    """
    lat = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    
    def validate_lat(self, value):
        """Validate latitude range."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        """Validate longitude range."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
