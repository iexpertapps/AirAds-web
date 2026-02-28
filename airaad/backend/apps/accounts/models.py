"""
AirAd Backend — AdminUser Model

Custom user model using AbstractBaseUser with 7 RBAC roles.
UUID primary key with default=uuid.uuid4 (callable — never uuid.uuid4()).
All auth events are logged to AuditLog from services.py, never via signals.
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class AdminRole(models.TextChoices):
    """Eleven RBAC roles for the AirAd admin portal.

    Phase-A data-collection roles (original 7) plus 4 governance roles
    added per spec §2.1 (Admin Operations & Governance Document).
    RolePermission.for_roles() is the ONLY mechanism to enforce them (R3).
    """

    # Phase-A data-collection roles
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    CITY_MANAGER = "CITY_MANAGER", "City Manager"
    DATA_ENTRY = "DATA_ENTRY", "Data Entry"
    QA_REVIEWER = "QA_REVIEWER", "QA Reviewer"
    FIELD_AGENT = "FIELD_AGENT", "Field Agent"
    ANALYST = "ANALYST", "Analyst"
    SUPPORT = "SUPPORT", "Support"

    # Governance roles — spec §2.1 (Admin Operations & Governance Document)
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER", "Operations Manager"
    CONTENT_MODERATOR = "CONTENT_MODERATOR", "Content Moderator"
    DATA_QUALITY_ANALYST = "DATA_QUALITY_ANALYST", "Data Quality Analyst"
    ANALYTICS_OBSERVER = "ANALYTICS_OBSERVER", "Analytics Observer"


class AdminUserManager(BaseUserManager["AdminUser"]):
    """Custom manager for AdminUser.

    Provides create_user() and create_superuser() with full type hints.
    """

    def create_user(
        self,
        email: str,
        password: str | None = None,
        role: str = AdminRole.DATA_ENTRY,
        **extra_fields: object,
    ) -> "AdminUser":
        """Create and save a regular AdminUser.

        Args:
            email: Unique email address — used as USERNAME_FIELD.
            password: Raw password (will be hashed). May be None for
                unusable-password accounts.
            role: AdminRole value. Defaults to DATA_ENTRY.
            **extra_fields: Additional model field values.

        Returns:
            Saved AdminUser instance.

        Raises:
            ValueError: If email is empty.
        """
        if not email:
            raise ValueError("AdminUser must have an email address")

        email = self.normalize_email(email)
        user: AdminUser = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "AdminUser":
        """Create and save a SuperAdmin user.

        Args:
            email: Unique email address.
            password: Raw password.
            **extra_fields: Additional model field values.

        Returns:
            Saved AdminUser instance with SUPER_ADMIN role.

        Raises:
            ValueError: If email is empty.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(
            email=email,
            password=password,
            role=AdminRole.SUPER_ADMIN,
            **extra_fields,
        )


class AdminUser(AbstractBaseUser, PermissionsMixin):
    """Custom admin user model for the AirAd internal portal.

    Uses email as the login identifier. Supports 7 RBAC roles via
    AdminRole TextChoices. Account lockout is enforced in services.py.

    Attributes:
        id: UUID primary key — default=uuid.uuid4 (callable, not evaluated once).
        email: Unique email address used as USERNAME_FIELD.
        full_name: Display name.
        role: One of 7 AdminRole values.
        is_active: Whether the account is active.
        is_staff: Django admin access flag.
        failed_login_count: Incremented on each failed login attempt.
        locked_until: Datetime until which the account is locked (nullable).
        last_login_ip: IP address of the most recent successful login.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,  # callable — NOT uuid.uuid4() (mutable default bug)
        editable=False,
    )
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=25,
        choices=AdminRole.choices,
        default=AdminRole.DATA_ENTRY,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Lockout tracking
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fix reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='adminuser_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='adminuser_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    # Password management
    must_change_password = models.BooleanField(
        default=False,
        help_text="Set True on creation via temp password. Cleared on first successful login.",
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AdminUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    def is_locked(self) -> bool:
        """Check whether this account is currently locked out.

        Returns:
            True if locked_until is set and in the future, False otherwise.
        """
        if self.locked_until is None:
            return False
        return timezone.now() < self.locked_until


class UserType(models.TextChoices):
    """User type discriminator for JWT payload (Phase B §3.2).

    JWT claims include user_type so the frontend/mobile can branch UI logic.
    """

    ADMIN = "ADMIN", "Admin"
    CUSTOMER = "CUSTOMER", "Customer"
    VENDOR = "VENDOR", "Vendor"


class CustomerUser(models.Model):
    """Public-facing customer/vendor user for Phase B (§3.2).

    Authenticates via OTP (SMS or WhatsApp). Phone is the unique identifier.
    Phone stored encrypted via AES-256-GCM in phone_encrypted (BinaryField).
    phone_hash stores a SHA-256 hash of the phone for unique lookups without
    decryption.

    The same model is used for both CUSTOMER and VENDOR user types —
    a customer becomes a vendor by claiming a Vendor listing.

    Attributes:
        id: UUID primary key.
        phone_hash: SHA-256 hash of phone number — indexed, unique, used for lookups.
        phone_encrypted: AES-256-GCM encrypted phone number (BinaryField).
        full_name: Display name (optional at first, required for vendor).
        email: Optional email (required for vendor).
        user_type: CUSTOMER or VENDOR.
        device_token: Push notification token (FCM/APNS).
        is_active: Whether the account is active.
        is_phone_verified: Set True after first successful OTP verification.
        last_login_at: Timestamp of most recent successful login.
        last_login_ip: IP address of most recent login.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    phone_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of phone number for unique lookups without decryption.",
    )
    phone_encrypted = models.BinaryField(
        help_text="AES-256-GCM encrypted phone number. Decrypt in services.py only.",
    )

    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True, db_index=True)

    user_type = models.CharField(
        max_length=10,
        choices=[
            (UserType.CUSTOMER, "Customer"),
            (UserType.VENDOR, "Vendor"),
        ],
        default=UserType.CUSTOMER,
        db_index=True,
    )

    device_token = models.CharField(
        max_length=500,
        blank=True,
        help_text="FCM/APNS push notification token.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_phone_verified = models.BooleanField(
        default=False,
        help_text="Set True after first successful OTP verification.",
    )

    # Customer preferences (§B-1)
    preferred_radius = models.PositiveIntegerField(
        default=500,
        help_text="Default search radius in meters for nearby discovery.",
    )
    preferred_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of preferred category tag slugs for personalised results.",
    )
    last_known_lat = models.FloatField(
        null=True,
        blank=True,
        help_text="Last known latitude — updated on each discovery request.",
    )
    last_known_lng = models.FloatField(
        null=True,
        blank=True,
        help_text="Last known longitude — updated on each discovery request.",
    )

    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer User"
        verbose_name_plural = "Customer Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_type", "is_active"]),
        ]

    def __str__(self) -> str:
        label = self.full_name or self.phone_hash[:8]
        return f"{label} ({self.user_type})"

    @property
    def is_authenticated(self) -> bool:
        """Required by DRF IsAuthenticated permission."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Required by DRF for anonymous user checks."""
        return False


class OTPRequest(models.Model):
    """Tracks OTP send/verify attempts for rate limiting and audit (Phase B §3.2).

    OTPs are never stored in plaintext — only a SHA-256 hash.
    Expires after 5 minutes. Max 3 verify attempts per OTP.

    Attributes:
        id: UUID primary key.
        phone_hash: SHA-256 of phone number (matches CustomerUser.phone_hash).
        otp_hash: SHA-256 hash of the OTP code — never plaintext.
        purpose: What the OTP is for (LOGIN, CLAIM_VERIFY, EMAIL_VERIFY).
        attempts: Number of verify attempts (max 3).
        is_used: Whether this OTP has been successfully verified.
        expires_at: When the OTP expires (5 minutes from creation).
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    phone_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of phone number.",
    )
    otp_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the OTP code — never store plaintext.",
    )

    purpose = models.CharField(
        max_length=20,
        choices=[
            ("LOGIN", "Login"),
            ("CLAIM_VERIFY", "Claim Verify"),
            ("EMAIL_VERIFY", "Email Verify"),
        ],
        default="LOGIN",
    )

    attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of verify attempts. Max 3 before OTP is invalidated.",
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(
        help_text="OTP expires 5 minutes after creation.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OTP Request"
        verbose_name_plural = "OTP Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_hash", "is_used", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"OTP {self.phone_hash[:8]}... ({self.purpose})"

    @property
    def is_expired(self) -> bool:
        """Check if this OTP has expired.

        Returns:
            True if current time is past expires_at.
        """
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if this OTP can still be used.

        Returns:
            True if not used, not expired, and attempts < 3.
        """
        return not self.is_used and not self.is_expired and self.attempts < 3
