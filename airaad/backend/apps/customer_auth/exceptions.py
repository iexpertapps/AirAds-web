"""
Custom exceptions for Customer Authentication with structured error handling.
"""

from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils import timezone
import uuid


class CustomerAuthException(APIException):
    """
    Base exception for customer authentication errors.
    """
    def __init__(self, message, error_code=None, category='AUTHENTICATION', 
                 severity='ERROR', details=None, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code or 'AUTH_ERROR'
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = timezone.now().isoformat()
        self.request_id = str(uuid.uuid4())
        
        super().__init__(message)


class AuthenticationFailedException(CustomerAuthException):
    """
    Exception for authentication failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='AUTH_FAILED',
            category='AUTHENTICATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidTokenException(CustomerAuthException):
    """
    Exception for invalid JWT tokens.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='INVALID_TOKEN',
            category='AUTHENTICATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class TokenExpiredException(CustomerAuthException):
    """
    Exception for expired JWT tokens.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='TOKEN_EXPIRED',
            category='AUTHENTICATION',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidGuestTokenException(CustomerAuthException):
    """
    Exception for invalid guest tokens.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='INVALID_GUEST_TOKEN',
            category='AUTHENTICATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class GuestTokenExpiredException(CustomerAuthException):
    """
    Exception for expired guest tokens.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='GUEST_TOKEN_EXPIRED',
            category='AUTHENTICATION',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class UserAlreadyExistsException(CustomerAuthException):
    """
    Exception when user already exists during registration.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='USER_ALREADY_EXISTS',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_409_CONFLICT
        )


class PasswordValidationException(CustomerAuthException):
    """
    Exception for password validation failures.
    """
    def __init__(self, message, validation_errors=None):
        details = {'validation_errors': validation_errors} if validation_errors else {}
        super().__init__(
            message=message,
            error_code='PASSWORD_VALIDATION_FAILED',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class EmailVerificationException(CustomerAuthException):
    """
    Exception for email verification failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='EMAIL_VERIFICATION_FAILED',
            category='AUTHENTICATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AccountDeletionException(CustomerAuthException):
    """
    Exception for account deletion failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='ACCOUNT_DELETION_FAILED',
            category='ACCOUNT_MANAGEMENT',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class DataExportException(CustomerAuthException):
    """
    Exception for data export failures.
    """
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            error_code='DATA_EXPORT_FAILED',
            category='DATA_MANAGEMENT',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ConsentRequiredException(CustomerAuthException):
    """
    Exception when required consent is not given.
    """
    def __init__(self, message, consent_type=None, details=None):
        details = details or {}
        if consent_type:
            details['consent_type'] = consent_type
        
        super().__init__(
            message=message,
            error_code='CONSENT_REQUIRED',
            category='GDPR',
            severity='WARNING',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RateLimitExceededException(CustomerAuthException):
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


class SecurityViolationException(CustomerAuthException):
    """
    Exception for security violations.
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


class InvalidInputException(CustomerAuthException):
    """
    Exception for invalid input data.
    """
    def __init__(self, message, field_name=None, validation_errors=None, details=None):
        details = details or {}
        if field_name:
            details['field_name'] = field_name
        if validation_errors:
            details['validation_errors'] = validation_errors
        
        super().__init__(
            message=message,
            error_code='INVALID_INPUT',
            category='VALIDATION',
            severity='ERROR',
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ServiceUnavailableException(CustomerAuthException):
    """
    Exception when required services are unavailable.
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


# Exception severity levels
class ErrorSeverity:
    """Error severity levels for classification."""
    CRITICAL = 'CRITICAL'  # Security breaches, system failures
    ERROR = 'ERROR'        # Authentication failures, validation errors
    WARNING = 'WARNING'    # Expired tokens, rate limits
    INFO = 'INFO'          # Informational messages


# Error categories
class ErrorCategory:
    """Error categories for classification."""
    AUTHENTICATION = 'AUTHENTICATION'      # Login, token, guest auth
    VALIDATION = 'VALIDATION'              # Input validation, password rules
    ACCOUNT_MANAGEMENT = 'ACCOUNT_MANAGEMENT'  # Registration, deletion, export
    GDPR = 'GDPR'                          # Consent, data protection
    SECURITY = 'SECURITY'                  # Rate limiting, security violations
    DATA_MANAGEMENT = 'DATA_MANAGEMENT'    # Data export, migration
    INFRASTRUCTURE = 'INFRASTRUCTURE'      # Service availability, database


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
        if isinstance(exception, CustomerAuthException):
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
        
        logger = logging.getLogger('customer_auth')
        
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
