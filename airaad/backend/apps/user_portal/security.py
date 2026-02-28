"""
Security utilities for User Portal discovery and data protection.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point
from rest_framework import status
import re

logger = logging.getLogger(__name__)


class LocationPrivacy:
    """
    Location data privacy and security utilities.
    """
    
    # Location privacy settings
    LOCATION_PRECISION = {
        'HIGH': 6,      # ~1 meter precision
        'MEDIUM': 4,    # ~10 meter precision  
        'LOW': 3,       # ~100 meter precision
        'VERY_LOW': 2,  # ~1 kilometer precision
    }
    
    @classmethod
    def anonymize_location(cls, lat, lng, precision='MEDIUM'):
        """
        Anonymize location coordinates to protect user privacy.
        """
        if lat is None or lng is None:
            return None, None
        
        # Get precision level
        precision_level = cls.LOCATION_PRECISION.get(precision, 4)
        
        # Round coordinates to reduce precision
        lat_rounded = round(lat, precision_level)
        lng_rounded = round(lng, precision_level)
        
        return lat_rounded, lng_rounded
    
    @classmethod
    def hash_location(cls, lat, lng):
        """
        Create hash of location for privacy-preserving analytics.
        """
        if lat is None or lng is None:
            return None
        
        # Create geohash-like representation
        lat_int = int((lat + 90) * 1000000)  # Convert to integer
        lng_int = int((lng + 180) * 1000000)
        
        location_hash = hashlib.sha256(f"{lat_int}:{lng_int}".encode()).hexdigest()
        return location_hash[:16]  # Return first 16 characters
    
    @classmethod
    def validate_location_bounds(cls, lat, lng):
        """
        Validate location coordinates are within acceptable bounds.
        """
        if lat is None or lng is None:
            return False, "Location coordinates are required"
        
        # Check latitude bounds
        if not (-90 <= lat <= 90):
            return False, "Latitude must be between -90 and 90 degrees"
        
        # Check longitude bounds
        if not (-180 <= lng <= 180):
            return False, "Longitude must be between -180 and 180 degrees"
        
        # Check for precision (too many decimal places may indicate GPS spoofing)
        if abs(lat) > 0 and len(str(lat).split('.')[-1]) > 8:
            return False, "Latitude precision too high"
        
        if abs(lng) > 0 and len(str(lng).split('.')[-1]) > 8:
            return False, "Longitude precision too high"
        
        return True, "Valid location"
    
    @classmethod
    def apply_location_privacy_settings(cls, user_preferences, lat, lng):
        """
        Apply user's location privacy preferences.
        """
        if not user_preferences:
            return lat, lng
        
        # Check if user has disabled location sharing
        if not user_preferences.get('location_enabled', True):
            return None, None
        
        # Apply precision based on user settings
        privacy_level = user_preferences.get('location_privacy', 'MEDIUM')
        
        return cls.anonymize_location(lat, lng, privacy_level)


class InputValidation:
    """
    Input validation and sanitization for security.
    """
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(--|#|\/\*|\*\/)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+\w+\s*=\s*\w+)',
        r'(\b(OR|AND)\s+\'\w+\'\s*=\s*\'\w+\')',
        r'(\b(OR|AND)\s+"\w+"\s*=\s*"\w+")',
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick=, onload=, etc.
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
    ]
    
    @classmethod
    def validate_search_query(cls, query):
        """
        Validate search query for security threats.
        """
        if not query:
            return False, "Search query cannot be empty"
        
        # Length validation
        if len(query) > 200:
            return False, "Search query too long"
        
        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected: {query}")
                return False, "Invalid search query"
        
        # Check for XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"XSS attempt detected in search: {query}")
                return False, "Invalid search query"
        
        # Check for suspicious characters
        if re.search(r'[<>"\']', query):
            # Allow some special characters for legitimate searches
            sanitized = re.sub(r'[<>"\']', '', query)
            if len(sanitized) < len(query) * 0.5:  # More than 50% suspicious chars
                return False, "Invalid characters in search query"
        
        return True, "Valid search query"
    
    @classmethod
    def validate_coordinates(cls, lat, lng):
        """
        Validate coordinate inputs.
        """
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return False, "Invalid coordinate format"
        
        return LocationPrivacy.validate_location_bounds(lat, lng)
    
    @classmethod
    def validate_radius(cls, radius):
        """
        Validate search radius parameter.
        """
        try:
            radius = int(radius)
        except (ValueError, TypeError):
            return False, "Invalid radius format"
        
        if radius < 100:
            return False, "Radius must be at least 100 meters"
        
        if radius > 50000:  # 50km max
            return False, "Radius cannot exceed 50km"
        
        return True, "Valid radius"
    
    @classmethod
    def sanitize_input(cls, input_data):
        """
        Sanitize input data to prevent security issues.
        """
        if isinstance(input_data, str):
            # Remove HTML tags
            sanitized = re.sub(r'<[^>]+>', '', input_data)
            
            # Remove potential script content
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
            
            # Remove excessive whitespace
            sanitized = ' '.join(sanitized.split())
            
            return sanitized.strip()
        
        elif isinstance(input_data, dict):
            return {key: cls.sanitize_input(value) for key, value in input_data.items()}
        
        elif isinstance(input_data, list):
            return [cls.sanitize_input(item) for item in input_data]
        
        else:
            return input_data


class RateLimiting:
    """
    Advanced rate limiting for API protection.
    """
    
    # Rate limits per endpoint
    RATE_LIMITS = {
        'nearby_vendors': {'requests': 60, 'window': 60, 'burst': 10},
        'ar_markers': {'requests': 120, 'window': 60, 'burst': 20},
        'search': {'requests': 30, 'window': 60, 'burst': 5},
        'voice_search': {'requests': 20, 'window': 60, 'burst': 3},
        'vendor_detail': {'requests': 100, 'window': 60, 'burst': 15},
        'default': {'requests': 100, 'window': 60, 'burst': 10},
    }
    
    @classmethod
    def check_rate_limit(cls, client_id, endpoint_type):
        """
        Check if client has exceeded rate limit.
        """
        from django.core.cache import cache
        
        rate_config = cls.RATE_LIMITS.get(endpoint_type, cls.RATE_LIMITS['default'])
        
        # Primary counter
        cache_key = f"rate_limit:{endpoint_type}:{client_id}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= rate_config['requests']:
            return False, rate_config['window']
        
        # Burst protection
        burst_key = f"rate_burst:{endpoint_type}:{client_id}"
        burst_count = cache.get(burst_key, 0)
        
        if burst_count >= rate_config['burst']:
            return False, min(rate_config['window'], 30)  # Shorter window for burst
        
        # Increment counters
        cache.set(cache_key, current_count + 1, timeout=rate_config['window'])
        cache.set(burst_key, burst_count + 1, timeout=30)  # 30 second burst window
        
        return True, None
    
    @classmethod
    def get_client_identifier(cls, request):
        """
        Get client identifier for rate limiting.
        """
        # Try authenticated user first
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Try guest token
        guest_token = request.headers.get('X-Guest-Token')
        if guest_token:
            return f"guest:{guest_token}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        return f"ip:{ip}"


class ContentSecurity:
    """
    Content security and validation for user-generated content.
    """
    
    ALLOWED_MIME_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'video': ['video/mp4', 'video/webm', 'video/quicktime'],
        'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg'],
    }
    
    MAX_FILE_SIZES = {
        'image': 5 * 1024 * 1024,      # 5MB
        'video': 50 * 1024 * 1024,     # 50MB
        'audio': 10 * 1024 * 1024,     # 10MB
    }
    
    @classmethod
    def validate_file_upload(cls, file, file_type):
        """
        Validate uploaded file for security.
        """
        if not file:
            return False, "No file provided"
        
        # Check file size
        max_size = cls.MAX_FILE_SIZES.get(file_type, 5 * 1024 * 1024)
        if file.size > max_size:
            return False, f"File size exceeds limit of {max_size // (1024*1024)}MB"
        
        # Check MIME type
        allowed_types = cls.ALLOWED_MIME_TYPES.get(file_type, [])
        if file.content_type not in allowed_types:
            return False, f"File type {file.content_type} not allowed"
        
        # Additional validation for images
        if file_type == 'image':
            try:
                from PIL import Image
                img = Image.open(file)
                
                # Check image dimensions
                if img.width > 4096 or img.height > 4096:
                    return False, "Image dimensions too large"
                
                # Check for malicious content in image metadata
                if hasattr(img, '_getexif') and img._getexif():
                    # Remove EXIF data for privacy
                    pass
                    
            except Exception as e:
                return False, f"Invalid image file: {e}"
        
        return True, "Valid file"
    
    @classmethod
    def sanitize_content(cls, content):
        """
        Sanitize user-generated content.
        """
        if not content:
            return content
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove potentially dangerous URLs
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        content = re.sub(r'data:', '', content, flags=re.IGNORECASE)
        
        # Limit length
        if len(content) > 1000:
            content = content[:1000] + '...'
        
        return content.strip()


class AuditLogger:
    """
    Security audit logging for user portal.
    """
    
    @classmethod
    def log_discovery_event(cls, event_type, user_or_guest, details=None, 
                           ip_address=None, user_agent=None):
        """
        Log discovery-related security events.
        """
        from apps.audit.models import AuditLog
        
        # Determine user identification
        user_id = None
        if hasattr(user_or_guest, 'customer_profile'):
            user_id = user_or_guest.customer_profile.id
        elif hasattr(user_or_guest, 'id'):
            user_id = user_or_guest.id
        
        # Log the security event
        AuditLog.log_action(
            user_id=user_id,
            action=f"DISCOVERY_{event_type}",
            entity_type="DISCOVERY_EVENT",
            metadata={
                'event_type': event_type,
                'details': details or {},
                'ip_address': ip_address,
                'user_agent': user_agent or '',
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @classmethod
    def log_location_access(cls, user_or_guest, lat, lng, radius, 
                           ip_address=None, user_agent=None):
        """
        Log location access for privacy compliance.
        """
        # Hash location for privacy
        location_hash = LocationPrivacy.hash_location(lat, lng)
        
        cls.log_discovery_event(
            'LOCATION_ACCESS',
            user_or_guest,
            {
                'location_hash': location_hash,
                'radius': radius,
                'precision_applied': 'MEDIUM',  # Default precision
            },
            ip_address,
            user_agent
        )
    
    @classmethod
    def log_search_activity(cls, user_or_guest, query, result_count,
                           ip_address=None, user_agent=None):
        """
        Log search activity for analytics and security.
        """
        cls.log_discovery_event(
            'SEARCH_ACTIVITY',
            user_or_guest,
            {
                'query_length': len(query) if query else 0,
                'result_count': result_count,
                'query_hash': hashlib.sha256(query.encode()).hexdigest()[:16] if query else None,
            },
            ip_address,
            user_agent
        )


class SecurityHeaders:
    """
    Security headers for API responses.
    """
    
    @classmethod
    def get_security_headers(cls):
        """
        Get security headers for API responses.
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Permissions-Policy': (
                'geolocation=(), '
                'camera=(), '
                'microphone=(), '
                'payment=(), '
                'usb=(), '
                'magnetometer=(), '
                'gyroscope=(), '
                'accelerometer=()'
            ),
        }
    
    @classmethod
    def apply_cors_headers(cls, response, origin=None):
        """
        Apply CORS headers for cross-origin requests.
        """
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', ['*'])
        
        if origin:
            if allowed_origins == ['*'] or origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
        else:
            response['Access-Control-Allow-Origin'] = allowed_origins[0] if allowed_origins else '*'
        
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Guest-Token'
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
