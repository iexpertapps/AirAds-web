import uuid
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction

from .models import CustomerUser, ConsentRecord, GuestToken
from core.security import hash_ip_address


User = get_user_model()


class CustomerAuthService:
    """
    Service layer for customer authentication operations.
    Handles registration, login, guest sessions, and JWT tokens.
    """

    JWT_AUDIENCE = "user-portal"
    TOKEN_ACCESS_TTL = timedelta(minutes=15)
    TOKEN_REFRESH_TTL = timedelta(days=7)
    GUEST_TOKEN_TTL = timedelta(days=30)

    @classmethod
    def create_guest_token(cls, ip_address=None, user_agent=None):
        """
        Create a new guest session token.
        Returns guest token UUID and expires_at timestamp.
        """
        guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + cls.GUEST_TOKEN_TTL,
            ip_address=hash_ip_address(ip_address) if ip_address else None,
            user_agent=user_agent or '',
        )
        
        return {
            'guest_token': str(guest_token.token),
            'expires_at': guest_token.expires_at.isoformat(),
            'expires_in_seconds': int(cls.GUEST_TOKEN_TTL.total_seconds()),
        }

    @classmethod
    def validate_guest_token(cls, guest_token_str):
        """
        Validate guest token and return GuestToken object.
        Returns None if invalid or expired.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            guest_token = GuestToken.objects.get(
                token=guest_uuid,
                is_active=True
            )
            
            if guest_token.is_expired:
                guest_token.is_active = False
                guest_token.save()
                return None
                
            # Update usage tracking
            guest_token.api_calls_count += 1
            guest_token.last_used_at = timezone.now()
            guest_token.save()
            
            return guest_token
            
        except (ValueError, GuestToken.DoesNotExist):
            return None

    @classmethod
    def register_customer(cls, email, password, display_name=None, phone_number=None, 
                        guest_token_str=None, ip_address=None, user_agent=None):
        """
        Register a new customer account.
        Migrates guest preferences if guest_token provided.
        """
        with transaction.atomic():
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                raise ValueError("User with this email already exists")
            
            # Create Django User
            django_user = User.objects.create_user(
                email=email,
                username=email,  # Use email as username
                password=password,
                is_active=False  # Require email verification
            )
            
            # Create CustomerUser profile
            customer_user = CustomerUser.objects.create(
                user=django_user,
                display_name=display_name,
                phone_number=phone_number,
            )
            
            # Handle guest token migration
            if guest_token_str:
                cls._migrate_guest_preferences(guest_token_str, customer_user)
            
            # Create consent records
            cls._create_registration_consents(customer_user, ip_address, user_agent)
            
            # Generate JWT tokens (inactive until email verification)
            tokens = cls._generate_jwt_tokens(django_user)
            
            return {
                'customer_user': customer_user,
                'tokens': tokens,
                'requires_email_verification': True,
            }

    @classmethod
    def login_customer(cls, email, password, guest_token_str=None, ip_address=None, user_agent=None):
        """
        Authenticate and login customer.
        Migrates guest preferences if guest_token provided.
        """
        # Authenticate user
        user = authenticate(username=email, password=password)
        if not user:
            raise ValueError("Invalid credentials")
        
        if not user.is_active:
            raise ValueError("Account is disabled")
        
        # Get or create CustomerUser profile
        customer_user, created = CustomerUser.objects.get_or_create(
            user=user,
            defaults={
                'display_name': user.email.split('@')[0],
            }
        )
        
        # Handle guest token migration
        if guest_token_str:
            cls._migrate_guest_preferences(guest_token_str, customer_user)
        
        # Update last known location if provided
        # (This would be updated via separate API call)
        
        # Generate JWT tokens
        tokens = cls._generate_jwt_tokens(user)
        
        return {
            'customer_user': customer_user,
            'tokens': tokens,
            'is_new_user': created,
        }

    @classmethod
    def verify_email(cls, token):
        """
        Verify email using verification token.
        """
        try:
            # Decode token (this would be generated during registration)
            # For now, using a simple approach - in production, use proper email verification service
            payload = AccessToken(token)
            user_id = payload['user_id']
            
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            
            return True
            
        except (TokenError, User.DoesNotExist):
            return False

    @classmethod
    def refresh_token(cls, refresh_token_str):
        """
        Refresh JWT access token.
        """
        try:
            refresh_token = RefreshToken(refresh_token_str)
            refresh_token.check_exp()
            
            # Verify audience
            if refresh_token['aud'] != cls.JWT_AUDIENCE:
                raise TokenError("Invalid token audience")
            
            # Generate new access token
            access_token = refresh_token.access_token
            
            return {
                'access_token': str(access_token),
                'access_token_expires_in': int(cls.TOKEN_ACCESS_TTL.total_seconds()),
            }
            
        except TokenError:
            raise ValueError("Invalid or expired refresh token")

    @classmethod
    def logout_customer(cls, refresh_token_str):
        """
        Logout customer by blacklisting refresh token.
        """
        try:
            refresh_token = RefreshToken(refresh_token_str)
            refresh_token.blacklist()
            return True
        except TokenError:
            return False

    @classmethod
    def request_password_reset(cls, email):
        """
        Request password reset for customer.
        Returns reset token (in production, send via email).
        """
        try:
            user = User.objects.get(email=email)
            customer_user = user.customer_profile
            
            # Generate reset token
            reset_token = cls._generate_password_reset_token(user)
            
            # Store reset token in cache with expiry
            cache.set(
                f'password_reset:{reset_token}',
                user.id,
                timeout=3600  # 1 hour
            )
            
            return {
                'reset_token': reset_token,
                'expires_in': 3600,
            }
            
        except User.DoesNotExist:
            # Don't reveal if email exists
            return None

    @classmethod
    def confirm_password_reset(cls, token, new_password):
        """
        Confirm password reset with token.
        """
        user_id = cache.get(f'password_reset:{token}')
        if not user_id:
            raise ValueError("Invalid or expired reset token")
        
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            
            # Clear the token
            cache.delete(f'password_reset:{token}')
            
            return True
            
        except User.DoesNotExist:
            raise ValueError("User not found")

    @classmethod
    def export_user_data(cls, customer_user):
        """
        Export all user data for GDPR compliance.
        Sources preferences from UserPreference model.
        """
        from apps.user_preferences.services import (
            UserPreferenceService, SearchHistoryService,
            InteractionService, ReelViewService
        )
        
        # Get preferences from UserPreference model
        prefs = UserPreferenceService.get_preferences(customer_user)
        
        # Collect all user data
        data = {
            'account': {
                'email': customer_user.user.email,
                'display_name': customer_user.display_name,
                'created_at': customer_user.created_at.isoformat(),
                'last_login': customer_user.user.last_login.isoformat() if customer_user.user.last_login else None,
            },
            'preferences': prefs or {},
            'consent_records': [
                {
                    'consent_type': record.consent_type,
                    'consented': record.consented,
                    'consent_version': record.consent_version,
                    'consented_at': record.consented_at.isoformat(),
                }
                for record in ConsentRecord.objects.filter(user=customer_user)
            ],
            'search_history': SearchHistoryService.get_search_history(customer_user, limit=1000),
            'interactions': InteractionService.get_recent_interactions(customer_user, limit=1000),
            'reel_views': ReelViewService.get_view_stats(customer_user, days=365),
        }
        
        # Mark export request
        customer_user.data_export_requested_at = timezone.now()
        customer_user.save()
        
        return data

    @classmethod
    def delete_user_account(cls, customer_user, confirmation_code):
        """
        Delete user account with confirmation code.
        Implements GDPR right to erasure.
        """
        from django.core.cache import cache
        
        # Verify confirmation code from cache (set by request_account_deletion)
        cache_key = f'deletion_code:{customer_user.id}'
        expected_code = cache.get(cache_key)
        if not expected_code or confirmation_code != expected_code:
            raise ValueError("Invalid or expired confirmation code")
        cache.delete(cache_key)
        
        with transaction.atomic():
            # Soft delete customer profile
            customer_user.soft_delete()
            
            # Deactivate Django user
            customer_user.user.is_active = False
            customer_user.user.save()
            
            # Schedule hard deletion after 30 days (via Celery task)
            from .tasks import schedule_user_data_purge
            schedule_user_data_purge.delay(customer_user.id)
            
            return True

    @classmethod
    def record_consent(cls, user_or_guest, consent_type, consented, 
                      consent_version='1.0', ip_address=None, user_agent=None, context=None):
        """
        Record consent for GDPR compliance.
        """
        consent_data = {
            'consent_type': consent_type,
            'consented': consented,
            'consent_version': consent_version,
            'ip_address': hash_ip_address(ip_address) if ip_address else '',
            'user_agent': user_agent or '',
            'context': context or {},
        }
        
        if isinstance(user_or_guest, CustomerUser):
            consent_data['user'] = user_or_guest
        else:
            consent_data['guest_token'] = user_or_guest
        
        ConsentRecord.objects.create(**consent_data)

    # Private helper methods

    @classmethod
    def _generate_jwt_tokens(cls, user):
        """
        Generate JWT tokens with user-portal audience.
        """
        refresh_token = RefreshToken.for_user(user)
        access_token = refresh_token.access_token
        
        # Set audience claim
        refresh_token['aud'] = cls.JWT_AUDIENCE
        access_token['aud'] = cls.JWT_AUDIENCE
        
        return {
            'access_token': str(access_token),
            'refresh_token': str(refresh_token),
            'access_token_expires_in': int(cls.TOKEN_ACCESS_TTL.total_seconds()),
            'refresh_token_expires_in': int(cls.TOKEN_REFRESH_TTL.total_seconds()),
        }

    @classmethod
    def _migrate_guest_preferences(cls, guest_token_str, customer_user):
        """
        Migrate guest preferences to user account.
        Delegates to MigrationService for full data migration, then deactivates the guest token.
        """
        try:
            guest_uuid = uuid.UUID(guest_token_str)
            guest_token = GuestToken.objects.get(token=guest_uuid)
            
            # Delegate full migration to user_preferences MigrationService
            from apps.user_preferences.services import MigrationService
            MigrationService.migrate_all_guest_data(str(guest_uuid), customer_user)
            
            # Deactivate the guest token after migration
            guest_token.is_active = False
            guest_token.save()
            
        except (ValueError, GuestToken.DoesNotExist):
            pass  # Invalid guest token, ignore

    @classmethod
    def _create_registration_consents(cls, customer_user, ip_address, user_agent):
        """
        Create default consent records for new registration.
        """
        default_consents = [
            ('TERMS', True),      # Required for registration
            ('ANALYTICS', True),  # Default opt-in
        ]
        
        for consent_type, consented in default_consents:
            cls.record_consent(
                customer_user,
                consent_type,
                consented,
                ip_address=ip_address,
                user_agent=user_agent,
                context={'source': 'registration'}
            )

    @classmethod
    def _generate_password_reset_token(cls, user):
        """
        Generate password reset token.
        """
        import secrets
        return secrets.token_urlsafe(32)

    @classmethod
    def _generate_deletion_code(cls, customer_user):
        """
        Generate and cache account deletion confirmation code.
        Code is valid for 1 hour.
        """
        import secrets
        from django.core.cache import cache
        
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        cache_key = f'deletion_code:{customer_user.id}'
        cache.set(cache_key, code, timeout=3600)  # 1 hour TTL
        return code
