from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status
import traceback
import logging

from .models_error import ErrorLog

logger = logging.getLogger(__name__)


class GlobalExceptionHandlerMiddleware(MiddlewareMixin):
    """
    Global exception handler middleware.
    Catches all unhandled exceptions and logs them systematically.
    """
    
    def process_exception(self, request, exception):
        """
        Handle unhandled exceptions.
        Returns appropriate error response and logs the exception.
        """
        # Log the exception with full context
        error_log = ErrorLog.log_exception(
            exception=exception,
            request=request,
            user=getattr(request, 'user', None),
            context={
                'middleware': 'GlobalExceptionHandler',
                'unhandled': True,
            }
        )
        
        # Determine response based on exception type and debug mode
        if settings.DEBUG:
            # In debug mode, return detailed error info
            return JsonResponse({
                'error': {
                    'message': str(exception),
                    'type': type(exception).__name__,
                    'error_id': str(error_log.id),
                    'stack_trace': traceback.format_exc(),
                }
            }, status=500)
        
        # In production, return generic error message
        return JsonResponse({
            'error': {
                'message': 'An internal server error occurred',
                'error_id': str(error_log.id),
                'type': 'INTERNAL_SERVER_ERROR',
            }
        }, status=500)


class APIErrorHandlerMiddleware(MiddlewareMixin):
    """
    API-specific error handler middleware.
    Handles API errors and formats responses consistently.
    """
    
    def process_response(self, request, response):
        """
        Process response and handle error responses.
        """
        # Only handle API responses
        if not request.path.startswith('/api/'):
            return response
        
        # Log error responses (4xx, 5xx)
        if response.status_code >= 400:
            try:
                # Try to extract error details from response
                error_data = {}
                if hasattr(response, 'data'):
                    error_data = response.data
                elif hasattr(response, 'content'):
                    try:
                        import json
                        error_data = json.loads(response.content.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
                
                # Determine error type and severity
                error_type = self._classify_api_error(response.status_code)
                severity = self._determine_api_severity(response.status_code)
                
                # Log the error
                ErrorLog.log_error(
                    error_type=error_type,
                    error_message=error_data.get('message', f'HTTP {response.status_code}'),
                    severity=severity,
                    request=request,
                    user=getattr(request, 'user', None),
                    error_code=str(response.status_code),
                    context={
                        'middleware': 'APIErrorHandler',
                        'status_code': response.status_code,
                        'response_data': error_data,
                    }
                )
                
            except Exception as e:
                # Don't let error logging break the main flow
                logger.error(f"Failed to log API error: {e}")
        
        return response
    
    def _classify_api_error(self, status_code):
        """Classify API error based on status code."""
        if status_code == 400:
            return 'VALIDATION'
        elif status_code == 401:
            return 'AUTHENTICATION'
        elif status_code == 403:
            return 'AUTHORIZATION'
        elif status_code == 404:
            return 'API'
        elif status_code == 429:
            return 'PERFORMANCE'
        elif status_code >= 500:
            return 'SYSTEM'
        else:
            return 'API'
    
    def _determine_api_severity(self, status_code):
        """Determine severity based on status code."""
        if status_code >= 500:
            return 'HIGH'
        elif status_code == 429:
            return 'MEDIUM'
        elif status_code in [401, 403]:
            return 'MEDIUM'
        else:
            return 'LOW'


class ValidationErrorHandlerMiddleware(MiddlewareMixin):
    """
    Validation error handler middleware.
    Provides detailed validation error responses.
    """
    
    def process_response(self, request, response):
        """
        Process validation errors and enhance them.
        """
        # Only handle API responses with validation errors
        if (not request.path.startswith('/api/') or 
            response.status_code != 400):
            return response
        
        try:
            # Check if this is a validation error
            if hasattr(response, 'data'):
                error_data = response.data
                
                # Enhance validation errors
                if isinstance(error_data, dict):
                    enhanced = self._enhance_validation_errors(error_data)
                    if enhanced != error_data:
                        response.data = enhanced
        
        except Exception as e:
            # Don't let error enhancement break the main flow
            logger.error(f"Failed to enhance validation error: {e}")
        
        return response
    
    def _enhance_validation_errors(self, error_data):
        """Enhance validation error data."""
        enhanced = error_data.copy()
        
        # Add error type classification
        if 'field_errors' in enhanced or isinstance(enhanced, dict):
            enhanced['error_type'] = 'VALIDATION'
            enhanced['error_category'] = 'field_validation'
        
        # Add helpful hints for common validation errors
        for field, errors in enhanced.items():
            if isinstance(errors, list) and errors:
                enhanced[f'{field}_hint'] = self._get_validation_hint(field, errors[0])
        
        return enhanced
    
    def _get_validation_hint(self, field, error_message):
        """Get helpful hint for validation error."""
        error_message = error_message.lower()
        
        if 'required' in error_message:
            return f"This field is required. Please provide a valid {field}."
        elif 'invalid' in error_message or 'valid' in error_message:
            return f"Please provide a valid {field} format."
        elif 'too long' in error_message:
            return f"This field is too long. Please provide a shorter {field}."
        elif 'too short' in error_message:
            return f"This field is too short. Please provide a longer {field}."
        elif 'email' in error_message:
            return "Please provide a valid email address."
        elif 'password' in error_message:
            return "Password must be at least 8 characters with letters and numbers."
        else:
            return f"Please check the {field} and try again."
