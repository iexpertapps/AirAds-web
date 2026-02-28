from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.cache import cache
import uuid
import math
from decimal import Decimal

from apps.customer_auth.models import CustomerUser
from .models_error import ErrorLog, ErrorPattern
from .models_backup import BackupLog, RecoveryLog

User = get_user_model()


class Vendor(models.Model):
    """
    Vendor model for User Portal discovery.
    SQLite-compatible with simple coordinates.
    """
    
    # Core vendor information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    
    # Location (Simple coordinates - SQLite compatible)
    lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Latitude in WGS84"
    )
    lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Longitude in WGS84"
    )
    
    # Category and tags
    category = models.CharField(max_length=50, db_index=True)
    subcategory = models.CharField(max_length=50, blank=True, db_index=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Subscription tier
    tier = models.CharField(
        max_length=10,
        choices=[
            ('SILVER', 'Silver'),
            ('GOLD', 'Gold'),
            ('DIAMOND', 'Diamond'),
            ('PLATINUM', 'Platinum'),
        ],
        default='SILVER',
        db_index=True
    )
    
    # Status and verification
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Business hours
    business_hours = models.JSONField(default=dict, blank=True)
    
    # Media
    logo_url = models.URLField(blank=True)
    cover_image_url = models.URLField(blank=True)
    
    # Analytics and popularity
    popularity_score = models.FloatField(default=0.0, db_index=True)
    interaction_count = models.IntegerField(default=0, db_index=True)
    
    # PostGIS location field for spatial queries
    location = PointField(geography=True, srid=4326, null=True, blank=True)
    
    # System tags for ranking boosts
    system_tags = models.JSONField(default=list, blank=True)  # ['new_vendor_boost', 'trending', 'verified']
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_vendors'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['tier', 'is_active']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['popularity_score', 'is_active']),
            models.Index(fields=['created_at', 'is_active']),
            models.Index(fields=['lat', 'lng']),  # Simple coordinate index
        ]
        ordering = ['-popularity_score', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"

    def save(self, *args, **kwargs):
        """Auto-populate location PointField from lat/lng."""
        if self.lat is not None and self.lng is not None:
            self.location = Point(float(self.lng), float(self.lat), srid=4326)
        super().save(*args, **kwargs)

    def get_tier_score(self):
        """Get normalized tier score (0-1)."""
        tier_scores = {
            'SILVER': 0.25,
            'GOLD': 0.50,
            'DIAMOND': 0.75,
            'PLATINUM': 1.00,
        }
        return tier_scores.get(self.tier, 0.25)

    def calculate_distance(self, lat, lng):
        """Calculate distance from given point in meters using Haversine formula."""
        if not self.lat or not self.lng or not lat or not lng:
            return None
        
        # Convert to radians
        lat1, lng1 = float(self.lat), float(self.lng)
        lat2, lng2 = float(lat), float(lng)
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in meters
        r = 6371000
        
        return c * r

    def get_active_promotions(self):
        """Get currently active promotions."""
        return self.promotions.filter(
            is_active=True,
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).order_by('-is_flash_deal', '-discount_percent')


class Promotion(models.Model):
    """
    Promotion/discount model for vendors.
    """
    
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
        ('BOGO', 'Buy One Get One'),
        ('FREE_ITEM', 'Free Item'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.CASCADE,
        related_name='promotions',
        null=True,
        blank=True,
    )
    
    # Promotion details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_percent = models.IntegerField(null=True, blank=True, help_text="For percentage discounts")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Flash deal settings
    is_flash_deal = models.BooleanField(default=False, db_index=True)
    flash_duration_minutes = models.IntegerField(default=60, help_text="Duration in minutes for flash deals")
    
    # Timing
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Usage limits
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Maximum uses, null for unlimited")
    usage_count = models.IntegerField(default=0)
    
    # Media
    image_url = models.URLField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_promotions'
        indexes = [
            models.Index(fields=['vendor_id', 'is_active', 'start_time']),
            models.Index(fields=['is_flash_deal', 'is_active', 'start_time']),
            models.Index(fields=['end_time', 'is_active']),
            models.Index(fields=['discount_percent']),
        ]
        ordering = ['-is_flash_deal', '-discount_percent', 'start_time']

    def __str__(self):
        return f"{self.title} - {self.vendor.name if self.vendor else 'No vendor'}"

    @property
    def is_currently_active(self):
        """Check if promotion is currently active."""
        now = timezone.now()
        return (
            self.is_active and
            self.start_time <= now <= self.end_time
        )

    def get_remaining_uses(self):
        """Get remaining uses if limited."""
        if self.usage_limit is None:
            return None
        return max(0, self.usage_limit - self.usage_count)


class VendorReel(models.Model):
    """
    Vendor reel/video content model.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.CASCADE,
        related_name='reels',
        null=True,
        blank=True,
    )
    
    # Reel content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    thumbnail_url = models.URLField()
    duration_seconds = models.IntegerField()
    
    # Engagement metrics
    view_count = models.IntegerField(default=0, db_index=True)
    cta_tap_count = models.IntegerField(default=0)
    completion_count = models.IntegerField(default=0)
    
    # Call to action
    cta_text = models.CharField(max_length=100, blank=True)
    cta_url = models.URLField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_vendor_reels'
        indexes = [
            models.Index(fields=['vendor_id', 'is_active', 'is_approved']),
            models.Index(fields=['view_count', 'is_active']),
            models.Index(fields=['created_at', 'is_active']),
        ]
        ordering = ['-view_count', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.vendor.name if self.vendor else 'No vendor'}"

    @property
    def completion_rate(self):
        """Calculate completion rate."""
        if self.view_count == 0:
            return 0
        return (self.completion_count / self.view_count) * 100

    @property
    def cta_tap_rate(self):
        """Calculate CTA tap rate."""
        if self.view_count == 0:
            return 0
        return (self.cta_tap_count / self.view_count) * 100


class Tag(models.Model):
    """
    Tag model for vendor categorization and browsing.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon_url = models.URLField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    
    # Category grouping
    category = models.CharField(max_length=30, db_index=True)
    sort_order = models.IntegerField(default=0)
    
    # Usage tracking
    vendor_count = models.IntegerField(default=0, db_index=True)
    search_count = models.IntegerField(default=0, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_tags'
        indexes = [
            models.Index(fields=['category', 'sort_order', 'is_active']),
            models.Index(fields=['vendor_count', 'is_active']),
            models.Index(fields=['search_count', 'is_active']),
        ]
        ordering = ['category', 'sort_order', 'name']

    def __str__(self):
        return self.name

    def update_vendor_count(self):
        """Update vendor count based on current vendors."""
        from django.db.models import Count
        
        # Count vendors with this tag
        count = Vendor.objects.filter(
            tags__contains=[self.name],
            is_active=True
        ).count()
        
        self.vendor_count = count
        self.save(update_fields=['vendor_count'])


class City(models.Model):
    """
    City model for location-based discovery.
    SQLite-compatible with simple coordinates.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    
    # Location (center point of city - simple coordinates)
    lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        help_text="Center latitude in WGS84"
    )
    lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        help_text="Center longitude in WGS84"
    )
    
    # Bounds for city area
    bounds_north = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_south = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_east = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_west = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Metadata
    country = models.CharField(max_length=50, default='Pakistan')
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    
    # Vendor counts
    vendor_count = models.IntegerField(default=0, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_cities'
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['vendor_count', 'is_active']),
        ]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def update_vendor_count(self):
        """Update vendor count based on vendors in city bounds."""
        # Count vendors within city bounds using simple coordinate comparison
        count = Vendor.objects.filter(
            lat__gte=self.bounds_south,
            lat__lte=self.bounds_north,
            lng__gte=self.bounds_west,
            lng__lte=self.bounds_east,
            is_active=True
        ).count()
        
        self.vendor_count = count
        self.save(update_fields=['vendor_count'])


class Area(models.Model):
    """
    Area model for city subdivisions.
    SQLite-compatible with simple coordinates.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='areas',
        db_index=True
    )
    
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, db_index=True)
    
    # Location (center point of area - simple coordinates)
    lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        help_text="Center latitude in WGS84"
    )
    lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        help_text="Center longitude in WGS84"
    )
    
    # Bounds for area
    bounds_north = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_south = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_east = models.DecimalField(max_digits=10, decimal_places=7)
    bounds_west = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    
    # Vendor counts
    vendor_count = models.IntegerField(default=0, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_areas'
        indexes = [
            models.Index(fields=['city', 'is_active', 'sort_order']),
            models.Index(fields=['vendor_count', 'is_active']),
        ]
        ordering = ['city', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name}, {self.city.name}"

    def update_vendor_count(self):
        """Update vendor count based on vendors in area bounds."""
        # Count vendors within area bounds using simple coordinate comparison
        count = Vendor.objects.filter(
            lat__gte=self.bounds_south,
            lat__lte=self.bounds_north,
            lng__gte=self.bounds_west,
            lng__lte=self.bounds_east,
            is_active=True
        ).count()
        
        self.vendor_count = count
        self.save(update_fields=['vendor_count'])


class UserPortalConfig(models.Model):
    """
    Configuration model for user portal settings.
    """
    
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_portal_config'
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.description}"

    @classmethod
    def get_config(cls, key, default=None):
        """Get configuration value."""
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_config(cls, key, value, description=""):
        """Set configuration value."""
        config, created = cls.objects.get_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description,
            }
        )
        
        if not created:
            config.value = value
            config.description = description
            config.save()
        
        return config
