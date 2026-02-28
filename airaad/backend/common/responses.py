from rest_framework import status
from rest_framework.response import Response
from typing import Any, Dict, Optional


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    meta: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Standard success response format.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        meta: Additional metadata
        
    Returns:
        Formatted DRF Response
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data,
    }
    
    if meta:
        response_data['meta'] = meta
    
    return Response(response_data, status=status_code)


def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    errors: Optional[Dict[str, Any]] = None,
    details: Optional[str] = None,
    error_id: Optional[str] = None
) -> Response:
    """
    Standard error response format.
    
    Args:
        message: Error message
        status_code: HTTP status code
        errors: Field-specific errors
        details: Additional error details
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response
    """
    response_data = {
        'success': False,
        'message': message,
        'error_code': status_code,
    }
    
    if errors:
        response_data['errors'] = errors
    
    if details:
        response_data['details'] = details
    
    if error_id:
        response_data['error_id'] = error_id
    
    return Response(response_data, status=status_code)


def paginated_response(
    data: Any,
    count: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "Data retrieved successfully",
    **kwargs
) -> Response:
    """
    Standard paginated response format.
    
    Args:
        data: Response data
        count: Total number of items
        page: Current page number
        page_size: Items per page
        message: Success message
        **kwargs: Additional metadata
        
    Returns:
        Formatted DRF Response with pagination info
    """
    total_pages = (count + page_size - 1) // page_size
    
    meta = {
        'pagination': {
            'page': page,
            'page_size': page_size,
            'count': count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }
    }
    
    # Add any additional metadata
    meta.update(kwargs)
    
    return success_response(
        data=data,
        message=message,
        meta=meta
    )


def validation_error_response(
    errors: Dict[str, Any],
    message: str = "Validation failed",
    error_id: Optional[str] = None
) -> Response:
    """
    Standard validation error response.
    
    Args:
        errors: Validation errors
        message: Error message
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response for validation errors
    """
    return error_response(
        message=message,
        status_code=status.HTTP_400_BAD_REQUEST,
        errors=errors,
        error_id=error_id
    )


def not_found_response(
    message: str = "Resource not found",
    error_id: Optional[str] = None
) -> Response:
    """
    Standard not found response.
    
    Args:
        message: Error message
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response for 404 errors
    """
    return error_response(
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
        error_id=error_id
    )


def unauthorized_response(
    message: str = "Unauthorized access",
    error_id: Optional[str] = None
) -> Response:
    """
    Standard unauthorized response.
    
    Args:
        message: Error message
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response for 401 errors
    """
    return error_response(
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
        error_id=error_id
    )


def forbidden_response(
    message: str = "Access forbidden",
    error_id: Optional[str] = None
) -> Response:
    """
    Standard forbidden response.
    
    Args:
        message: Error message
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response for 403 errors
    """
    return error_response(
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
        error_id=error_id
    )


def server_error_response(
    message: str = "Internal server error",
    error_id: Optional[str] = None
) -> Response:
    """
    Standard server error response.
    
    Args:
        message: Error message
        error_id: Error tracking ID
        
    Returns:
        Formatted DRF Response for 500 errors
    """
    return error_response(
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_id=error_id
    )
