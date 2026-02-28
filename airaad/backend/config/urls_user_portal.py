"""
User Portal URL Configuration
"""
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView

def api_version_info(request):
    """Return API version information"""
    versions = {
        'v1': {
            'status': 'stable',
            'deprecated': False,
            'sunset_date': None,
            'released': '2026-02-01'
        }
    }
    
    return JsonResponse({
        'current_version': 'v1',
        'supported_versions': versions,
        'default_version': 'v1'
    })

urlpatterns = [
    # API version info
    path('', api_version_info, name='api_version_info'),
    
    # User Portal v1 endpoints
    path('v1/', include([
        # Customer Authentication
        path('auth/', include('apps.customer_auth.urls')),
        
        # User Preferences
        path('preferences/', include('apps.user_preferences.urls')),
        
        # Discovery Engine
        path('user-portal/', include('apps.user_portal.urls')),
        
        # Token refresh (JWT)
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    ])),
]
