from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsCustomerUser(permissions.BasePermission):
    """
    Permission to check if user is a customer.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user has a customer profile
        try:
            from apps.customer_auth.models import CustomerUser
            return CustomerUser.objects.filter(user=request.user).exists()
        except:
            return False


class IsGuestOrAuthenticated(permissions.BasePermission):
    """
    Permission that allows either authenticated users or guest sessions.
    """
    
    def has_permission(self, request, view):
        # Allow authenticated users
        if request.user.is_authenticated:
            return True
        
        # Allow guest requests with valid guest token
        guest_token = request.headers.get('X-Guest-Token')
        if guest_token:
            try:
                from apps.customer_auth.models import GuestToken
                return GuestToken.objects.filter(
                    token=guest_token,
                    is_active=True
                ).exists()
            except:
                return False
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission that allows only owners to edit, but anyone to read.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        try:
            from apps.customer_auth.models import CustomerUser
            customer_user = CustomerUser.objects.get(user=request.user)
            return obj.user == customer_user
        except:
            return False


class IsVendorOwner(permissions.BasePermission):
    """
    Permission to check if user owns the vendor.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        try:
            from apps.customer_auth.models import CustomerUser
            customer_user = CustomerUser.objects.get(user=request.user)
            
            # Check if user is associated with this vendor
            if hasattr(obj, 'vendor'):
                return obj.vendor.user == customer_user
            elif hasattr(obj, 'id'):
                # For Vendor objects directly
                return obj.user == customer_user
            
            return False
        except:
            return False


class HasValidConsent(permissions.BasePermission):
    """
    Permission to check if user has given required consent.
    """
    
    def __init__(self, consent_type=None):
        self.consent_type = consent_type
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            from apps.customer_auth.models import CustomerUser, ConsentRecord
            customer_user = CustomerUser.objects.get(user=request.user)
            
            # Check for specific consent type if provided
            if self.consent_type:
                return ConsentRecord.objects.filter(
                    user=customer_user,
                    consent_type=self.consent_type,
                    consented=True
                ).exists()
            
            # Check for basic required consents
            required_consents = ['TERMS', 'PRIVACY']
            return ConsentRecord.objects.filter(
                user=customer_user,
                consent_type__in=required_consents,
                consented=True
            ).count() == len(required_consents)
            
        except:
            return False
