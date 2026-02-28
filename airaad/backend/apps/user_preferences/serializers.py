from rest_framework import serializers
from django.core.exceptions import ValidationError
import re

from .models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for UserPreference model.
    """
    notifications = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPreference
        fields = [
            'default_view',
            'search_radius_m',
            'show_open_now_only',
            'preferred_category_slugs',
            'price_range',
            'theme',
            'notifications',
            'location',
            'updated_at',
            'created_at',
        ]
        read_only_fields = ['updated_at', 'created_at']
    
    def get_notifications(self, obj):
        """Get notification preferences as nested object."""
        return {
            'nearby_deals': obj.notifications_nearby_deals,
            'flash_deals': obj.notifications_flash_deals,
            'new_vendors': obj.notifications_new_vendors,
            'all_off': obj.notifications_all_off,
        }
    
    def get_location(self, obj):
        """Get location preferences as nested object."""
        return {
            'auto_enabled': obj.auto_location_enabled,
            'manual_lat': float(obj.manual_location_lat) if obj.manual_location_lat else None,
            'manual_lng': float(obj.manual_location_lng) if obj.manual_location_lng else None,
            'manual_name': obj.manual_location_name,
        }


class UserPreferenceUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user preferences.
    """
    default_view = serializers.ChoiceField(
        required=False,
        choices=['AR', 'MAP', 'LIST'],
        error_messages={
            'invalid_choice': 'Invalid view type. Choose from AR, MAP, or LIST.',
        }
    )
    search_radius_m = serializers.IntegerField(
        required=False,
        min_value=100,
        max_value=5000,
        error_messages={
            'min_value': 'Search radius must be at least 100 meters',
            'max_value': 'Search radius cannot exceed 5000 meters',
        }
    )
    show_open_now_only = serializers.BooleanField(required=False)
    preferred_category_slugs = serializers.ListField(
        required=False,
        child=serializers.CharField(max_length=50),
        allow_empty=True,
        error_messages={
            'invalid': 'Categories must be a list of strings',
        }
    )
    price_range = serializers.ChoiceField(
        required=False,
        choices=['BUDGET', 'MID', 'PREMIUM'],
        error_messages={
            'invalid_choice': 'Invalid price range. Choose from BUDGET, MID, or PREMIUM.',
        }
    )
    theme = serializers.ChoiceField(
        required=False,
        choices=['DARK', 'LIGHT', 'SYSTEM'],
        error_messages={
            'invalid_choice': 'Invalid theme. Choose from DARK, LIGHT, or SYSTEM.',
        }
    )
    notifications_nearby_deals = serializers.BooleanField(required=False)
    notifications_flash_deals = serializers.BooleanField(required=False)
    notifications_new_vendors = serializers.BooleanField(required=False)
    notifications_all_off = serializers.BooleanField(required=False)
    auto_location_enabled = serializers.BooleanField(required=False)
    manual_location_lat = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid latitude format',
            'max_decimal_places': 'Invalid latitude precision',
        }
    )
    manual_location_lng = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        allow_null=True,
        error_messages={
            'max_digits': 'Invalid longitude format',
            'max_decimal_places': 'Invalid longitude precision',
        }
    )
    manual_location_name = serializers.CharField(
        required=False,
        max_length=100,
        allow_blank=True,
        error_messages={
            'max_length': 'Location name cannot exceed 100 characters',
        }
    )
    
    def validate_preferred_category_slugs(self, value):
        """Validate preferred categories."""
        if len(value) > 20:
            raise serializers.ValidationError("Cannot select more than 20 categories")
        
        # Check for duplicates
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate categories are not allowed")
        
        # Validate category slug format
        for slug in value:
            if not re.match(r'^[a-z0-9\-_]+$', slug):
                raise serializers.ValidationError(f"Invalid category slug format: {slug}")
        
        return value
    
    def validate_manual_location_lat(self, value):
        """Validate latitude range."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_manual_location_lng(self, value):
        """Validate longitude range."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate(self, attrs):
        """Validate location consistency."""
        manual_lat = attrs.get('manual_location_lat')
        manual_lng = attrs.get('manual_location_lng')
        manual_name = attrs.get('manual_location_name')
        
        # If setting manual location, all fields should be provided
        if (manual_lat is not None or manual_lng is not None or manual_name is not None):
            if not all([manual_lat, manual_lng, manual_name]):
                raise serializers.ValidationError(
                    "All manual location fields (lat, lng, name) must be provided together"
                )
        
        return attrs


class SearchHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for UserSearchHistory model.
    """
    query_type_display = serializers.CharField(source='get_query_type_display', read_only=True)
    
    class Meta:
        model = UserSearchHistory
        fields = [
            'id',
            'query_text',
            'query_type',
            'query_type_display',
            'extracted_category',
            'extracted_intent',
            'extracted_price_range',
            'search_lat',
            'search_lng',
            'search_radius_m',
            'result_count',
            'navigated_to_vendor_id',
            'searched_at',
        ]
        read_only_fields = ['id', 'searched_at']
    
    def to_representation(self, instance):
        """Custom representation with formatted data."""
        data = super().to_representation(instance)
        
        # Convert Decimal fields to float for JSON serialization
        if data.get('search_lat'):
            data['search_lat'] = float(data['search_lat'])
        if data.get('search_lng'):
            data['search_lng'] = float(data['search_lng'])
        
        return data


class UserVendorInteractionSerializer(serializers.ModelSerializer):
    """
    Serializer for UserVendorInteraction model.
    """
    interaction_type_display = serializers.CharField(source='get_interaction_type_display', read_only=True)
    
    class Meta:
        model = UserVendorInteraction
        fields = [
            'id',
            'vendor_id',
            'interaction_type',
            'interaction_type_display',
            'session_id',
            'lat',
            'lng',
            'metadata',
            'interacted_at',
        ]
        read_only_fields = ['id', 'interacted_at']
    
    def to_representation(self, instance):
        """Custom representation with formatted data."""
        data = super().to_representation(instance)
        
        # Convert Decimal fields to float for JSON serialization
        if data.get('lat'):
            data['lat'] = float(data['lat'])
        if data.get('lng'):
            data['lng'] = float(data['lng'])
        
        return data


class FlashDealAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for FlashDealAlert model.
    """
    
    class Meta:
        model = FlashDealAlert
        fields = [
            'id',
            'discount_id',
            'vendor_id',
            'alerted_at',
            'dismissed',
            'dismissed_at',
            'tapped',
            'tapped_at',
        ]
        read_only_fields = ['id', 'alerted_at']


class NearbyReelViewSerializer(serializers.ModelSerializer):
    """
    Serializer for NearbyReelView model.
    """
    
    class Meta:
        model = NearbyReelView
        fields = [
            'id',
            'reel_id',
            'vendor_id',
            'watched_seconds',
            'completed',
            'cta_tapped',
            'lat',
            'lng',
            'viewed_at',
        ]
        read_only_fields = ['id', 'viewed_at']
    
    def to_representation(self, instance):
        """Custom representation with formatted data."""
        data = super().to_representation(instance)
        
        # Convert Decimal fields to float for JSON serialization
        if data.get('lat'):
            data['lat'] = float(data['lat'])
        if data.get('lng'):
            data['lng'] = float(data['lng'])
        
        return data


class InteractionTrackingSerializer(serializers.Serializer):
    """
    Serializer for interaction tracking requests.
    """
    vendor_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Vendor ID is required',
            'invalid': 'Invalid Vendor ID format',
        }
    )
    interaction_type = serializers.ChoiceField(
        required=True,
        choices=UserVendorInteraction.INTERACTION_TYPES,
        error_messages={
            'required': 'Interaction type is required',
            'invalid_choice': 'Invalid interaction type',
        }
    )
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            'invalid': 'Invalid session ID format',
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
    metadata = serializers.DictField(
        required=False,
        allow_empty=True,
        child=serializers.CharField(),
        error_messages={
            'invalid': 'Metadata must be a dictionary',
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


class ReelViewTrackingSerializer(serializers.Serializer):
    """
    Serializer for reel view tracking requests.
    """
    reel_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Reel ID is required',
            'invalid': 'Invalid Reel ID format',
        }
    )
    vendor_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Vendor ID is required',
            'invalid': 'Invalid Vendor ID format',
        }
    )
    watched_seconds = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        error_messages={
            'min_value': 'Watched seconds cannot be negative',
        }
    )
    completed = serializers.BooleanField(required=False, default=False)
    cta_tapped = serializers.BooleanField(required=False, default=False)
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


class FlashDealAlertCreateSerializer(serializers.Serializer):
    """
    Serializer for creating flash deal alerts.
    """
    discount_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Discount ID is required',
            'invalid': 'Invalid Discount ID format',
        }
    )
    vendor_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Vendor ID is required',
            'invalid': 'Invalid Vendor ID format',
        }
    )


class FlashDealAlertUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating flash deal alerts.
    """
    discount_id = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Discount ID is required',
            'invalid': 'Invalid Discount ID format',
        }
    )
    action = serializers.ChoiceField(
        required=True,
        choices=['dismiss', 'tap'],
        error_messages={
            'required': 'Action is required',
            'invalid_choice': 'Invalid action. Use "dismiss" or "tap"',
        }
    )


class MigrationSerializer(serializers.Serializer):
    """
    Serializer for guest data migration.
    """
    guest_token = serializers.UUIDField(
        required=True,
        error_messages={
            'required': 'Guest token is required',
            'invalid': 'Invalid guest token format',
        }
    )
