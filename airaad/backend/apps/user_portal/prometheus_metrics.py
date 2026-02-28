"""
Prometheus Metrics Collection for AirAds User Portal
Comprehensive metrics collection for monitoring and alerting
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import logging

try:
    import psutil
except ImportError:
    psutil = None

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
except ImportError:
    Counter = Histogram = Gauge = Info = CollectorRegistry = generate_latest = None

try:
    import redis
except ImportError:
    redis = None

from .models_error import ErrorLog
from .models_backup import BackupLog, RecoveryLog
from .logging import structured_logger

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus metrics collection system.
    Provides comprehensive metrics for monitoring the User Portal.
    """
    
    def __init__(self):
        self.logger = structured_logger
        
        if CollectorRegistry is None:
            self.registry = None
            logger.warning("prometheus_client not installed — metrics collection disabled")
            return
        
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # Application info
        self.app_info = Info(
            'user_portal_info',
            'User Portal application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': getattr(settings, 'APP_VERSION', '1.0.0'),
            'environment': getattr(settings, 'ENVIRONMENT', 'production'),
            'service': 'user-portal'
        })
        
        # HTTP metrics
        self.http_requests_total = Counter(
            'user_portal_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'user_portal_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            'user_portal_db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'user_portal_db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
            registry=self.registry
        )
        
        self.db_queries_total = Counter(
            'user_portal_db_queries_total',
            'Total database queries',
            ['operation', 'table'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations_total = Counter(
            'user_portal_cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'user_portal_cache_size_bytes',
            'Cache size in bytes',
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'user_portal_errors_total',
            'Total errors',
            ['error_type', 'severity'],
            registry=self.registry
        )
        
        self.error_rate = Gauge(
            'user_portal_error_rate',
            'Error rate (errors per minute)',
            registry=self.registry
        )
        
        # Business metrics
        self.active_users = Gauge(
            'user_portal_active_users',
            'Number of active users',
            ['user_type'],
            registry=self.registry
        )
        
        self.vendor_interactions_total = Counter(
            'user_portal_vendor_interactions_total',
            'Total vendor interactions',
            ['interaction_type'],
            registry=self.registry
        )
        
        self.search_queries_total = Counter(
            'user_portal_search_queries_total',
            'Total search queries',
            ['query_type'],
            registry=self.registry
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'user_portal_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'user_portal_system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'user_portal_system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )
        
        # Backup metrics
        self.backup_duration = Histogram(
            'user_portal_backup_duration_seconds',
            'Backup duration in seconds',
            ['backup_type'],
            buckets=[60, 300, 900, 1800, 3600, 7200],
            registry=self.registry
        )
        
        self.backup_size = Histogram(
            'user_portal_backup_size_bytes',
            'Backup size in bytes',
            ['backup_type'],
            buckets=[1000000, 10000000, 100000000, 1000000000, 10000000000],
            registry=self.registry
        )
        
        self.backup_success_rate = Gauge(
            'user_portal_backup_success_rate',
            'Backup success rate',
            ['backup_type'],
            registry=self.registry
        )
        
        # Redis metrics
        self.redis_connections = Gauge(
            'user_portal_redis_connections',
            'Redis connections',
            registry=self.registry
        )
        
        self.redis_memory_usage = Gauge(
            'user_portal_redis_memory_usage_bytes',
            'Redis memory usage in bytes',
            registry=self.registry
        )
        
        self.redis_keys = Gauge(
            'user_portal_redis_keys',
            'Number of Redis keys',
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if self.registry is None:
            return
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        if self.registry is None:
            return
        self.db_query_duration.labels(operation=operation).observe(duration)
        self.db_queries_total.labels(operation=operation, table=table).inc()
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation metrics."""
        if self.registry is None:
            return
        self.cache_operations_total.labels(operation=operation, result=result).inc()
    
    def record_error(self, error_type: str, severity: str):
        """Record error metrics."""
        if self.registry is None:
            return
        self.errors_total.labels(error_type=error_type, severity=severity).inc()
    
    def record_vendor_interaction(self, interaction_type: str):
        """Record vendor interaction metrics."""
        if self.registry is None:
            return
        self.vendor_interactions_total.labels(interaction_type=interaction_type).inc()
    
    def record_search_query(self, query_type: str):
        """Record search query metrics."""
        if self.registry is None:
            return
        self.search_queries_total.labels(query_type=query_type).inc()
    
    def record_backup(self, backup_type: str, duration: float, size: int, success: bool):
        """Record backup metrics."""
        if self.registry is None:
            return
        self.backup_duration.labels(backup_type=backup_type).observe(duration)
        self.backup_size.labels(backup_type=backup_type).observe(size)
        
        # Update success rate
        self._update_backup_success_rate(backup_type)
    
    def update_system_metrics(self):
        """Update system metrics."""
        if self.registry is None or psutil is None:
            return
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.system_disk_usage.set((disk.used / disk.total) * 100)
            
        except Exception as e:
            self.logger.error("Failed to update system metrics", error=str(e))
    
    def update_database_metrics(self):
        """Update database metrics."""
        if self.registry is None:
            return
        try:
            # Active connections
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
                self.db_connections_active.set(active_connections)
                
        except Exception as e:
            self.logger.error("Failed to update database metrics", error=str(e))
    
    def update_cache_metrics(self):
        """Update cache metrics."""
        if self.registry is None or redis is None:
            return
        try:
            # Get Redis info — parse URL format (redis://host:port/db)
            from urllib.parse import urlparse
            _redis_url = settings.CACHES['default'].get('LOCATION', 'redis://localhost:6379/0')
            _parsed = urlparse(_redis_url)
            redis_client = redis.Redis(
                host=_parsed.hostname or 'localhost',
                port=_parsed.port or 6379,
                db=int(_parsed.path.lstrip('/') or 0)
            )
            
            info = redis_client.info()
            
            # Redis connections
            self.redis_connections.set(info.get('connected_clients', 0))
            
            # Redis memory usage
            self.redis_memory_usage.set(info.get('used_memory', 0))
            
            # Redis keys
            self.redis_keys.set(info.get('db0', {}).get('keys', 0))
            
            # Cache size (approximate)
            self.cache_size.set(info.get('used_memory', 0))
            
        except Exception as e:
            self.logger.error("Failed to update cache metrics", error=str(e))
    
    def update_business_metrics(self):
        """Update business metrics."""
        if self.registry is None:
            return
        try:
            from apps.customer_auth.models import CustomerUser
            from apps.user_preferences.models import UserVendorInteraction, UserSearchHistory
            
            # Active users (last 24 hours)
            yesterday = timezone.now() - timedelta(days=1)
            
            # Registered users active in last 24h
            registered_active = CustomerUser.objects.filter(
                user__last_login__gte=yesterday
            ).count()
            
            # Guest users active in last 24h
            guest_active = UserVendorInteraction.objects.filter(
                user=None,
                interacted_at__gte=yesterday
            ).values('session_id').distinct().count()
            
            self.active_users.labels(user_type='registered').set(registered_active)
            self.active_users.labels(user_type='guest').set(guest_active)
            
            # Error rate (last hour)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            error_count = ErrorLog.objects.filter(occurred_at__gte=one_hour_ago).count()
            self.error_rate.set(error_count)
            
        except Exception as e:
            self.logger.error("Failed to update business metrics", error=str(e))
    
    def _update_backup_success_rate(self, backup_type: str):
        """Update backup success rate for a specific backup type."""
        try:
            # Get last 7 days of backups
            seven_days_ago = timezone.now() - timedelta(days=7)
            
            total_backups = BackupLog.objects.filter(
                backup_type=backup_type,
                started_at__gte=seven_days_ago
            ).count()
            
            if total_backups > 0:
                successful_backups = BackupLog.objects.filter(
                    backup_type=backup_type,
                    started_at__gte=seven_days_ago,
                    success=True
                ).count()
                
                success_rate = (successful_backups / total_backups) * 100
                self.backup_success_rate.labels(backup_type=backup_type).set(success_rate)
            
        except Exception as e:
            self.logger.error("Failed to update backup success rate", error=str(e))
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        if self.registry is None:
            return '# prometheus_client not installed\n'
        # Update all dynamic metrics
        self.update_system_metrics()
        self.update_database_metrics()
        self.update_cache_metrics()
        self.update_business_metrics()
        
        # Generate metrics
        return generate_latest(self.registry).decode('utf-8')
    
    def start_metrics_collection(self):
        """Start continuous metrics collection."""
        self.logger.info("Starting Prometheus metrics collection")
        
        # This would typically be run in a background thread or separate process
        # For now, metrics are updated on-demand when get_metrics() is called


class MetricsMiddleware:
    """
    Django middleware for collecting HTTP request metrics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.metrics = PrometheusMetrics()
    
    def __call__(self, request):
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        endpoint = self._get_endpoint(request)
        self.metrics.record_http_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration=duration
        )
        
        return response
    
    def _get_endpoint(self, request) -> str:
        """Extract endpoint from request."""
        # Remove query parameters and API version
        path = request.path
        
        # Remove API version prefix
        if path.startswith('/api/user-portal/v1/'):
            path = path.replace('/api/user-portal/v1', '')
        
        # Replace UUIDs with placeholder
        import re
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/:id', path)
        
        return path or '/'


class DatabaseQueryMiddleware:
    """
    Django middleware for collecting database query metrics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.metrics = PrometheusMetrics()
    
    def __call__(self, request):
        # Store original cursor execute method
        original_execute = connection.cursor
        
        def cursor_execute_wrapper():
            cursor = original_execute()
            original_execute_method = cursor.execute
            
            def execute_wrapper(sql, params=None):
                start_time = time.time()
                try:
                    result = original_execute_method(sql, params)
                    duration = time.time() - start_time
                    
                    # Extract table name and operation
                    operation, table = self._parse_query(sql)
                    if operation and table:
                        self.metrics.record_db_query(operation, table, duration)
                    
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_db_query('ERROR', 'unknown', duration)
                    raise
            
            cursor.execute = execute_wrapper
            return cursor
        
        # Monkey patch for the duration of the request
        connection.cursor = cursor_execute_wrapper
        
        try:
            response = self.get_response(request)
        finally:
            # Restore original method
            connection.cursor = original_execute
        
        return response
    
    def _parse_query(self, sql: str) -> tuple:
        """Parse SQL to extract operation and table name."""
        sql_upper = sql.upper().strip()
        
        # Extract operation
        operation = None
        for op in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            if sql_upper.startswith(op):
                operation = op.lower()
                break
        
        # Extract table name (simplified)
        table = 'unknown'
        if operation == 'select':
            if 'FROM' in sql_upper:
                from_part = sql_upper.split('FROM')[1].strip()
                table = from_part.split()[0].strip('"')
        elif operation in ['insert', 'update', 'delete']:
            if sql_upper.startswith(operation.upper()):
                rest = sql_upper[len(operation):].strip()
                if rest.startswith('INTO'):
                    table = rest.replace('INTO', '').strip().split()[0].strip('"')
                elif rest.startswith(''):
                    table = rest.split()[0].strip('"')
        
        return operation, table


# Global metrics instance
prometheus_metrics = PrometheusMetrics()
