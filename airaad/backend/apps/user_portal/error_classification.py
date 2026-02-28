from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache
import logging

from .logging import structured_logger

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error type classification."""
    SYSTEM = 'SYSTEM'
    DATABASE = 'DATABASE'
    API = 'API'
    AUTHENTICATION = 'AUTHENTICATION'
    AUTHORIZATION = 'AUTHORIZATION'
    VALIDATION = 'VALIDATION'
    EXTERNAL = 'EXTERNAL'
    PERFORMANCE = 'PERFORMANCE'
    SECURITY = 'SECURITY'
    BUSINESS = 'BUSINESS'


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


@dataclass
class ErrorClassification:
    """Error classification result."""
    error_type: ErrorType
    severity: ErrorSeverity
    category: str
    is_recoverable: bool
    suggested_action: str
    alert_threshold: int = 5
    auto_recovery_possible: bool = False


class ErrorClassifier:
    """
    Error classification system.
    Classifies errors by type, severity, and provides recovery suggestions.
    """
    
    def __init__(self):
        self.classification_rules = self._build_classification_rules()
        self.severity_rules = self._build_severity_rules()
    
    def classify_exception(self, exception: Exception, context: Dict[str, Any] = None) -> ErrorClassification:
        """
        Classify an exception with context.
        
        Args:
            exception: The exception to classify
            context: Additional context for classification
            
        Returns:
            ErrorClassification with detailed classification
        """
        context = context or {}
        exception_name = type(exception).__name__
        exception_message = str(exception)
        
        # Determine error type
        error_type = self._classify_error_type(exception_name, exception_message, context)
        
        # Determine severity
        severity = self._classify_severity(exception_name, exception_message, context)
        
        # Determine category
        category = self._determine_category(error_type, exception_name, context)
        
        # Determine recoverability
        is_recoverable = self._is_recoverable(error_type, severity, context)
        
        # Suggest action
        suggested_action = self._suggest_action(error_type, severity, context)
        
        # Check auto-recovery
        auto_recovery = self._can_auto_recover(error_type, severity, context)
        
        # Determine alert threshold
        alert_threshold = self._get_alert_threshold(error_type, severity)
        
        classification = ErrorClassification(
            error_type=error_type,
            severity=severity,
            category=category,
            is_recoverable=is_recoverable,
            suggested_action=suggested_action,
            alert_threshold=alert_threshold,
            auto_recovery_possible=auto_recovery
        )
        
        # Log classification
        structured_logger.debug(
            "Error classified",
            error_type=error_type.value,
            severity=severity.value,
            category=category,
            recoverable=is_recoverable,
            exception_name=exception_name,
            exception_message=exception_message[:100]
        )
        
        return classification
    
    def _classify_error_type(self, exception_name: str, exception_message: str, context: Dict[str, Any]) -> ErrorType:
        """Classify error type based on exception and context."""
        exception_lower = exception_name.lower()
        message_lower = exception_message.lower()
        
        # Database errors
        if any(keyword in exception_lower for keyword in ['database', 'db', 'sql', 'operational', 'integrity']):
            return ErrorType.DATABASE
        
        # Authentication errors
        if any(keyword in exception_lower for keyword in ['authentication', 'auth', 'login', 'credential']):
            return ErrorType.AUTHENTICATION
        
        # Authorization errors
        if any(keyword in exception_lower for keyword in ['permission', 'forbidden', 'unauthorized', 'access']):
            return ErrorType.AUTHORIZATION
        
        # Validation errors
        if any(keyword in exception_lower for keyword in ['validation', 'invalid', 'required', 'format']):
            return ErrorType.VALIDATION
        
        # API errors
        if any(keyword in exception_lower for keyword in ['api', 'http', 'response', 'request']):
            return ErrorType.API
        
        # Performance errors
        if any(keyword in exception_lower for keyword in ['timeout', 'slow', 'performance', 'memory']):
            return ErrorType.PERFORMANCE
        
        # Security errors
        if any(keyword in exception_lower for keyword in ['security', 'csrf', 'xss', 'injection']):
            return ErrorType.SECURITY
        
        # External service errors
        if context.get('external_service') or 'external' in message_lower:
            return ErrorType.EXTERNAL
        
        # Default to system error
        return ErrorType.SYSTEM
    
    def _classify_severity(self, exception_name: str, exception_message: str, context: Dict[str, Any]) -> ErrorSeverity:
        """Classify error severity."""
        exception_lower = exception_name.lower()
        message_lower = exception_message.lower()
        
        # Critical errors
        if any(keyword in exception_lower for keyword in ['critical', 'fatal', 'systemexit']):
            return ErrorSeverity.CRITICAL
        
        # High severity
        if any(keyword in exception_lower for keyword in ['database', 'connection', 'timeout', 'security']):
            return ErrorSeverity.HIGH
        
        # Medium severity
        if any(keyword in exception_lower for keyword in ['authentication', 'authorization', 'api', 'performance']):
            return ErrorSeverity.MEDIUM
        
        # Low severity
        if any(keyword in exception_lower for keyword in ['validation', 'format', 'required']):
            return ErrorSeverity.LOW
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _determine_category(self, error_type: ErrorType, exception_name: str, context: Dict[str, Any]) -> str:
        """Determine error category for better organization."""
        if error_type == ErrorType.DATABASE:
            if 'connection' in exception_name.lower():
                return 'database_connection'
            elif 'integrity' in exception_name.lower():
                return 'database_integrity'
            else:
                return 'database_query'
        
        elif error_type == ErrorType.API:
            if context.get('method') == 'GET':
                return 'api_read'
            elif context.get('method') in ['POST', 'PUT', 'PATCH']:
                return 'api_write'
            else:
                return 'api_general'
        
        elif error_type == ErrorType.AUTHENTICATION:
            return 'user_authentication'
        
        elif error_type == ErrorType.AUTHORIZATION:
            return 'user_authorization'
        
        elif error_type == ErrorType.VALIDATION:
            return 'input_validation'
        
        elif error_type == ErrorType.PERFORMANCE:
            if 'timeout' in exception_name.lower():
                return 'timeout'
            else:
                return 'performance'
        
        else:
            return 'general'
    
    def _is_recoverable(self, error_type: ErrorType, severity: ErrorSeverity, context: Dict[str, Any]) -> bool:
        """Determine if error is recoverable."""
        # Critical errors are not recoverable
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        # Validation errors are recoverable
        if error_type == ErrorType.VALIDATION:
            return True
        
        # Authentication errors might be recoverable with retry
        if error_type == ErrorType.AUTHENTICATION:
            return True
        
        # Some database errors are recoverable
        if error_type == ErrorType.DATABASE:
            if context.get('error_category') == 'database_connection':
                return True
            elif context.get('error_category') == 'database_query':
                return True
        
        # Performance errors might be recoverable with retry
        if error_type == ErrorType.PERFORMANCE:
            return context.get('error_category') == 'timeout'
        
        # Default to not recoverable
        return False
    
    def _suggest_action(self, error_type: ErrorType, severity: ErrorSeverity, context: Dict[str, Any]) -> str:
        """Suggest action for error recovery."""
        if error_type == ErrorType.DATABASE:
            if context.get('error_category') == 'database_connection':
                return "Retry with exponential backoff, check database connectivity"
            else:
                return "Review query logic, check data integrity"
        
        elif error_type == ErrorType.AUTHENTICATION:
            return "Refresh authentication token, re-authenticate user"
        
        elif error_type == ErrorType.AUTHORIZATION:
            return "Check user permissions, verify access rights"
        
        elif error_type == ErrorType.VALIDATION:
            return "Validate input data, check required fields"
        
        elif error_type == ErrorType.API:
            return "Check API endpoint, verify request format"
        
        elif error_type == ErrorType.PERFORMANCE:
            return "Optimize query, increase timeout, check resources"
        
        elif error_type == ErrorType.SECURITY:
            return "Review security settings, check for vulnerabilities"
        
        else:
            return "Review system logs, check application state"
    
    def _can_auto_recover(self, error_type: ErrorType, severity: ErrorSeverity, context: Dict[str, Any]) -> bool:
        """Determine if error can be auto-recovered."""
        # Only low and medium severity errors can be auto-recovered
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return False
        
        # Validation errors can be auto-recovered with default values
        if error_type == ErrorType.VALIDATION:
            return True
        
        # Some database connection errors can be auto-recovered
        if error_type == ErrorType.DATABASE and context.get('error_category') == 'database_connection':
            return True
        
        # Timeout errors can be auto-recovered with retry
        if error_type == ErrorType.PERFORMANCE and context.get('error_category') == 'timeout':
            return True
        
        return False
    
    def _get_alert_threshold(self, error_type: ErrorType, severity: ErrorSeverity) -> int:
        """Get alert threshold for error type and severity."""
        base_thresholds = {
            ErrorSeverity.LOW: 20,
            ErrorSeverity.MEDIUM: 10,
            ErrorSeverity.HIGH: 5,
            ErrorSeverity.CRITICAL: 1,
        }
        
        # Adjust thresholds based on error type
        type_multipliers = {
            ErrorType.DATABASE: 0.5,  # Database errors are more important
            ErrorType.SECURITY: 0.3,  # Security errors are very important
            ErrorType.PERFORMANCE: 0.7,  # Performance errors are moderately important
            ErrorType.VALIDATION: 2.0,  # Validation errors are less important
        }
        
        base_threshold = base_thresholds.get(severity, 10)
        multiplier = type_multipliers.get(error_type, 1.0)
        
        return max(1, int(base_threshold * multiplier))
    
    def _build_classification_rules(self) -> Dict[str, Any]:
        """Build classification rules for different error types."""
        return {
            'database': {
                'keywords': ['database', 'db', 'sql', 'operational', 'integrity'],
                'severity_adjustment': 1.5,
            },
            'authentication': {
                'keywords': ['authentication', 'auth', 'login', 'credential'],
                'severity_adjustment': 1.0,
            },
            'authorization': {
                'keywords': ['permission', 'forbidden', 'unauthorized', 'access'],
                'severity_adjustment': 1.0,
            },
            'validation': {
                'keywords': ['validation', 'invalid', 'required', 'format'],
                'severity_adjustment': 0.5,
            },
            'api': {
                'keywords': ['api', 'http', 'response', 'request'],
                'severity_adjustment': 1.0,
            },
            'performance': {
                'keywords': ['timeout', 'slow', 'performance', 'memory'],
                'severity_adjustment': 1.2,
            },
            'security': {
                'keywords': ['security', 'csrf', 'xss', 'injection'],
                'severity_adjustment': 2.0,
            },
        }
    
    def _build_severity_rules(self) -> Dict[str, Any]:
        """Build severity rules for different error types."""
        return {
            'critical_keywords': ['critical', 'fatal', 'systemexit'],
            'high_keywords': ['database', 'connection', 'timeout', 'security'],
            'medium_keywords': ['authentication', 'authorization', 'api', 'performance'],
            'low_keywords': ['validation', 'format', 'required'],
        }


class ErrorMetrics:
    """
    Error metrics collection and analysis.
    """
    
    def __init__(self):
        self.classifier = ErrorClassifier()
    
    def get_error_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        from .models_error import ErrorLog
        from django.utils import timezone
        from django.db.models import Count
        
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        # Basic error counts
        total_errors = ErrorLog.objects.filter(occurred_at__gte=since).count()
        
        # Error type distribution
        type_distribution = ErrorLog.objects.filter(
            occurred_at__gte=since
        ).values('error_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Severity distribution
        severity_distribution = ErrorLog.objects.filter(
            occurred_at__gte=since
        ).values('severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Top error messages
        top_errors = ErrorLog.objects.filter(
            occurred_at__gte=since
        ).values('error_message').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Error trends (hourly)
        hourly_trends = ErrorLog.objects.filter(
            occurred_at__gte=since
        ).extra({
            'hour': "strftime('%%Y-%%m-%%d %%H:00:00', occurred_at)"
        }).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return {
            'period_hours': hours,
            'total_errors': total_errors,
            'type_distribution': list(type_distribution),
            'severity_distribution': list(severity_distribution),
            'top_errors': list(top_errors),
            'hourly_trends': list(hourly_trends),
        }
    
    def get_error_health_metrics(self) -> Dict[str, Any]:
        """Get error health metrics."""
        metrics_1h = self.get_error_metrics(hours=1)
        metrics_24h = self.get_error_metrics(hours=24)
        
        # Calculate error rate
        error_rate_1h = metrics_1h['total_errors']
        error_rate_24h = metrics_24h['total_errors'] / 24  # Per hour average
        
        # Calculate health score
        health_score = self._calculate_health_score(error_rate_1h, error_rate_24h)
        
        return {
            'error_rate_1h': error_rate_1h,
            'error_rate_24h_avg': error_rate_24h,
            'health_score': health_score,
            'health_status': self._get_health_status(health_score),
            'timestamp': timezone.now().isoformat(),
        }
    
    def _calculate_health_score(self, error_rate_1h: int, error_rate_24h_avg: float) -> float:
        """Calculate health score based on error rates."""
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for recent errors
        score -= error_rate_1h * 2  # Recent errors have more impact
        score -= error_rate_24h_avg * 0.5  # Historical errors have less impact
        
        # Ensure score doesn't go below 0
        return max(0.0, score)
    
    def _get_health_status(self, health_score: float) -> str:
        """Get health status based on health score."""
        if health_score >= 90:
            return 'EXCELLENT'
        elif health_score >= 75:
            return 'GOOD'
        elif health_score >= 60:
            return 'FAIR'
        elif health_score >= 40:
            return 'POOR'
        else:
            return 'CRITICAL'


# Global instances
error_classifier = ErrorClassifier()
error_metrics = ErrorMetrics()
