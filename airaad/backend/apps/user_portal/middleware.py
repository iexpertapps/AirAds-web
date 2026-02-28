"""
Performance and security middleware for User Portal.
"""

import time
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status
import logging

from .cache import PerformanceMonitor, CacheManager

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor API performance and collect metrics.
    """
    
    def process_request(self, request):
        """Record request start time."""
        request._start_time = time.time()
        request._request_id = str(uuid.uuid4())
        
        # Add request ID to response headers
        request.META['HTTP_X_REQUEST_ID'] = request._request_id
        
        return None
    
    def process_response(self, request, response):
        """Record performance metrics."""
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            
            # Add performance headers
            response['X-Response-Time'] = f"{duration_ms:.2f}ms"
            response['X-Request-ID'] = getattr(request, '_request_id', '')
            
            # Record metrics for API endpoints
            if request.path.startswith('/api/user-portal/'):
                query_type = self._get_query_type(request.path)
                result_count = self._get_result_count(response)
                
                PerformanceMonitor.record_query_performance(
                    query_type=query_type,
                    duration_ms=duration_ms,
                    result_count=result_count
                )
        
        return response
    
    def _get_query_type(self, path):
        """Extract query type from request path."""
        path_parts = path.strip('/').split('/')
        
        if 'nearby' in path:
            return 'nearby_vendors'
        elif 'ar-markers' in path:
            return 'ar_markers'
        elif 'search' in path:
            return 'search'
        elif 'voice-search' in path:
            return 'voice_search'
        elif 'vendors' in path and len(path_parts) > 4:
            return 'vendor_detail'
        elif 'tags' in path:
            return 'tags'
        elif 'cities' in path:
            return 'cities'
        elif 'promotions-strip' in path:
            return 'promotions'
        elif 'flash-deals' in path:
            return 'flash_deals'
        elif 'nearby-reels' in path:
            return 'nearby_reels'
        else:
            return 'unknown'
    
    def _get_result_count(self, response):
        """Extract result count from response."""
        try:
            if hasattr(response, 'data'):
                # DRF Response
                if isinstance(response.data, dict):
                    if 'results' in response.data:
                        return len(response.data['results'])
                    elif 'vendors' in response.data:
                        return len(response.data['vendors'])
                    elif 'markers' in response.data:
                        return len(response.data['markers'])
                    elif 'promotions' in response.data:
                        return len(response.data['promotions'])
                    elif 'reels' in response.data:
                        return len(response.data['reels'])
                    elif 'tags' in response.data:
                        return len(response.data['tags'])
                    elif 'cities' in response.data:
                        return len(response.data['cities'])
                    elif 'flash_deals' in response.data:
                        return len(response.data['flash_deals'])
        except Exception:
            pass
        
        return 0


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for API endpoints.
    """
    
    # Rate limits per minute per IP/user
    RATE_LIMITS = {
        'nearby_vendors': {'requests': 60, 'window': 60},      # 60/minute
        'ar_markers': {'requests': 120, 'window': 60},         # 120/minute (AR needs more)
        'search': {'requests': 30, 'window': 60},              # 30/minute
        'voice_search': {'requests': 20, 'window': 60},        # 20/minute
        'vendor_detail': {'requests': 100, 'window': 60},      # 100/minute
        'default': {'requests': 100, 'window': 60},           # 100/minute default
    }
    
    def process_request(self, request):
        """Check rate limits."""
        if not request.path.startswith('/api/user-portal/'):
            return None
        
        # Get client identifier
        client_id = self._get_client_id(request)
        query_type = self._get_query_type(request.path)
        
        # Get rate limit for this endpoint
        rate_limit = self.RATE_LIMITS.get(query_type, self.RATE_LIMITS['default'])
        
        # Check cache for current count
        cache_key = f"rate_limit:{query_type}:{client_id}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= rate_limit['requests']:
            # Rate limit exceeded
            response = JsonResponse({
                'error': {
                    'message': 'Rate limit exceeded',
                    'details': f'Maximum {rate_limit["requests"]} requests per {rate_limit["window"]} seconds',
                    'retry_after': rate_limit['window']
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            response['Retry-After'] = str(rate_limit['window'])
            return response
        
        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=rate_limit['window'])
        
        return None
    
    def _get_client_id(self, request):
        """Get client identifier for rate limiting."""
        # Try to get authenticated user ID
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        return f"ip:{ip}"
    
    def _get_query_type(self, path):
        """Extract query type from request path."""
        path_parts = path.strip('/').split('/')
        
        if 'nearby' in path:
            return 'nearby_vendors'
        elif 'ar-markers' in path:
            return 'ar_markers'
        elif 'search' in path:
            return 'search'
        elif 'voice-search' in path:
            return 'voice_search'
        elif 'vendors' in path and len(path_parts) > 4:
            return 'vendor_detail'
        else:
            return 'default'


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Security headers middleware for API responses.
    """
    
    def process_response(self, request, response):
        """Add security headers."""
        if request.path.startswith('/api/user-portal/'):
            # Security headers
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # CORS headers (configure based on your needs)
            response['Access-Control-Allow-Origin'] = settings.CORS_ALLOWED_ORIGINS[0] if hasattr(settings, 'CORS_ALLOWED_ORIGINS') else '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Guest-Token'
            response['Access-Control-Max-Age'] = '86400'  # 24 hours
            
            # Cache control for API responses
            if request.method == 'GET':
                # Cache GET requests
                cache_control = 'public, max-age=300'  # 5 minutes
                if 'ar-markers' in request.path:
                    cache_control = 'public, max-age=30'  # 30 seconds for AR
                elif 'search' in request.path:
                    cache_control = 'public, max-age=300'  # 5 minutes for search
                elif 'tags' in request.path or 'cities' in request.path:
                    cache_control = 'public, max-age=3600'  # 1 hour for static data
                
                response['Cache-Control'] = cache_control
            else:
                # Don't cache POST/PUT/DELETE requests
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
        
        return response


class CacheControlMiddleware(MiddlewareMixin):
    """
    Intelligent cache control middleware.
    """
    
    def process_response(self, request, response):
        """Add cache control headers based on response content."""
        if not request.path.startswith('/api/user-portal/'):
            return response
        
        # Skip caching for error responses
        if response.status_code >= 400:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        
        # Skip caching for authenticated user-specific data
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            'preferences' in request.path):
            response['Cache-Control'] = 'private, max-age=300'
            return response
        
        # Add ETag for GET requests if not present
        if request.method == 'GET' and 'ETag' not in response:
            etag = self._generate_etag(response)
            if etag:
                response['ETag'] = etag
        
        return response
    
    def _generate_etag(self, response):
        """Generate ETag for response."""
        try:
            if hasattr(response, 'data'):
                # DRF Response
                content = str(response.data)
            else:
                # Django HttpResponse
                content = response.content.decode('utf-8')
            
            # Generate hash of content
            import hashlib
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Request logging middleware for debugging and monitoring.
    """
    
    def process_request(self, request):
        """Log incoming requests."""
        if request.path.startswith('/api/user-portal/'):
            logger.info(
                f"API Request: {request.method} {request.path} "
                f"from {self._get_client_ip(request)} "
                f"user={getattr(request.user, 'id', 'anonymous')}"
            )
    
    def process_response(self, request, response):
        """Log response status."""
        if request.path.startswith('/api/user-portal/'):
            logger.info(
                f"API Response: {request.method} {request.path} "
                f"status={response.status_code} "
                f"duration={getattr(response, 'X-Response-Time', 'unknown')}"
            )
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
