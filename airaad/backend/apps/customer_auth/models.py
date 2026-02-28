from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
from core.fields import EncryptedCharField


class CustomerUser(models.Model):
    """
    Customer user profile for AirAds User Portal.
    One-to-one with Django User model for authentication.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]

    # Core relationship
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    
    # Basic profile
    display_name = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    phone_number = EncryptedCharField(max_length=20, blank=True, null=True)
    
    # Guest session tracking
    guest_token = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    
    # Behavioral data (privacy-first, on-device primary)
    behavioral_data = models.JSONField(default=dict, blank=True)
    
    # GDPR compliance
    data_export_requested_at = models.DateTimeField(null=True, blank=True)
    consent_records = models.JSONField(default=list, blank=True)  # Stores consent history
    
    # Social auth placeholder (Phase-2)
    social_auth_provider = models.CharField(max_length=50, blank=True, null=True)
    social_auth_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps and soft delete
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'customer_users'
        indexes = [
            models.Index(fields=['guest_token']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} ({self.display_name or 'No display name'})"

    def soft_delete(self):
        """Soft delete the customer user"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        # Clear PII but keep structure for analytics
        self.display_name = None
        self.phone_number = None
        self.behavioral_data = {}
        self.save()


class ConsentRecord(models.Model):
    """
    GDPR consent records for customer users.
    Stores proof of consent for data collection.
    """
    CONSENT_TYPES = [
        ('LOCATION', 'Location Services'),
        ('ANALYTICS', 'Analytics Tracking'),
        ('MARKETING', 'Marketing Communications'),
        ('TERMS', 'Terms of Service'),
        ('PRIVACY', 'Privacy Policy'),
        ('VOICE', 'Voice Data Processing'),
    ]

    # User identification (either authenticated user or guest)
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    guest_token = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Consent details
    consent_type = models.CharField(max_length=20, choices=CONSENT_TYPES, db_index=True)
    consented = models.BooleanField(db_index=True)
    consent_version = models.CharField(max_length=10, default='1.0')
    
    # Request metadata
    ip_address = models.CharField(max_length=128, db_index=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Timestamps
    consented_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Additional context
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'consent_records'
        indexes = [
            models.Index(fields=['user', 'consent_type', 'consented_at']),
            models.Index(fields=['guest_token', 'consent_type']),
            models.Index(fields=['consented_at', 'consent_type']),
        ]
        unique_together = [['user', 'consent_type', 'consented_at'], 
                          ['guest_token', 'consent_type', 'consented_at']]

    def __str__(self):
        identifier = self.user.user.email if self.user else f"Guest: {self.guest_token}"
        return f"{self.consent_type}: {self.consented} for {identifier}"


class GuestToken(models.Model):
    """
    Guest session tokens for anonymous users.
    Auto-expiring tokens for temporary sessions.
    """
    token = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Session metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Usage tracking
    api_calls_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'guest_tokens'
        indexes = [
            models.Index(fields=['expires_at', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Guest token {self.token} (expires: {self.expires_at})"

    @property
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at

    def extend_expiry(self, days=30):
        """Extend token expiry"""
        from datetime import timedelta
        self.expires_at = timezone.now() + timedelta(days=days)
        self.save()
