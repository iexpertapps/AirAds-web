from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
import uuid
import json
import traceback

User = get_user_model()


class ErrorLog(models.Model):
    """
    Centralized error logging model for production monitoring.
    Stores structured error data for analysis and alerting.
    """
    
    ERROR_TYPES = [
        ('SYSTEM', 'System Error'),
        ('DATABASE', 'Database Error'),
        ('API', 'API Error'),
        ('AUTHENTICATION', 'Authentication Error'),
        ('AUTHORIZATION', 'Authorization Error'),
        ('VALIDATION', 'Validation Error'),
        ('EXTERNAL', 'External Service Error'),
        ('PERFORMANCE', 'Performance Issue'),
        ('SECURITY', 'Security Issue'),
        ('BUSINESS', 'Business Logic Error'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Error identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error_type = models.CharField(max_length=20, choices=ERROR_TYPES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, db_index=True)
    
    # Error details
    error_message = models.TextField()
    error_code = models.CharField(max_length=50, blank=True, db_index=True)
    stack_trace = models.TextField(blank=True)
    
    # Request context
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=500, blank=True, db_index=True)
    query_params = models.JSONField(default=dict, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    
    # User context
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.EmailField(blank=True)
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # System context
    hostname = models.CharField(max_length=100, db_index=True)
    service_name = models.CharField(max_length=50, default='user-portal', db_index=True)
    environment = models.CharField(max_length=20, default='production', db_index=True)
    
    # Additional context
    context = models.JSONField(default=dict, blank=True)
    
    # Resolution tracking
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=100, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_portal_error_logs'
        indexes = [
            models.Index(fields=['error_type', 'severity', 'occurred_at']),
            models.Index(fields=['service_name', 'environment', 'occurred_at']),
            models.Index(fields=['resolved', 'occurred_at']),
            models.Index(fields=['path', 'occurred_at']),
            models.Index(fields=['user_id', 'occurred_at']),
            models.Index(fields=['error_code', 'occurred_at']),
        ]
        ordering = ['-occurred_at']
    
    def __str__(self):
        return f"{self.error_type}: {self.error_message[:100]}"
    
    @classmethod
    def log_error(cls, error_type, error_message, severity='MEDIUM', **kwargs):
        """Log an error with context."""
        from django.conf import settings
        
        # Extract context from kwargs
        request = kwargs.pop('request', None)
        user = kwargs.pop('user', None)
        stack_trace = kwargs.pop('stack_trace', None)
        
        # Build context data
        context_data = {}
        
        # Request context
        if request:
            context_data.update({
                'request_id': getattr(request, '_request_id', ''),
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': cls._get_client_ip(request),
            })
        
        # User context
        if user and user.is_authenticated:
            context_data.update({
                'user_id': str(user.id),
                'user_email': user.email,
            })
        
        # System context
        context_data.update({
            'hostname': getattr(settings, 'HOSTNAME', 'unknown'),
            'service_name': 'user-portal',
            'environment': getattr(settings, 'ENVIRONMENT', 'production'),
        })
        
        # Additional context
        if kwargs:
            context_data['additional'] = kwargs
        
        # Create error log entry
        error_log = cls.objects.create(
            error_type=error_type,
            severity=severity,
            error_message=error_message,
            error_code=kwargs.get('error_code', ''),
            stack_trace=stack_trace or traceback.format_exc(),
            occurred_at=timezone.now(),
            **context_data
        )
        
        # Trigger alert for critical errors
        if severity in ['HIGH', 'CRITICAL']:
            cls._trigger_alert(error_log)
        
        return error_log
    
    @classmethod
    def log_exception(cls, exception, request=None, user=None, **kwargs):
        """Log an exception with full context."""
        error_type = cls._classify_exception(exception)
        severity = cls._determine_severity(exception)
        
        return cls.log_error(
            error_type=error_type,
            error_message=str(exception),
            severity=severity,
            request=request,
            user=user,
            error_code=getattr(exception, 'code', ''),
            stack_trace=traceback.format_exc(),
            **kwargs
        )
    
    @staticmethod
    def _classify_exception(exception):
        """Classify exception type."""
        exception_type = type(exception).__name__
        
        # Database errors
        if 'Database' in exception_type or 'Operational' in exception_type:
            return 'DATABASE'
        
        # Authentication errors
        if 'Authentication' in exception_type or 'Permission' in exception_type:
            return 'AUTHENTICATION'
        
        # Validation errors
        if 'Validation' in exception_type or 'ValidationError' in exception_type:
            return 'VALIDATION'
        
        # API errors
        if 'API' in exception_type or 'HTTP' in exception_type:
            return 'API'
        
        # Default to system error
        return 'SYSTEM'
    
    @staticmethod
    def _determine_severity(exception):
        """Determine error severity based on exception type."""
        exception_type = type(exception).__name__
        
        # Critical errors
        if any(keyword in exception_type for keyword in ['Critical', 'Fatal', 'SystemExit']):
            return 'CRITICAL'
        
        # High severity
        if any(keyword in exception_type for keyword in ['Database', 'Connection', 'Timeout']):
            return 'HIGH'
        
        # Medium severity
        if any(keyword in exception_type for keyword in ['Validation', 'Authentication', 'Permission']):
            return 'MEDIUM'
        
        # Default to low
        return 'LOW'
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    @staticmethod
    def _trigger_alert(error_log):
        """Trigger alert for critical errors."""
        try:
            from .services import AlertService
            AlertService.send_error_alert(error_log)
        except Exception:
            # Don't let alert errors break the main flow
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send error alert: {error_log.id}")
    
    @classmethod
    def get_error_stats(cls, hours=24):
        """Get error statistics for the last N hours."""
        from django.utils import timezone
        from django.db.models import Count
        
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        return cls.objects.filter(
            occurred_at__gte=since
        ).values('error_type', 'severity').annotate(
            count=Count('id')
        ).order_by('-count')
    
    @classmethod
    def get_error_trends(cls, days=7):
        """Get error trends over the last N days."""
        from django.utils import timezone
        from django.db.models import Count
        from django.db.models.functions import TruncHour
        
        since = timezone.now() - timezone.timedelta(days=days)
        
        return cls.objects.filter(
            occurred_at__gte=since
        ).annotate(
            hour=TruncHour('occurred_at')
        ).values('hour', 'severity').annotate(
            count=Count('id')
        ).order_by('hour')


class ErrorPattern(models.Model):
    """
    Pattern matching for recurring errors.
    Helps identify and track common error patterns.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Pattern matching
    error_type = models.CharField(max_length=20, choices=ErrorLog.ERROR_TYPES)
    pattern = models.CharField(max_length=500, help_text="Regex pattern to match error messages")
    severity_threshold = models.CharField(max_length=10, choices=ErrorLog.SEVERITY_LEVELS, default='MEDIUM')
    
    # Alerting
    alert_enabled = models.BooleanField(default=True)
    alert_threshold = models.IntegerField(default=10, help_text="Alert after N occurrences in time window")
    time_window_minutes = models.IntegerField(default=60, help_text="Time window for threshold counting")
    
    # Status
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_portal_error_patterns'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def matches(self, error_log):
        """Check if error log matches this pattern."""
        import re
        
        if error_log.error_type != self.error_type:
            return False
        
        try:
            return bool(re.search(self.pattern, error_log.error_message))
        except re.error:
            return False
    
    def should_alert(self, error_log):
        """Check if we should send an alert for this error."""
        if not self.alert_enabled or not self.active:
            return False
        
        # Count occurrences in time window
        from django.utils import timezone
        since = timezone.now() - timezone.timedelta(minutes=self.time_window_minutes)
        
        count = ErrorLog.objects.filter(
            error_type=self.error_type,
            error_message__regex=self.pattern,
            occurred_at__gte=since
        ).count()
        
        return count >= self.alert_threshold
