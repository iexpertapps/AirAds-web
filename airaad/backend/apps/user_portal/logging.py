import logging
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import connection

from .models_error import ErrorLog

# Configure structured logger
structured_logger = logging.getLogger('user_portal.structured')


class StructuredLogger:
    """
    Structured logging system for production monitoring.
    Provides consistent log formatting and context enrichment.
    """
    
    def __init__(self, service_name='user-portal'):
        self.service_name = service_name
        self.hostname = getattr(settings, 'HOSTNAME', 'unknown')
        self.environment = getattr(settings, 'ENVIRONMENT', 'production')
    
    def log(self, level: str, message: str, **kwargs):
        """
        Log a message with structured context.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **kwargs: Additional context data
        """
        # Build structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'service': self.service_name,
            'hostname': self.hostname,
            'environment': self.environment,
            'message': message,
        }
        
        # Add context data
        if kwargs:
            log_entry['context'] = kwargs
        
        # Add request context if available
        request = kwargs.pop('request', None)
        if request:
            log_entry['request'] = {
                'id': getattr(request, '_request_id', ''),
                'method': request.method,
                'path': request.path,
                'user_id': str(getattr(request.user, 'id', 'anonymous')),
            }
        
        # Add user context if available
        user = kwargs.pop('user', None)
        if user and user.is_authenticated:
            log_entry['user'] = {
                'id': str(user.id),
                'email': user.email,
            }
        
        # Log the structured entry
        log_message = json.dumps(log_entry, default=str)
        getattr(structured_logger, level.lower())(log_message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log('CRITICAL', message, **kwargs)
    
    def api_request(self, method: str, path: str, status_code: int, 
                   duration_ms: float, **kwargs):
        """Log API request with performance metrics."""
        self.info(
            f"API {method} {path}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def database_query(self, query_type: str, table: str, duration_ms: float, 
                      row_count: int = 0, **kwargs):
        """Log database query with performance metrics."""
        self.debug(
            f"DB Query: {query_type} on {table}",
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            row_count=row_count,
            **kwargs
        )
    
    def cache_operation(self, operation: str, key: str, hit: bool = None, **kwargs):
        """Log cache operation."""
        self.debug(
            f"Cache {operation}: {key}",
            operation=operation,
            key=key,
            hit=hit,
            **kwargs
        )
    
    def security_event(self, event_type: str, severity: str, **kwargs):
        """Log security event."""
        self.warning(
            f"Security Event: {event_type}",
            security_event=True,
            event_type=event_type,
            severity=severity,
            **kwargs
        )
    
    def business_event(self, event_type: str, **kwargs):
        """Log business event."""
        self.info(
            f"Business Event: {event_type}",
            business_event=True,
            event_type=event_type,
            **kwargs
        )


class ErrorAnalyzer:
    """
    Error analysis and pattern detection system.
    """
    
    def __init__(self):
        self.logger = StructuredLogger()
    
    def analyze_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error trends over the last N hours."""
        since = timezone.now() - timedelta(hours=hours)
        
        # Get error statistics
        error_stats = ErrorLog.get_error_stats(hours)
        
        # Analyze patterns
        analysis = {
            'period_hours': hours,
            'total_errors': sum(stat['count'] for stat in error_stats),
            'error_types': {},
            'severity_distribution': {},
            'top_errors': [],
            'trending_up': [],
            'trending_down': [],
        }
        
        # Group by error type
        for stat in error_stats:
            error_type = stat['error_type']
            severity = stat['severity']
            count = stat['count']
            
            if error_type not in analysis['error_types']:
                analysis['error_types'][error_type] = 0
            analysis['error_types'][error_type] += count
            
            if severity not in analysis['severity_distribution']:
                analysis['severity_distribution'][severity] = 0
            analysis['severity_distribution'][severity] += count
        
        # Sort and get top errors
        analysis['top_errors'] = sorted(
            error_stats,
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        
        # Log analysis
        self.logger.info(
            "Error trend analysis completed",
            analysis_period_hours=hours,
            total_errors=analysis['total_errors'],
            top_error_type=analysis['top_errors'][0] if analysis['top_errors'] else None
        )
        
        return analysis
    
    def detect_error_patterns(self) -> list:
        """Detect recurring error patterns."""
        patterns = []
        
        # Get recent errors
        recent_errors = ErrorLog.objects.filter(
            occurred_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        # Group by error message patterns
        error_groups = {}
        for error in recent_errors:
            # Simple pattern detection - same error type and similar message
            key = f"{error.error_type}:{error.error_message[:50]}"
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(error)
        
        # Find patterns with multiple occurrences
        for key, errors in error_groups.items():
            if len(errors) >= 3:  # Pattern threshold
                patterns.append({
                    'pattern': key,
                    'count': len(errors),
                    'first_occurrence': min(e.occurred_at for e in errors),
                    'last_occurrence': max(e.occurred_at for e in errors),
                    'severity_distribution': list(set(e.severity for e in errors)),
                })
        
        # Sort by frequency
        patterns.sort(key=lambda x: x['count'], reverse=True)
        
        # Log pattern detection
        self.logger.info(
            "Error pattern detection completed",
            patterns_found=len(patterns),
            top_pattern=patterns[0] if patterns else None
        )
        
        return patterns
    
    def get_error_health_score(self) -> Dict[str, Any]:
        """Calculate overall error health score."""
        # Get recent error statistics
        recent_stats = ErrorLog.get_error_stats(hours=1)
        hourly_stats = ErrorLog.get_error_stats(hours=24)
        
        # Calculate scores
        recent_error_count = sum(stat['count'] for stat in recent_stats)
        hourly_error_count = sum(stat['count'] for stat in hourly_stats)
        
        # Health score calculation (0-100)
        # Fewer errors = higher score
        recent_score = max(0, 100 - (recent_error_count * 10))
        hourly_score = max(0, 100 - (hourly_error_count * 2))
        
        # Critical errors have bigger impact
        critical_recent = sum(stat['count'] for stat in recent_stats 
                           if stat['severity'] == 'CRITICAL')
        critical_hourly = sum(stat['count'] for stat in hourly_stats 
                            if stat['severity'] == 'CRITICAL')
        
        recent_score = max(0, recent_score - (critical_recent * 20))
        hourly_score = max(0, hourly_score - (critical_hourly * 10))
        
        overall_score = (recent_score + hourly_score) / 2
        
        health_status = 'HEALTHY'
        if overall_score < 50:
            health_status = 'CRITICAL'
        elif overall_score < 70:
            health_status = 'WARNING'
        elif overall_score < 85:
            health_status = 'DEGRADED'
        
        return {
            'overall_score': round(overall_score, 1),
            'health_status': health_status,
            'recent_errors': recent_error_count,
            'hourly_errors': hourly_error_count,
            'critical_recent': critical_recent,
            'critical_hourly': critical_hourly,
            'timestamp': timezone.now().isoformat(),
        }


class PerformanceLogger:
    """
    Performance logging and monitoring.
    """
    
    def __init__(self):
        self.logger = StructuredLogger()
    
    def log_slow_query(self, query: str, duration_ms: float, **kwargs):
        """Log slow database query."""
        self.logger.warning(
            "Slow database query detected",
            query_type='database',
            query=query[:200],  # Truncate long queries
            duration_ms=duration_ms,
            slow_threshold_ms=1000,
            **kwargs
        )
    
    def log_slow_api(self, method: str, path: str, duration_ms: float, **kwargs):
        """Log slow API request."""
        self.logger.warning(
            "Slow API request detected",
            query_type='api',
            method=method,
            path=path,
            duration_ms=duration_ms,
            slow_threshold_ms=2000,
            **kwargs
        )
    
    def log_cache_miss(self, key: str, operation: str, **kwargs):
        """Log cache miss for optimization."""
        self.logger.debug(
            "Cache miss detected",
            query_type='cache',
            key=key,
            operation=operation,
            **kwargs
        )
    
    def log_memory_usage(self, usage_mb: float, threshold_mb: float = 500, **kwargs):
        """Log high memory usage."""
        if usage_mb > threshold_mb:
            self.logger.warning(
                "High memory usage detected",
                query_type='performance',
                memory_usage_mb=usage_mb,
                threshold_mb=threshold_mb,
                **kwargs
            )


# Global instances
structured_logger = StructuredLogger()
error_analyzer = ErrorAnalyzer()
performance_logger = PerformanceLogger()
