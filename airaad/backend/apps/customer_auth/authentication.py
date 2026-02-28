from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from .models import GuestToken, CustomerUser

User = get_user_model()


class CustomerUserAuthentication(JWTAuthentication):
    """
    Custom JWT authentication for customer users.
    Validates audience claim to ensure tokens are for user-portal only.
    """
    
    def get_validated_token(self, raw_token):
        """
        Validate JWT token and check audience.
        """
        try:
            validated_token = super().get_validated_token(raw_token)
            
            # Check audience claim
            audience = validated_token.get('aud')
            if audience != 'user-portal':
                raise InvalidToken('Invalid token audience')
            
            return validated_token
            
        except TokenError as e:
            raise InvalidToken(str(e))
    
    def get_user(self, validated_token):
        """
        Get user from validated token.
        """
        try:
            user_id = validated_token['user_id']
            user = User.objects.get(id=user_id)
            
            # Check if user has customer profile
            if not hasattr(user, 'customer_profile'):
                raise AuthenticationFailed('User is not a customer')
            
            # Check if customer is not soft-deleted
            customer_user = user.customer_profile
            if customer_user.is_deleted:
                raise AuthenticationFailed('Customer account has been deleted')
            
            return user
            
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
        except KeyError:
            raise AuthenticationFailed('Token contains no recognizable user identification')


class GuestTokenAuthentication(BaseAuthentication):
    """
    Authentication for guest users using guest tokens.
    """
    
    def authenticate(self, request):
        """
        Authenticate guest user using X-Guest-Token header.
        """
        guest_token_header = request.headers.get('X-Guest-Token')
        if not guest_token_header:
            return None
        
        try:
            # Validate guest token
            guest_token_obj = GuestToken.objects.get(
                token=guest_token_header,
                is_active=True
            )
            
            if guest_token_obj.is_expired:
                guest_token_obj.is_active = False
                guest_token_obj.save()
                return None
            
            # Update usage tracking
            guest_token_obj.api_calls_count += 1
            guest_token_obj.last_used_at = guest_token_obj.created_at  # Will be updated by auto_now
            guest_token_obj.save()
            
            # Return None for user (guest) and guest token as auth
            return (None, guest_token_obj)
            
        except GuestToken.DoesNotExist:
            return None
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Guest token'


class CustomerOrGuestAuthentication(BaseAuthentication):
    """
    Combined authentication that accepts either JWT tokens or guest tokens.
    Tries JWT first, then guest token.
    """
    
    def __init__(self):
        self.jwt_auth = CustomerUserAuthentication()
        self.guest_auth = GuestTokenAuthentication()
    
    def authenticate(self, request):
        """
        Try JWT authentication first, then guest token.
        """
        # Try JWT authentication
        jwt_result = self.jwt_auth.authenticate(request)
        if jwt_result:
            return jwt_result
        
        # Try guest token authentication
        guest_result = self.guest_auth.authenticate(request)
        if guest_result:
            return guest_result
        
        return None
    
    def authenticate_header(self, request):
        """
        Return appropriate authentication header.
        """
        return 'Bearer or Guest token'
