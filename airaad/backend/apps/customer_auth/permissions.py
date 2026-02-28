from rest_framework import permissions


class IsCustomerUser(permissions.BasePermission):
    """
    Permission to check if user is an authenticated customer.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and has customer profile.
        """
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'customer_profile') and
            not request.user.customer_profile.is_deleted
        )


class IsGuestOrAuthenticated(permissions.BasePermission):
    """
    Permission to allow either authenticated customers or guest users.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated customer or has valid guest token.
        """
        # Check for authenticated customer
        if (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'customer_profile') and
            not request.user.customer_profile.is_deleted
        ):
            return True
        
        # Check for guest token (set by GuestTokenAuthentication)
        return hasattr(request, 'guest_token')


class IsGuestOnly(permissions.BasePermission):
    """
    Permission to allow only guest users (not authenticated customers).
    """
    
    def has_permission(self, request, view):
        """
        Check if user is a guest (not authenticated but has guest token).
        """
        # Must not be authenticated
        if request.user and request.user.is_authenticated:
            return False
        
        # Must have guest token
        return hasattr(request, 'guest_token')


class HasValidConsent(permissions.BasePermission):
    """
    Permission to check if user has given required consent.
    """
    
    def __init__(self, consent_type=None):
        self.consent_type = consent_type
    
    def has_permission(self, request, view):
        """
        Check if user has given the required consent.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        customer_user = request.user.customer_profile
        
        # Check consent records
        from .models import ConsentRecord
        
        consent_query = ConsentRecord.objects.filter(
            user=customer_user,
            consent_type=self.consent_type,
            consented=True
        )
        
        return consent_query.exists()


class HasLocationConsent(HasValidConsent):
    """
    Permission to check if user has given location consent.
    """
    def __init__(self):
        super().__init__('LOCATION')


class HasAnalyticsConsent(HasValidConsent):
    """
    Permission to check if user has given analytics consent.
    """
    def __init__(self):
        super().__init__('ANALYTICS')


class HasVoiceConsent(HasValidConsent):
    """
    Permission to check if user has given voice data consent.
    """
    def __init__(self):
        super().__init__('VOICE')


class CustomerUserThrottle(permissions.BasePermission):
    """
    Permission class for rate limiting customer users.
    Different limits for authenticated vs guest users.
    """
    
    def has_permission(self, request, view):
        """
        Always returns True - rate limiting is handled by DRF throttling.
        This permission class exists to allow different throttle rates
        based on user type in DRF settings.
        """
        return True
