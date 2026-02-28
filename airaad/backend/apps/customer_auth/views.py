from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from .models import CustomerUser, ConsentRecord, GuestToken
from .services import CustomerAuthService
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerLoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ConsentRecordSerializer,
)
from common.responses import success_response, error_response
from common.permissions import IsCustomerUser, IsGuestOrAuthenticated

User = get_user_model()


class GuestTokenView(APIView):
    """
    Create or validate guest session tokens.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Create new guest token"""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            guest_data = CustomerAuthService.create_guest_token(
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return success_response(
                data=guest_data,
                message="Guest token created successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                message="Failed to create guest token",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request):
        """Validate guest token"""
        guest_token = request.headers.get('X-Guest-Token')
        if not guest_token:
            return error_response(
                message="Guest token required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        guest_obj = CustomerAuthService.validate_guest_token(guest_token)
        if not guest_obj:
            return error_response(
                message="Invalid or expired guest token",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        return success_response(
            data={
                'valid': True,
                'expires_at': guest_obj.expires_at.isoformat(),
                'api_calls_count': guest_obj.api_calls_count,
            },
            message="Guest token is valid"
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class CustomerRegistrationView(APIView):
    """
    Register new customer account.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Register new customer"""
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            result = CustomerAuthService.register_customer(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                display_name=serializer.validated_data.get('display_name'),
                phone_number=serializer.validated_data.get('phone_number'),
                guest_token_str=serializer.validated_data.get('guest_token'),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            response_data = {
                'user': {
                    'id': str(result['customer_user'].id),
                    'email': result['customer_user'].user.email,
                    'display_name': result['customer_user'].display_name,
                },
                'tokens': result['tokens'],
                'requires_email_verification': result['requires_email_verification'],
            }
            
            return success_response(
                data=response_data,
                message="Registration successful. Please check your email for verification.",
                status_code=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="Registration failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class EmailVerificationView(APIView):
    """
    Verify customer email address.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Verify email with token"""
        token = request.data.get('token')
        if not token:
            return error_response(
                message="Verification token required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            success = CustomerAuthService.verify_email(token)
            if not success:
                return error_response(
                    message="Invalid or expired verification token",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            return success_response(
                message="Email verified successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Email verification failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerLoginView(APIView):
    """
    Login customer with email and password.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Login customer"""
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            result = CustomerAuthService.login_customer(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                guest_token_str=serializer.validated_data.get('guest_token'),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Fetch preferences from UserPreference model
            from apps.user_preferences.services import UserPreferenceService
            prefs = UserPreferenceService.get_preferences(result['customer_user'])
            
            response_data = {
                'user': {
                    'id': str(result['customer_user'].id),
                    'email': result['customer_user'].user.email,
                    'display_name': result['customer_user'].display_name,
                    'avatar_url': result['customer_user'].avatar_url,
                    'preferred_radius_m': prefs.get('search_radius_m', 500) if prefs else 500,
                    'preferred_categories': prefs.get('preferred_category_slugs', []) if prefs else [],
                },
                'tokens': result['tokens'],
                'is_new_user': result['is_new_user'],
            }
            
            return success_response(
                data=response_data,
                message="Login successful",
                status_code=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return error_response(
                message="Login failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class TokenRefreshView(BaseTokenRefreshView):
    """
    Refresh JWT access token.
    """
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            # Add custom metadata
            response.data['expires_in'] = 15 * 60  # 15 minutes in seconds
            
            return response
            
        except TokenError as e:
            return error_response(
                message="Token refresh failed",
                details=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class CustomerLogoutView(APIView):
    """
    Logout customer and blacklist refresh token.
    """
    permission_classes = [IsCustomerUser]
    
    def post(self, request):
        """Logout customer"""
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return error_response(
                message="Refresh token required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            success = CustomerAuthService.logout_customer(refresh_token)
            if not success:
                return error_response(
                    message="Logout failed",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            return success_response(
                message="Logout successful",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Logout failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetRequestView(APIView):
    """
    Request password reset for customer account.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Request password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            email = serializer.validated_data['email']
            result = CustomerAuthService.request_password_reset(email)
            
            # Always return success to prevent email enumeration
            return success_response(
                message="If an account with this email exists, a password reset link has been sent.",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Password reset request failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Confirm password reset"""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            success = CustomerAuthService.confirm_password_reset(token, new_password)
            if not success:
                return error_response(
                    message="Password reset failed",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            return success_response(
                message="Password reset successful",
                status_code=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="Password reset failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerProfileView(APIView):
    """
    Get current customer profile.
    """
    permission_classes = [IsCustomerUser]
    
    def get(self, request):
        """Get customer profile"""
        customer_user = request.user.customer_profile
        
        # Fetch preferences from UserPreference model
        from apps.user_preferences.services import UserPreferenceService
        prefs = UserPreferenceService.get_preferences(customer_user)
        
        profile_data = {
            'id': str(customer_user.id),
            'email': customer_user.user.email,
            'display_name': customer_user.display_name,
            'avatar_url': customer_user.avatar_url,
            'phone_number': customer_user.phone_number,
            'preferred_radius_m': prefs.get('search_radius_m', 500) if prefs else 500,
            'preferred_categories': prefs.get('preferred_category_slugs', []) if prefs else [],
            'last_known_lat': prefs.get('manual_location_lat') if prefs else None,
            'last_known_lng': prefs.get('manual_location_lng') if prefs else None,
            'notification_enabled': not prefs.get('notifications_all_off', False) if prefs else True,
            'created_at': customer_user.created_at.isoformat(),
            'updated_at': customer_user.updated_at.isoformat(),
        }
        
        return success_response(
            data=profile_data,
            message="Profile retrieved successfully",
            status_code=status.HTTP_200_OK
        )


class AccountExportView(APIView):
    """
    Export all user data (GDPR compliance).
    """
    permission_classes = [IsCustomerUser]
    
    def get(self, request):
        """Export user data"""
        try:
            customer_user = request.user.customer_profile
            user_data = CustomerAuthService.export_user_data(customer_user)
            
            from django.http import HttpResponse
            import json
            from datetime import datetime
            
            response = HttpResponse(
                json.dumps(user_data, indent=2, default=str),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="airad-data-export-{datetime.now().strftime("%Y%m%d")}.json"'
            
            return response
            
        except Exception as e:
            return error_response(
                message="Data export failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccountDeleteView(APIView):
    """
    Delete user account (GDPR right to erasure).
    """
    permission_classes = [IsCustomerUser]
    
    def delete(self, request):
        """Delete user account"""
        confirmation_code = request.data.get('confirmation_code')
        if not confirmation_code:
            return error_response(
                message="Confirmation code required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer_user = request.user.customer_profile
            success = CustomerAuthService.delete_user_account(
                customer_user, 
                confirmation_code
            )
            
            if not success:
                return error_response(
                    message="Account deletion failed",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            return success_response(
                message="Account deletion initiated. Your data will be permanently deleted after 30 days.",
                status_code=status.HTTP_202_ACCEPTED
            )
            
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="Account deletion failed",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConsentRecordView(APIView):
    """
    Record user consent for GDPR compliance.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def post(self, request):
        """Record consent"""
        try:
            consent_type = request.data.get('consent_type')
            consented = request.data.get('consented', False)
            consent_version = request.data.get('consent_version', '1.0')
            context = request.data.get('context', {})
            
            if not consent_type:
                return error_response(
                    message="Consent type required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user.customer_profile
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required for anonymous consent",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            CustomerAuthService.record_consent(
                user_or_guest=user_or_guest,
                consent_type=consent_type,
                consented=consented,
                consent_version=consent_version,
                ip_address=ip_address,
                user_agent=user_agent,
                context=context
            )
            
            return success_response(
                message="Consent recorded successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                message="Failed to record consent",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
