"""
System Health Monitoring for AirAds User Portal
Comprehensive health monitoring and status reporting
"""

import time
import psutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import redis
import logging

from .models_error import ErrorLog
from .models_backup import BackupLog, RecoveryLog
from .replication_monitor import ReplicationMonitor
from .logging import structured_logger

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """
    Comprehensive system health monitoring.
    Monitors all aspects of the User Portal system.
    """
    
    def __init__(self):
        self.logger = structured_logger
        self.replication_monitor = ReplicationMonitor()
        
        # Health thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 70.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0,
            'response_time_warning': 1.0,  # seconds
            'response_time_critical': 2.0,
            'error_rate_warning': 5.0,  # errors per minute
            'error_rate_critical': 10.0,
            'replication_lag_warning': 30.0,  # seconds
            'replication_lag_critical': 300.0,
        }
    
    def get_system_health(self) -> Dict:
        """Get comprehensive system health status."""
        health_check = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'components': {},
            'alerts': [],
            'metrics': {}
        }
        
        try:
            # Check individual components
            components = {
                'application': self._check_application_health(),
                'database': self._check_database_health(),
                'cache': self._check_cache_health(),
                'storage': self._check_storage_health(),
                'network': self._check_network_health(),
                'services': self._check_services_health(),
            }
            
            health_check['components'] = components
            
            # Calculate overall status
            status_counts = {'HEALTHY': 0, 'WARNING': 0, 'CRITICAL': 0, 'DOWN': 0}
            
            for component_name, component in components.items():
                status = component.get('status', 'UNKNOWN')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Add alerts for non-healthy components
                if status in ['WARNING', 'CRITICAL', 'DOWN']:
                    health_check['alerts'].append({
                        'component': component_name,
                        'severity': status,
                        'message': component.get('message', f'{component_name} is {status}'),
                        'details': component.get('details', {})
                    })
            
            # Determine overall status
            if status_counts['CRITICAL'] > 0 or status_counts['DOWN'] > 0:
                health_check['overall_status'] = 'CRITICAL'
            elif status_counts['WARNING'] > 0:
                health_check['overall_status'] = 'WARNING'
            else:
                health_check['overall_status'] = 'HEALTHY'
            
            # Add system metrics
            health_check['metrics'] = self._get_system_metrics()
            
            self.logger.info(
                "System health check completed",
                overall_status=health_check['overall_status'],
                components_checked=len(components),
                alerts_count=len(health_check['alerts'])
            )
            
        except Exception as e:
            health_check['overall_status'] = 'ERROR'
            health_check['alerts'].append({
                'component': 'system_health',
                'severity': 'CRITICAL',
                'message': 'System health check failed',
                'details': {'error': str(e)}
            })
            
            self.logger.error("System health check failed", error=str(e))
        
        return health_check
    
    def _check_application_health(self) -> Dict:
        """Check application health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {},
            'response_time': None
        }
        
        try:
            # Test application response time
            start_time = time.time()
            
            # Simple database query to test application
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = time.time() - start_time
            health['response_time'] = response_time
            
            # Check recent errors
            recent_errors = ErrorLog.objects.filter(
                occurred_at__gte=timezone.now() - timedelta(minutes=5)
            ).count()
            
            health['details']['recent_errors'] = recent_errors
            health['details']['response_time'] = response_time
            
            # Determine status
            if response_time > self.thresholds['response_time_critical']:
                health['status'] = 'CRITICAL'
                health['message'] = f'Application response time critical: {response_time:.2f}s'
            elif response_time > self.thresholds['response_time_warning']:
                health['status'] = 'WARNING'
                health['message'] = f'Application response time slow: {response_time:.2f}s'
            elif recent_errors > self.thresholds['error_rate_critical']:
                health['status'] = 'CRITICAL'
                health['message'] = f'High error rate: {recent_errors} errors in last 5 minutes'
            elif recent_errors > self.thresholds['error_rate_warning']:
                health['status'] = 'WARNING'
                health['message'] = f'Elevated error rate: {recent_errors} errors in last 5 minutes'
            else:
                health['status'] = 'HEALTHY'
                health['message'] = 'Application is healthy'
            
        except Exception as e:
            health['status'] = 'DOWN'
            health['message'] = f'Application health check failed: {str(e)}'
            health['details']['error'] = str(e)
        
        return health
    
    def _check_database_health(self) -> Dict:
        """Check database health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {}
        }
        
        try:
            # Test database connectivity
            with connection.cursor() as cursor:
                # Check connection
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Get connection count
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
                
                # Check database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                db_size = cursor.fetchone()[0]
                
                # Check replication status
                cursor.execute("SELECT pg_is_in_recovery()")
                in_recovery = cursor.fetchone()[0]
                
                if in_recovery:
                    cursor.execute("""
                        SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
                    """)
                    lag_result = cursor.fetchone()
                    replication_lag = lag_result[0] if lag_result and lag_result[0] else 0
                else:
                    replication_lag = 0
                
                health['details'] = {
                    'active_connections': active_connections,
                    'database_size': db_size,
                    'in_recovery': in_recovery,
                    'replication_lag': replication_lag
                }
                
                # Determine status
                if replication_lag > self.thresholds['replication_lag_critical']:
                    health['status'] = 'CRITICAL'
                    health['message'] = f'Database replication lag critical: {replication_lag:.1f}s'
                elif replication_lag > self.thresholds['replication_lag_warning']:
                    health['status'] = 'WARNING'
                    health['message'] = f'Database replication lag elevated: {replication_lag:.1f}s'
                else:
                    health['status'] = 'HEALTHY'
                    health['message'] = 'Database is healthy'
            
        except Exception as e:
            health['status'] = 'DOWN'
            health['message'] = f'Database health check failed: {str(e)}'
            health['details']['error'] = str(e)
        
        return health
    
    def _check_cache_health(self) -> Dict:
        """Check cache (Redis) health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {}
        }
        
        try:
            # Test Redis connectivity
            redis_client = redis.Redis(
                host=settings.CACHES['default']['LOCATION'].split(':')[0],
                port=int(settings.CACHES['default']['LOCATION'].split(':')[1]),
                db=int(settings.CACHES['default']['LOCATION'].split('/')[2] if '/' in settings.CACHES['default']['LOCATION'] else 0),
                socket_timeout=5
            )
            
            # Ping test
            pong = redis_client.ping()
            
            if pong:
                # Get Redis info
                info = redis_client.info()
                
                used_memory = info.get('used_memory', 0)
                max_memory = info.get('maxmemory', 0)
                connected_clients = info.get('connected_clients', 0)
                keyspace_hits = info.get('keyspace_hits', 0)
                keyspace_misses = info.get('keyspace_misses', 0)
                
                # Calculate hit rate
                total_requests = keyspace_hits + keyspace_misses
                hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 0
                
                # Calculate memory usage percentage
                memory_usage_percent = (used_memory / max_memory * 100) if max_memory > 0 else 0
                
                health['details'] = {
                    'connected_clients': connected_clients,
                    'used_memory': used_memory,
                    'max_memory': max_memory,
                    'memory_usage_percent': memory_usage_percent,
                    'hit_rate': hit_rate,
                    'keyspace_hits': keyspace_hits,
                    'keyspace_misses': keyspace_misses
                }
                
                # Determine status
                if memory_usage_percent > 90:
                    health['status'] = 'CRITICAL'
                    health['message'] = f'Redis memory usage critical: {memory_usage_percent:.1f}%'
                elif memory_usage_percent > 80:
                    health['status'] = 'WARNING'
                    health['message'] = f'Redis memory usage high: {memory_usage_percent:.1f}%'
                elif hit_rate < 50:
                    health['status'] = 'WARNING'
                    health['message'] = f'Redis hit rate low: {hit_rate:.1f}%'
                else:
                    health['status'] = 'HEALTHY'
                    health['message'] = 'Cache is healthy'
            else:
                health['status'] = 'DOWN'
                health['message'] = 'Cache ping failed'
            
        except Exception as e:
            health['status'] = 'DOWN'
            health['message'] = f'Cache health check failed: {str(e)}'
            health['details']['error'] = str(e)
        
        return health
    
    def _check_storage_health(self) -> Dict:
        """Check storage health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {}
        }
        
        try:
            # Check disk usage
            disk_usage = psutil.disk_usage('/')
            
            total = disk_usage.total
            used = disk_usage.used
            free = disk_usage.free
            usage_percent = (used / total) * 100
            
            health['details'] = {
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': free,
                'usage_percent': usage_percent
            }
            
            # Determine status
            if usage_percent > self.thresholds['disk_critical']:
                health['status'] = 'CRITICAL'
                health['message'] = f'Disk usage critical: {usage_percent:.1f}%'
            elif usage_percent > self.thresholds['disk_warning']:
                health['status'] = 'WARNING'
                health['message'] = f'Disk usage high: {usage_percent:.1f}%'
            else:
                health['status'] = 'HEALTHY'
                health['message'] = 'Storage is healthy'
            
        except Exception as e:
            health['status'] = 'ERROR'
            health['message'] = f'Storage health check failed: {str(e)}'
            health['details']['error'] = str(e)
        
        return health
    
    def _check_network_health(self) -> Dict:
        """Check network health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {}
        }
        
        try:
            # Check network interfaces
            network_io = psutil.net_io_counters()
            
            # Check active connections
            connections = len(psutil.net_connections())
            
            health['details'] = {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv,
                'active_connections': connections
            }
            
            # Simple connectivity test (ping external service)
            try:
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                internet_connected = True
            except:
                internet_connected = False
            
            health['details']['internet_connected'] = internet_connected
            
            # Determine status
            if not internet_connected:
                health['status'] = 'CRITICAL'
                health['message'] = 'No internet connectivity'
            else:
                health['status'] = 'HEALTHY'
                health['message'] = 'Network is healthy'
            
        except Exception as e:
            health['status'] = 'ERROR'
            health['message'] = f'Network health check failed: {str(e)}'
            health['details']['error'] = str(e)
        
        return health
    
    def _check_services_health(self) -> Dict:
        """Check system services health."""
        health = {
            'status': 'UNKNOWN',
            'message': '',
            'details': {}
        }
        
        services_to_check = ['nginx', 'gunicorn', 'redis', 'postgresql']
        service_status = {}
        
        for service in services_to_check:
            try:
                # Check if service is running
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                status = result.stdout.strip()
                service_status[service] = {
                    'status': status,
                    'active': status == 'active'
                }
                
            except subprocess.TimeoutExpired:
                service_status[service] = {
                    'status': 'timeout',
                    'active': False
                }
            except Exception as e:
                service_status[service] = {
                    'status': 'error',
                    'active': False,
                    'error': str(e)
                }
        
        health['details'] = service_status
        
        # Determine overall status
        active_services = sum(1 for s in service_status.values() if s.get('active', False))
        total_services = len(services_to_check)
        
        if active_services == 0:
            health['status'] = 'CRITICAL'
            health['message'] = f'No services active ({active_services}/{total_services})'
        elif active_services < total_services:
            health['status'] = 'WARNING'
            health['message'] = f'Some services down ({active_services}/{total_services})'
        else:
            health['status'] = 'HEALTHY'
            health['message'] = 'All services healthy'
        
        return health
    
    def _get_system_metrics(self) -> Dict:
        """Get system performance metrics."""
        metrics = {}
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg()
            
            metrics['cpu'] = {
                'usage_percent': cpu_percent,
                'core_count': cpu_count,
                'load_1min': load_avg[0],
                'load_5min': load_avg[1],
                'load_15min': load_avg[2]
            }
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics['memory'] = {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'free': memory.free,
                'percent': memory.percent,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent
            }
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            metrics['disk'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
            
            # Network metrics
            network = psutil.net_io_counters()
            
            metrics['network'] = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Process metrics
            process = psutil.Process()
            
            metrics['process'] = {
                'pid': process.pid,
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            }
            
        except Exception as e:
            metrics['error'] = str(e)
            self.logger.error("Failed to get system metrics", error=str(e))
        
        return metrics
    
    def get_health_summary(self) -> Dict:
        """Get simplified health summary for quick checks."""
        full_health = self.get_system_health()
        
        summary = {
            'timestamp': full_health['timestamp'],
            'overall_status': full_health['overall_status'],
            'component_count': len(full_health['components']),
            'healthy_components': sum(1 for c in full_health['components'].values() if c.get('status') == 'HEALTHY'),
            'alert_count': len(full_health['alerts']),
            'critical_alerts': len([a for a in full_health['alerts'] if a['severity'] == 'CRITICAL']),
            'warning_alerts': len([a for a in full_health['alerts'] if a['severity'] == 'WARNING'])
        }
        
        return summary


# Global health monitor instance
system_health_monitor = SystemHealthMonitor()
