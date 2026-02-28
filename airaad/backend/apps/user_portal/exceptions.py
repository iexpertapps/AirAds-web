"""
Custom exceptions for User Portal with structured error handling.
"""

from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils import timezone
import uuid


class UserPortalException(APIException):
    """
    Base exception for user portal errors.
    """
    def __init__(self, message, error_code=None, category='DISCOVERY', 
                 severity='ERROR', details=None, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code or 'PORTAL_ERROR'
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = timezone.now().isoformat()
        self.request_id = str(uuid.uuid4())
        
        super().__init__(message)


class LocationValidationException(UserPortalException):
    """
    Exception for location validation failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='LOCATION_VALIDATION_FAILED',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidCoordinatesException(UserPortalException):
    """
    Exception for invalid coordinate inputs.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='INVALID_COORDINATES',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class SearchValidationException(UserPortalException):
    """
    Exception for search query validation failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='SEARCH_VALIDATION_FAILED',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class VendorNotFoundException(UserPortalException):
    """
    Exception when vendor is not found.
    """
    def __init__(self, message, vendor_id=None, details=None):
        details = details or {}
        if vendor_id:
            details['vendor_id'] = str(vendor_id)
        
        super().__init__(
            message=message,
            error_code='VENDOR_NOT_FOUND',
            category='DISCOVERY',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )


class NoResultsFoundException(UserPortalException):
    """
    Exception when no results are found for search/discovery.
    """
    def __init__(self, message, search_type=None, details=None):
        details = details or {}
        if search_type:
            details['search_type'] = search_type
        
        super().__init__(
            message=message,
            error_code='NO_RESULTS_FOUND',
            category='DISCOVERY',
            severity='INFO',
            details=details,
            status_code=status.HTTP_200_OK  # Not an error, just no results
        )


class RadiusOutOfRangeException(UserPortalException):
    """
    Exception when search radius is out of allowed range.
    """
    def __init__(self, message, radius=None, details=None):
        details = details or {}
        if radius:
            details['requested_radius'] = radius
        
        super().__init__(
            message=message,
            error_code='RADIUS_OUT_OF_RANGE',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RateLimitExceededException(UserPortalException):
    """
    Exception for rate limit exceeded.
    """
    def __init__(self, message, retry_after=None, details=None):
        details = details or {}
        if retry_after:
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            error_code='RATE_LIMIT_EXCEEDED',
            category='SECURITY',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class SecurityViolationException(UserPortalException):
    """
    Exception for security violations in user portal.
    """
    def __init__(self, message, violation_type=None, details=None):
        details = details or {}
        if violation_type:
            details['violation_type'] = violation_type
        
        super().__init__(
            message=message,
            error_code='SECURITY_VIOLATION',
            category='SECURITY',
            severity='CRITICAL',
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class LocationPrivacyException(UserPortalException):
    """
    Exception for location privacy violations.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='LOCATION_PRIVACY_VIOLATION',
            category='PRIVACY',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ContentSecurityException(UserPortalException):
    """
    Exception for content security violations.
    """
    def __init__(self, message, content_type=None, details=None):
        details = details or {}
        if content_type:
            details['content_type'] = content_type
        
        super().__init__(
            message=message,
            error_code='CONTENT_SECURITY_VIOLATION',
            category='SECURITY',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ServiceUnavailableException(UserPortalException):
    """
    Exception when discovery services are unavailable.
    """
    def __init__(self, message, service_name=None, details=None):
        details = details or {}
        if service_name:
            details['service_name'] = service_name
        
        super().__init__(
            message=message,
            error_code='SERVICE_UNAVAILABLE',
            category='INFRASTRUCTURE',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class CacheException(UserPortalException):
    """
    Exception for cache-related errors.
    """
    def __init__(self, message, cache_operation=None, details=None):
        details = details or {}
        if cache_operation:
            details['cache_operation'] = cache_operation
        
        super().__init__(
            message=message,
            error_code='CACHE_ERROR',
            category='INFRASTRUCTURE',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class PerformanceException(UserPortalException):
    """
    Exception for performance-related issues.
    """
    def __init__(self, message, operation=None, duration_ms=None, details=None):
        details = details or {}
        if operation:
            details['operation'] = operation
        if duration_ms:
            details['duration_ms'] = duration_ms
        
        super().__init__(
            message=message,
            error_code='PERFORMANCE_ISSUE',
            category='PERFORMANCE',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DataIntegrityException(UserPortalException):
    """
    Exception for data integrity issues.
    """
    def __init__(self, message, entity_type=None, entity_id=None, details=None):
        details = details or {}
        if entity_type:
            details['entity_type'] = entity_type
        if entity_id:
            details['entity_id'] = str(entity_id)
        
        super().__init__(
            message=message,
            error_code='DATA_INTEGRITY_ERROR',
            category='DATA',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class RankingCalculationException(UserPortalException):
    """
    Exception for ranking calculation errors.
    """
    def __init__(self, message, vendor_id=None, details=None):
        details = details or {}
        if vendor_id:
            details['vendor_id'] = str(vendor_id)
        
        super().__init__(
            message=message,
            error_code='RANKING_CALCULATION_ERROR',
            category='DISCOVERY',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class SpatialQueryException(UserPortalException):
    """
    Exception for spatial query errors.
    """
    def __init__(self, message, query_type=None, details=None):
        details = details or {}
        if query_type:
            details['query_type'] = query_type
        
        super().__init__(
            message=message,
            error_code='SPATIAL_QUERY_ERROR',
            category='DISCOVERY',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Exception severity levels
class ErrorSeverity:
    """Error severity levels for classification."""
    CRITICAL = 'CRITICAL'  # Security breaches, data integrity
    ERROR = 'ERROR'        # Validation failures, service errors
    WARNING = 'WARNING'    # Rate limits, performance issues
    INFO = 'INFO'          # No results found, informational


# Error categories
class ErrorCategory:
    """Error categories for classification."""
    DISCOVERY = 'DISCOVERY'              # Search, ranking, spatial queries
    VALIDATION = 'VALIDATION'            # Input validation, coordinate validation
    SECURITY = 'SECURITY'                # Rate limiting, content security
    PRIVACY = 'PRIVACY'                  # Location privacy, data protection
    INFRASTRUCTURE = 'INFRASTRUCTURE'    # Services, cache, performance
    DATA = 'DATA'                        # Data integrity, migration
    PERFORMANCE = 'PERFORMANCE'          # Slow queries, performance issues


# Exception handler utility
class ExceptionHandler:
    """
    Utility for handling and formatting exceptions.
    """
    
    @staticmethod
    def format_exception_response(exception):
        """
        Format exception for API response.
        """
        if isinstance(exception, UserPortalException):
            return {
                'error': {
                    'message': exception.message,
                    'error_code': exception.error_code,
                    'category': exception.category,
                    'severity': exception.severity,
                    'details': exception.details,
                    'timestamp': exception.timestamp,
                    'request_id': exception.request_id,
                }
            }
        else:
            # Handle unexpected exceptions
            return {
                'error': {
                    'message': 'An unexpected error occurred',
                    'error_code': 'INTERNAL_ERROR',
                    'category': 'INFRASTRUCTURE',
                    'severity': 'CRITICAL',
                    'details': {},
                    'timestamp': timezone.now().isoformat(),
                    'request_id': str(uuid.uuid4()),
                }
            }
    
    @staticmethod
    def log_exception(exception, request=None):
        """
        Log exception for debugging and monitoring.
        """
        import logging
        
        logger = logging.getLogger('user_portal')
        
        log_data = {
            'exception_type': type(exception).__name__,
            'message': str(exception),
            'error_code': getattr(exception, 'error_code', 'UNKNOWN'),
            'category': getattr(exception, 'category', 'UNKNOWN'),
            'severity': getattr(exception, 'severity', 'ERROR'),
            'details': getattr(exception, 'details', {}),
            'timestamp': timezone.now().isoformat(),
        }
        
        if request:
            log_data.update({
                'path': request.path,
                'method': request.method,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
            })
        
        # Log based on severity
        if log_data['severity'] == 'CRITICAL':
            logger.critical(f"Critical error: {log_data}")
        elif log_data['severity'] == 'ERROR':
            logger.error(f"Error: {log_data}")
        elif log_data['severity'] == 'WARNING':
            logger.warning(f"Warning: {log_data}")
        else:
            logger.info(f"Info: {log_data}")
    
    @staticmethod
    def handle_exception(exception, request=None):
        """
        Handle exception with logging and response formatting.
        """
        # Log the exception
        ExceptionHandler.log_exception(exception, request)
        
        # Format response
        response_data = ExceptionHandler.format_exception_response(exception)
        
        # Return response data and status code
        return response_data, getattr(exception, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
