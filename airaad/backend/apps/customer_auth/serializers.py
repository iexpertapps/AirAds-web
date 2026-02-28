from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import re

from .models import CustomerUser, ConsentRecord, GuestToken

User = get_user_model()


class CustomerRegistrationSerializer(serializers.Serializer):
    """
    Serializer for customer registration.
    """
    email = serializers.EmailField(
        required=True,
        max_length=254,
        error_messages={
            'required': 'Email address is required',
            'invalid': 'Please enter a valid email address',
        }
    )
    password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        error_messages={
            'required': 'Password is required',
            'min_length': 'Password must be at least 8 characters long',
        }
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            'required': 'Password confirmation is required',
        }
    )
    display_name = serializers.CharField(
        required=False,
        max_length=50,
        allow_blank=True,
        error_messages={
            'max_length': 'Display name cannot exceed 50 characters',
        }
    )
    phone_number = serializers.CharField(
        required=False,
        max_length=20,
        allow_blank=True,
        error_messages={
            'max_length': 'Phone number cannot exceed 20 characters',
        }
    )
    guest_token = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            'invalid': 'Invalid guest token format',
        }
    )
    
    def validate_email(self, value):
        """Validate email format and uniqueness."""
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Please enter a valid email address")
        
        # Check if email already exists
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists")
        
        return value.lower()
    
    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character")
        
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not re.match(r'^[\d\s\-\+\(\)]+$', value):
            raise serializers.ValidationError("Phone number can only contain digits, spaces, and basic symbols")
        
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        
        return attrs


class CustomerLoginSerializer(serializers.Serializer):
    """
    Serializer for customer login.
    """
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email address is required',
            'invalid': 'Please enter a valid email address',
        }
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            'required': 'Password is required',
        }
    )
    guest_token = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            'invalid': 'Invalid guest token format',
        }
    )
    
    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email address is required',
            'invalid': 'Please enter a valid email address',
        }
    )
    
    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """
    token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Reset token is required',
        }
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        write_only=True,
        error_messages={
            'required': 'New password is required',
            'min_length': 'Password must be at least 8 characters long',
        }
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            'required': 'Password confirmation is required',
        }
    )
    
    def validate_new_password(self, value):
        """Validate new password strength."""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character")
        
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        
        return attrs


class CustomerProfileSerializer(serializers.Serializer):
    """
    Serializer for customer profile updates.
    """
    display_name = serializers.CharField(
        required=False,
        max_length=50,
        allow_blank=True,
        error_messages={
            'max_length': 'Display name cannot exceed 50 characters',
        }
    )
    phone_number = serializers.CharField(
        required=False,
        max_length=20,
        allow_blank=True,
        error_messages={
            'max_length': 'Phone number cannot exceed 20 characters',
        }
    )
    avatar_url = serializers.URLField(
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'Please enter a valid URL',
        }
    )
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not re.match(r'^[\d\s\-\+\(\)]+$', value):
            raise serializers.ValidationError("Phone number can only contain digits, spaces, and basic symbols")
        
        return value


class ConsentRecordSerializer(serializers.Serializer):
    """
    Serializer for consent records.
    """
    consent_type = serializers.ChoiceField(
        required=True,
        choices=[
            ('LOCATION', 'Location Services'),
            ('ANALYTICS', 'Analytics Tracking'),
            ('MARKETING', 'Marketing Communications'),
            ('TERMS', 'Terms of Service'),
            ('PRIVACY', 'Privacy Policy'),
            ('VOICE', 'Voice Data Processing'),
        ],
        error_messages={
            'required': 'Consent type is required',
            'invalid_choice': 'Invalid consent type',
        }
    )
    consented = serializers.BooleanField(
        required=True,
        error_messages={
            'required': 'Consent status is required',
        }
    )
    consent_version = serializers.CharField(
        required=False,
        max_length=10,
        default='1.0',
        error_messages={
            'max_length': 'Consent version cannot exceed 10 characters',
        }
    )
    context = serializers.DictField(
        required=False,
        allow_empty=True,
        child=serializers.CharField(),
        error_messages={
            'invalid': 'Context must be a dictionary',
        }
    )


class CustomerUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerUser model.
    """
    email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    
    class Meta:
        model = CustomerUser
        fields = [
            'id',
            'email',
            'display_name',
            'avatar_url',
            'phone_number',
            'created_at',
            'updated_at',
            'is_active',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'is_active',
            'date_joined',
            'last_login',
        ]
    
    def to_representation(self, instance):
        """Custom representation for CustomerUser."""
        if hasattr(instance, 'customer_profile'):
            # This is a User object, get CustomerUser
            instance = instance.customer_profile
        
        return super().to_representation(instance)


class GuestTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for GuestToken model.
    """
    time_remaining_seconds = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = GuestToken
        fields = [
            'token',
            'created_at',
            'expires_at',
            'is_active',
            'api_calls_count',
            'last_used_at',
            'time_remaining_seconds',
            'is_expired',
        ]
        read_only_fields = [
            'token',
            'created_at',
            'expires_at',
            'api_calls_count',
            'last_used_at',
        ]
    
    def get_time_remaining_seconds(self, obj):
        """Calculate remaining time in seconds."""
        from django.utils import timezone
        if obj.is_expired:
            return 0
        return int((obj.expires_at - timezone.now()).total_seconds())
    
    def get_is_expired(self, obj):
        """Check if token is expired."""
        return obj.is_expired
