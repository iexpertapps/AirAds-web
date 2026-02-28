"""
Real-time Replication Monitoring for AirAds User Portal
Monitors database replication lag, Redis replication status, and data consistency
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psycopg2
import redis
from redis import Redis
import django

# Setup Django environment
import os
import sys
sys.path.append('/Users/syedsmacbook/Developer/AirAds-web/airaad/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.user_portal.models_backup import BackupLog, RecoveryLog
from apps.user_portal.logging import structured_logger
from django.conf import settings
from django.utils import timezone


class ReplicationMonitor:
    """
    Real-time replication monitoring system.
    Monitors PostgreSQL replication, Redis replication, and data consistency.
    """
    
    def __init__(self):
        self.logger = structured_logger
        
        # Database configuration
        self.db_config = {
            'host': settings.DATABASES['default']['HOST'],
            'port': settings.DATABASES['default']['PORT'],
            'database': settings.DATABASES['default']['NAME'],
            'user': settings.DATABASES['default']['USER'],
            'password': settings.DATABASES['default']['PASSWORD'],
        }
        
        # Redis configuration — parse URL format (redis://host:port/db)
        try:
            from urllib.parse import urlparse
            _redis_url = settings.CACHES['default'].get('LOCATION', 'redis://localhost:6379/0')
            _parsed = urlparse(_redis_url)
            self.redis_config = {
                'host': _parsed.hostname or 'localhost',
                'port': _parsed.port or 6379,
                'db': int(_parsed.path.lstrip('/') or 0),
            }
        except Exception:
            self.redis_config = {'host': 'localhost', 'port': 6379, 'db': 0}
        
        # Monitoring thresholds
        self.replication_lag_threshold = getattr(settings, 'REPLICATION_LAG_THRESHOLD', 60)  # seconds
        self.redis_memory_threshold = getattr(settings, 'REDIS_MEMORY_THRESHOLD', 80)  # percentage
        
        # Alert settings
        self.alert_cooldown = getattr(settings, 'ALERT_COOLDOWN', 300)  # 5 minutes
        self.last_alerts = {}
    
    def monitor_replication(self) -> Dict:
        """Monitor all replication systems."""
        monitoring_results = {
            'timestamp': datetime.now().isoformat(),
            'database_replication': self._monitor_database_replication(),
            'redis_replication': self._monitor_redis_replication(),
            'data_consistency': self._check_data_consistency(),
            'system_health': self._check_system_health(),
            'alerts': []
        }
        
        # Check for alerts
        alerts = self._generate_alerts(monitoring_results)
        monitoring_results['alerts'] = alerts
        
        # Log monitoring results
        self.logger.info(
            "Replication monitoring completed",
            database_status=monitoring_results['database_replication']['status'],
            redis_status=monitoring_results['redis_replication']['status'],
            alerts_count=len(alerts)
        )
        
        return monitoring_results
    
    def _monitor_database_replication(self) -> Dict:
        """Monitor PostgreSQL replication status."""
        result = {
            'status': 'UNKNOWN',
            'replication_lag': None,
            'master_status': 'UNKNOWN',
            'slave_status': 'UNKNOWN',
            'last_check': datetime.now().isoformat(),
            'details': {}
        }
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Check if this is a master or replica
            cursor.execute("SELECT pg_is_in_recovery()")
            in_recovery = cursor.fetchone()[0]
            
            if in_recovery:
                # This is a replica/standby
                result['slave_status'] = 'ACTIVE'
                
                # Get replication lag
                cursor.execute("""
                    SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
                """)
                lag_result = cursor.fetchone()
                
                if lag_result and lag_result[0]:
                    result['replication_lag'] = int(lag_result[0])
                    
                    # Determine status based on lag
                    if result['replication_lag'] <= self.replication_lag_threshold:
                        result['status'] = 'HEALTHY'
                    else:
                        result['status'] = 'LAGGING'
                
                # Get replay location
                cursor.execute("SELECT pg_last_xact_replay_timestamp(), pg_last_wal_receive_lsn()")
                replay_info = cursor.fetchone()
                result['details']['last_replay_timestamp'] = replay_info[0].isoformat() if replay_info[0] else None
                result['details']['last_wal_lsn'] = str(replay_info[1]) if replay_info[1] else None
                
            else:
                # This is the master
                result['master_status'] = 'ACTIVE'
                result['status'] = 'MASTER'
                
                # Get WAL information
                cursor.execute("SELECT pg_current_wal_lsn(), pg_current_wal_flush_lsn()")
                wal_info = cursor.fetchone()
                result['details']['current_wal_lsn'] = str(wal_info[0]) if wal_info[0] else None
                result['details']['current_wal_flush_lsn'] = str(wal_info[1]) if wal_info[1] else None
                
                # Check for replica connections
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_stat_replication 
                    WHERE state = 'streaming'
                """)
                replica_count = cursor.fetchone()[0]
                result['details']['active_replicas'] = replica_count
            
            conn.close()
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
            self.logger.error("Database replication monitoring failed", error=str(e))
        
        return result
    
    def _monitor_redis_replication(self) -> Dict:
        """Monitor Redis replication status."""
        result = {
            'status': 'UNKNOWN',
            'role': 'unknown',
            'memory_usage': None,
            'connected_slaves': 0,
            'replication_offset': None,
            'last_check': datetime.now().isoformat(),
            'details': {}
        }
        
        try:
            redis_client = Redis(**self.redis_config)
            info = redis_client.info()
            
            # Get role information
            role = info.get('role', 'master')
            result['role'] = role
            
            if role == 'master':
                result['status'] = 'MASTER'
                
                # Get connected slaves
                connected_slaves = info.get('connected_slaves', 0)
                result['connected_slaves'] = connected_slaves
                
                # Get replication info for each slave
                if connected_slaves > 0:
                    result['details']['slaves'] = []
                    for i in range(connected_slaves):
                        slave_info_key = f'slave{i}'
                        if slave_info_key in info:
                            slave_info = info[slave_info_key]
                            result['details']['slaves'].append({
                                'ip': slave_info.get('ip'),
                                'port': slave_info.get('port'),
                                'state': slave_info.get('state'),
                                'lag': slave_info.get('lag'),
                                'offset': slave_info.get('offset')
                            })
                
                # Get master replication offset
                result['replication_offset'] = info.get('master_repl_offset')
                
            elif role == 'slave':
                result['status'] = 'SLAVE'
                
                # Get slave replication info
                result['details']['master_host'] = info.get('master_host')
                result['details']['master_port'] = info.get('master_port')
                result['details']['master_link_status'] = info.get('master_link_status')
                result['details']['master_sync_in_progress'] = info.get('master_sync_in_progress', False)
                result['replication_offset'] = info.get('slave_repl_offset')
                
                # Check replication lag
                master_link_status = info.get('master_link_status', 'down')
                if master_link_status == 'up':
                    result['status'] = 'HEALTHY'
                else:
                    result['status'] = 'DISCONNECTED'
            
            # Get memory usage
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
                result['memory_usage'] = round(memory_usage_percent, 2)
                
                # Check memory threshold
                if memory_usage_percent > self.redis_memory_threshold:
                    if result['status'] == 'HEALTHY':
                        result['status'] = 'HIGH_MEMORY'
            
            # Get additional Redis info
            result['details']['connected_clients'] = info.get('connected_clients', 0)
            result['details']['total_commands_processed'] = info.get('total_commands_processed', 0)
            result['details']['keyspace_hits'] = info.get('keyspace_hits', 0)
            result['details']['keyspace_misses'] = info.get('keyspace_misses', 0)
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
            self.logger.error("Redis replication monitoring failed", error=str(e))
        
        return result
    
    def _check_data_consistency(self) -> Dict:
        """Check data consistency between systems."""
        result = {
            'status': 'UNKNOWN',
            'checks_performed': 0,
            'checks_passed': 0,
            'inconsistencies': [],
            'last_check': datetime.now().isoformat()
        }
        
        try:
            # Check database connectivity
            db_check = self._check_database_connectivity()
            result['checks_performed'] += 1
            if db_check['success']:
                result['checks_passed'] += 1
            else:
                result['inconsistencies'].append({
                    'type': 'database_connectivity',
                    'message': db_check['error']
                })
            
            # Check Redis connectivity
            redis_check = self._check_redis_connectivity()
            result['checks_performed'] += 1
            if redis_check['success']:
                result['checks_passed'] += 1
            else:
                result['inconsistencies'].append({
                    'type': 'redis_connectivity',
                    'message': redis_check['error']
                })
            
            # Check cache consistency
            cache_check = self._check_cache_consistency()
            result['checks_performed'] += 1
            if cache_check['success']:
                result['checks_passed'] += 1
            else:
                result['inconsistencies'].append({
                    'type': 'cache_consistency',
                    'message': cache_check['error']
                })
            
            # Determine overall status
            if result['checks_passed'] == result['checks_performed']:
                result['status'] = 'CONSISTENT'
            elif result['checks_passed'] > 0:
                result['status'] = 'PARTIAL'
            else:
                result['status'] = 'INCONSISTENT'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['inconsistencies'].append({
                'type': 'system_error',
                'message': str(e)
            })
            self.logger.error("Data consistency check failed", error=str(e))
        
        return result
    
    def _check_database_connectivity(self) -> Dict:
        """Check database connectivity and basic operations."""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Simple query to test connectivity
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            conn.close()
            
            return {'success': True, 'result': result}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_redis_connectivity(self) -> Dict:
        """Check Redis connectivity and basic operations."""
        try:
            redis_client = Redis(**self.redis_config)
            
            # Ping test
            pong = redis_client.ping()
            
            # Set/get test
            test_key = 'replication_monitor_test'
            redis_client.set(test_key, 'test_value', ex=10)
            test_value = redis_client.get(test_key)
            redis_client.delete(test_key)
            
            if pong and test_value == b'test_value':
                return {'success': True}
            else:
                return {'success': False, 'error': 'Redis operations failed'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_cache_consistency(self) -> Dict:
        """Check cache consistency and performance."""
        try:
            from django.core.cache import cache
            
            # Test cache operations
            test_key = 'replication_monitor_cache_test'
            test_value = {'timestamp': datetime.now().isoformat()}
            
            # Set test value
            cache.set(test_key, test_value, 60)
            
            # Get test value
            cached_value = cache.get(test_key)
            
            # Delete test key
            cache.delete(test_key)
            
            if cached_value == test_value:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Cache value mismatch'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_system_health(self) -> Dict:
        """Check overall system health."""
        result = {
            'status': 'UNKNOWN',
            'cpu_usage': None,
            'memory_usage': None,
            'disk_usage': None,
            'load_average': None,
            'last_check': datetime.now().isoformat()
        }
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            result['cpu_usage'] = cpu_percent
            
            # Memory usage
            memory = psutil.virtual_memory()
            result['memory_usage'] = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # Disk usage
            disk = psutil.disk_usage('/')
            result['disk_usage'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
            
            # Load average
            load_avg = psutil.getloadavg()
            result['load_average'] = {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            }
            
            # Determine overall health status
            if (cpu_percent < 80 and 
                memory.percent < 80 and 
                result['disk_usage']['percent'] < 80):
                result['status'] = 'HEALTHY'
            elif (cpu_percent < 95 and 
                  memory.percent < 95 and 
                  result['disk_usage']['percent'] < 95):
                result['status'] = 'WARNING'
            else:
                result['status'] = 'CRITICAL'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            self.logger.error("System health check failed", error=str(e))
        
        return result
    
    def _generate_alerts(self, monitoring_results: Dict) -> List[Dict]:
        """Generate alerts based on monitoring results."""
        alerts = []
        current_time = datetime.now()
        
        # Database replication alerts
        db_status = monitoring_results['database_replication']
        if db_status['status'] == 'LAGGING':
            alert = {
                'type': 'REPLICATION_LAG',
                'severity': 'HIGH',
                'message': f"Database replication lag: {db_status['replication_lag']} seconds",
                'timestamp': current_time.isoformat(),
                'details': db_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        elif db_status['status'] == 'ERROR':
            alert = {
                'type': 'DATABASE_ERROR',
                'severity': 'CRITICAL',
                'message': "Database replication monitoring failed",
                'timestamp': current_time.isoformat(),
                'details': db_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        # Redis replication alerts
        redis_status = monitoring_results['redis_replication']
        if redis_status['status'] == 'DISCONNECTED':
            alert = {
                'type': 'REDIS_DISCONNECTED',
                'severity': 'HIGH',
                'message': "Redis replica disconnected from master",
                'timestamp': current_time.isoformat(),
                'details': redis_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        elif redis_status['status'] == 'HIGH_MEMORY':
            alert = {
                'type': 'REDIS_HIGH_MEMORY',
                'severity': 'MEDIUM',
                'message': f"Redis memory usage: {redis_status['memory_usage']}%",
                'timestamp': current_time.isoformat(),
                'details': redis_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        elif redis_status['status'] == 'ERROR':
            alert = {
                'type': 'REDIS_ERROR',
                'severity': 'CRITICAL',
                'message': "Redis replication monitoring failed",
                'timestamp': current_time.isoformat(),
                'details': redis_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        # Data consistency alerts
        consistency_status = monitoring_results['data_consistency']
        if consistency_status['status'] == 'INCONSISTENT':
            alert = {
                'type': 'DATA_INCONSISTENCY',
                'severity': 'HIGH',
                'message': f"Data consistency issues detected: {len(consistency_status['inconsistencies'])} issues",
                'timestamp': current_time.isoformat(),
                'details': consistency_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        # System health alerts
        system_status = monitoring_results['system_health']
        if system_status['status'] == 'CRITICAL':
            alert = {
                'type': 'SYSTEM_CRITICAL',
                'severity': 'CRITICAL',
                'message': "System resources critically low",
                'timestamp': current_time.isoformat(),
                'details': system_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        elif system_status['status'] == 'WARNING':
            alert = {
                'type': 'SYSTEM_WARNING',
                'severity': 'MEDIUM',
                'message': "System resources approaching limits",
                'timestamp': current_time.isoformat(),
                'details': system_status
            }
            if self._should_send_alert(alert):
                alerts.append(alert)
        
        return alerts
    
    def _should_send_alert(self, alert: Dict) -> bool:
        """Check if alert should be sent based on cooldown."""
        alert_key = f"{alert['type']}_{alert['severity']}"
        current_time = datetime.now()
        
        # Check if we sent this alert type recently
        if alert_key in self.last_alerts:
            last_sent = self.last_alerts[alert_key]
            time_diff = (current_time - last_sent).total_seconds()
            
            if time_diff < self.alert_cooldown:
                return False
        
        # Update last sent time
        self.last_alerts[alert_key] = current_time
        
        return True
    
    def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring."""
        self.logger.info(f"Starting replication monitoring with {interval}s interval")
        
        try:
            while True:
                results = self.monitor_replication()
                
                # Process alerts if any
                if results['alerts']:
                    for alert in results['alerts']:
                        self._send_alert(alert)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Replication monitoring stopped by user")
        except Exception as e:
            self.logger.error("Replication monitoring error", error=str(e))
            raise
    
    def _send_alert(self, alert: Dict):
        """Send alert notification."""
        # Log the alert
        self.logger.warning(
            f"Alert: {alert['type']}",
            severity=alert['severity'],
            message=alert['message'],
            details=alert['details']
        )
        
        # Here you could integrate with external alert systems
        # like PagerDuty, Slack, email, etc.
        
        # For now, just log it
        print(f"ALERT [{alert['severity']}]: {alert['message']}")


def main():
    """Main monitoring execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AirAds Replication Monitor')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    monitor = ReplicationMonitor()
    
    try:
        if args.once:
            results = monitor.monitor_replication()
            print(json.dumps(results, indent=2, default=str))
        else:
            monitor.start_monitoring(args.interval)
    
    except Exception as e:
        print(f"Monitoring failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
