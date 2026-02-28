from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

from apps.customer_auth.models import CustomerUser

User = get_user_model()


class UserPreference(models.Model):
    """
    User preferences for customer users and guest sessions.
    Stores UI preferences, search settings, and notification choices.
    """
    
    # User identification (either authenticated user or guest)
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # UI preferences
    default_view = models.CharField(
        max_length=10,
        choices=[
            ('AR', 'AR View'),
            ('MAP', 'Map View'),
            ('LIST', 'List View'),
        ],
        default='AR'
    )
    search_radius_m = models.IntegerField(default=500, db_index=True)
    show_open_now_only = models.BooleanField(default=False)
    
    # Category and price preferences
    preferred_category_slugs = models.JSONField(default=list, blank=True)
    price_range = models.CharField(
        max_length=10,
        choices=[
            ('BUDGET', 'Budget'),
            ('MID', 'Mid Range'),
            ('PREMIUM', 'Premium'),
        ],
        default='MID'
    )
    
    # Theme preference
    theme = models.CharField(
        max_length=10,
        choices=[
            ('DARK', 'Dark'),
            ('LIGHT', 'Light'),
            ('SYSTEM', 'System'),
        ],
        default='DARK'
    )
    
    # Notification preferences
    notifications_nearby_deals = models.BooleanField(default=True)
    notifications_flash_deals = models.BooleanField(default=True)
    notifications_new_vendors = models.BooleanField(default=True)
    notifications_all_off = models.BooleanField(default=False)
    
    # Location preferences
    auto_location_enabled = models.BooleanField(default=True)
    manual_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    manual_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    manual_location_name = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_preferences'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['guest_token']),
            models.Index(fields=['default_view']),
            models.Index(fields=['search_radius_m']),
            models.Index(fields=['updated_at']),
        ]
        unique_together = [['user'], ['guest_token']]  # One preference record per user/guest

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"Preferences for {identifier}"

    @classmethod
    def get_for_user(cls, customer_user):
        """Get or create preferences for authenticated user."""
        preference, created = cls.objects.get_or_create(
            user=customer_user,
            defaults={
                'default_view': 'AR',
                'search_radius_m': 500,
                'theme': 'DARK',
            }
        )
        return preference

    @classmethod
    def get_for_guest(cls, guest_token):
        """Get or create preferences for guest."""
        try:
            # Handle if guest_token is already a UUID object
            if isinstance(guest_token, uuid.UUID):
                guest_uuid = guest_token
            else:
                guest_uuid = uuid.UUID(guest_token)
            
            preference, created = cls.objects.get_or_create(
                guest_token=guest_uuid,
                defaults={
                    'default_view': 'AR',
                    'search_radius_m': 500,
                    'theme': 'DARK',
                }
            )
            return preference
        except (ValueError, TypeError):
            return None


class UserSearchHistory(models.Model):
    """
    Search history for users and guests.
    Tracks search queries and results for analytics and personalization.
    """
    
    # User identification
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Search details
    query_text = models.CharField(max_length=200, db_index=True)
    query_type = models.CharField(
        max_length=10,
        choices=[
            ('TEXT', 'Text Search'),
            ('VOICE', 'Voice Search'),
            ('TAG', 'Tag Browse'),
        ],
        db_index=True
    )
    
    # Extracted intent (from NLP processing)
    extracted_category = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    extracted_intent = models.CharField(max_length=50, null=True, blank=True)
    extracted_price_range = models.CharField(max_length=10, null=True, blank=True)
    
    # Search context
    search_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    search_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    search_radius_m = models.IntegerField(null=True, blank=True)
    
    # Results
    result_count = models.IntegerField(default=0)
    navigated_to_vendor_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Timestamps
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'user_search_history'
        indexes = [
            models.Index(fields=['user', 'searched_at']),
            models.Index(fields=['guest_token', 'searched_at']),
            models.Index(fields=['query_type', 'searched_at']),
            models.Index(fields=['extracted_category', 'searched_at']),
            models.Index(fields=['navigated_to_vendor_id']),
        ]
        ordering = ['-searched_at']

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"Search: '{self.query_text}' by {identifier}"

    @classmethod
    def record_search(cls, user_or_guest, query_text, query_type, **kwargs):
        """Record a search query."""
        search_data = {
            'query_text': query_text,
            'query_type': query_type,
        }
        
        # Add optional fields
        optional_fields = [
            'extracted_category', 'extracted_intent', 'extracted_price_range',
            'search_lat', 'search_lng', 'search_radius_m', 'result_count',
            'navigated_to_vendor_id'
        ]
        for field in optional_fields:
            if field in kwargs:
                search_data[field] = kwargs[field]
        
        # Add user identification
        if hasattr(user_or_guest, 'customer_profile') or isinstance(user_or_guest, CustomerUser):
            # Handle authenticated user
            if hasattr(user_or_guest, 'customer_profile'):
                search_data['user'] = user_or_guest.customer_profile
            else:
                search_data['user'] = user_or_guest
        else:
            # Handle guest token
            if hasattr(user_or_guest, 'token'):
                search_data['guest_token'] = user_or_guest.token
            else:
                search_data['guest_token'] = user_or_guest
        
        return cls.objects.create(**search_data)


class UserVendorInteraction(models.Model):
    """
    Track user interactions with vendors.
    Used for analytics and ranking algorithm improvements.
    """
    
    INTERACTION_TYPES = [
        ('VIEW', 'Profile View'),
        ('TAP', 'AR Marker Tap'),
        ('NAVIGATION', 'Navigation Click'),
        ('CALL', 'Phone Call'),
        ('REEL_VIEW', 'Reel View'),
        ('PROMOTION_TAP', 'Promotion Tap'),
        ('ARRIVAL', 'Physical Arrival'),
        ('SHARE', 'Share Vendor'),
        ('FAVORITE', 'Add to Favorites'),
    ]
    
    # User identification
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Vendor and interaction details
    vendor_id = models.UUIDField(db_index=True)  # Not FK for performance
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, db_index=True)
    session_id = models.UUIDField(db_index=True)  # Groups interactions in one session
    
    # Location context
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Additional context
    metadata = models.JSONField(default=dict, blank=True)  # Store additional interaction data
    
    # Timestamps
    interacted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'user_vendor_interactions'
        indexes = [
            models.Index(fields=['vendor_id', 'interaction_type', 'interacted_at']),
            models.Index(fields=['user', 'interacted_at']),
            models.Index(fields=['guest_token', 'interacted_at']),
            models.Index(fields=['session_id', 'interacted_at']),
            models.Index(fields=['interacted_at']),
        ]
        ordering = ['-interacted_at']

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"{self.interaction_type}: Vendor {self.vendor_id} by {identifier}"

    @classmethod
    def record_interaction(cls, user_or_guest, vendor_id, interaction_type, 
                          session_id=None, lat=None, lng=None, **metadata):
        """Record a vendor interaction."""
        interaction_data = {
            'vendor_id': vendor_id,
            'interaction_type': interaction_type,
            'session_id': session_id or uuid.uuid4(),
            'metadata': metadata or {},
        }
        
        # Add location if provided
        if lat is not None:
            interaction_data['lat'] = lat
        if lng is not None:
            interaction_data['lng'] = lng
        
        # Add user identification
        if hasattr(user_or_guest, 'customer_profile') or isinstance(user_or_guest, CustomerUser):
            # Handle authenticated user
            if hasattr(user_or_guest, 'customer_profile'):
                interaction_data['user'] = user_or_guest.customer_profile
            else:
                interaction_data['user'] = user_or_guest
        else:
            # Handle guest token
            if hasattr(user_or_guest, 'token'):
                interaction_data['guest_token'] = user_or_guest.token
            else:
                interaction_data['guest_token'] = user_or_guest
        
        return cls.objects.create(**interaction_data)


class FlashDealAlert(models.Model):
    """
    Track flash deal alerts to prevent duplicate notifications.
    """
    
    # User identification
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Deal details
    discount_id = models.UUIDField(db_index=True)
    vendor_id = models.UUIDField(db_index=True)
    
    # Alert tracking
    alerted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    dismissed = models.BooleanField(default=False, db_index=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Interaction tracking
    tapped = models.BooleanField(default=False)
    tapped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'flash_deal_alerts'
        indexes = [
            models.Index(fields=['user', 'discount_id']),
            models.Index(fields=['guest_token', 'discount_id']),
            models.Index(fields=['alerted_at']),
            models.Index(fields=['dismissed', 'alerted_at']),
        ]
        unique_together = [['user', 'discount_id'], ['guest_token', 'discount_id']]

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"Flash alert: Discount {self.discount_id} for {identifier}"

    @classmethod
    def should_alert(cls, user_or_guest, discount_id, vendor_id):
        """Check if user should be alerted about this flash deal."""
        # Check if alert already exists
        alert_exists = cls.objects.filter(
            discount_id=discount_id,
            **(
                {'user': user_or_guest.customer_profile} 
                if hasattr(user_or_guest, 'customer_profile') 
                else {'guest_token': user_or_guest}
            )
        ).exists()
        
        return not alert_exists

    @classmethod
    def create_alert(cls, user_or_guest, discount_id, vendor_id):
        """Create a flash deal alert."""
        alert_data = {
            'discount_id': discount_id,
            'vendor_id': vendor_id,
        }
        
        # Add user identification
        if hasattr(user_or_guest, 'customer_profile'):
            alert_data['user'] = user_or_guest.customer_profile
        else:
            alert_data['guest_token'] = user_or_guest
        
        return cls.objects.create(**alert_data)


class NearbyReelView(models.Model):
    """
    Track reel views from nearby vendors feed.
    """
    
    # User identification
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Reel details
    reel_id = models.UUIDField(db_index=True)
    vendor_id = models.UUIDField(db_index=True)
    
    # Viewing metrics
    watched_seconds = models.IntegerField(default=0)
    completed = models.BooleanField(default=False, db_index=True)
    cta_tapped = models.BooleanField(default=False, db_index=True)
    
    # Location context
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Timestamps
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'nearby_reel_views'
        indexes = [
            models.Index(fields=['reel_id', 'viewed_at']),
            models.Index(fields=['vendor_id', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),
            models.Index(fields=['guest_token', 'viewed_at']),
            models.Index(fields=['completed', 'viewed_at']),
            models.Index(fields=['cta_tapped', 'viewed_at']),
        ]
        ordering = ['-viewed_at']

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"Reel view: {self.reel_id} ({self.watched_seconds}s) by {identifier}"

    @classmethod
    def record_view(cls, user_or_guest, reel_id, vendor_id, **kwargs):
        """Record a reel view."""
        view_data = {
            'reel_id': reel_id,
            'vendor_id': vendor_id,
        }
        
        # Add optional fields
        optional_fields = ['watched_seconds', 'completed', 'cta_tapped', 'lat', 'lng']
        for field in optional_fields:
            if field in kwargs:
                view_data[field] = kwargs[field]
        
        # Add user identification
        if hasattr(user_or_guest, 'customer_profile'):
            view_data['user'] = user_or_guest.customer_profile
        else:
            view_data['guest_token'] = user_or_guest
        
        return cls.objects.create(**view_data)
