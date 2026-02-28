"""
Uptime Monitoring for AirAds User Portal
External uptime monitoring integration and status tracking
"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import logging

from .system_health import SystemHealthMonitor
from .logging import structured_logger
from .models_error import ErrorLog

logger = logging.getLogger(__name__)


class UptimeMonitor:
    """
    Uptime monitoring system.
    Integrates with external monitoring services and tracks uptime statistics.
    """
    
    def __init__(self):
        self.logger = structured_logger
        self.health_monitor = SystemHealthMonitor()
        
        # Configuration
        self.config = getattr(settings, 'UPTIME_MONITORING_CONFIG', {})
        self.check_interval = self.config.get('check_interval', 60)  # seconds
        self.timeout = self.config.get('timeout', 10)  # seconds
        self.endpoints = self.config.get('endpoints', [])
        
        # External monitoring services
        self.uptime_robot = UptimeRobotMonitor(self.config.get('uptime_robot', {}))
        self.pingdom = PingdomMonitor(self.config.get('pingdom', {}))
        self.statuspage = StatusPageMonitor(self.config.get('statuspage', {}))
        
        # Uptime statistics
        self.uptime_stats = {}
        self.check_history = []
    
    def check_uptime(self) -> Dict:
        """Perform comprehensive uptime check."""
        uptime_check = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'checks': {},
            'external_services': {},
            'statistics': {},
            'alerts': []
        }
        
        try:
            # Internal endpoint checks
            internal_checks = self._check_internal_endpoints()
            uptime_check['checks'] = internal_checks
            
            # External service checks
            external_checks = self._check_external_services()
            uptime_check['external_services'] = external_checks
            
            # Calculate overall status
            all_checks = list(internal_checks.values()) + list(external_checks.values())
            failed_checks = [c for c in all_checks if c.get('status') == 'DOWN']
            
            if failed_checks:
                uptime_check['overall_status'] = 'DEGRADED' if len(failed_checks) < len(all_checks) else 'DOWN'
                uptime_check['alerts'] = [
                    {
                        'type': 'uptime_failure',
                        'message': f"Uptime check failed for {len(failed_checks)} endpoints",
                        'details': {'failed_endpoints': [c['name'] for c in failed_checks]}
                    }
                ]
            else:
                uptime_check['overall_status'] = 'UP'
            
            # Update statistics
            self._update_statistics(uptime_check)
            uptime_check['statistics'] = self.get_uptime_statistics()
            
            # Store check history
            self.check_history.append(uptime_check)
            if len(self.check_history) > 1000:  # Keep last 1000 checks
                self.check_history = self.check_history[-1000:]
            
            self.logger.info(
                "Uptime check completed",
                overall_status=uptime_check['overall_status'],
                endpoints_checked=len(all_checks),
                failed_count=len(failed_checks)
            )
            
        except Exception as e:
            uptime_check['overall_status'] = 'ERROR'
            uptime_check['alerts'].append({
                'type': 'uptime_error',
                'message': 'Uptime monitoring failed',
                'details': {'error': str(e)}
            })
            
            self.logger.error("Uptime check failed", error=str(e))
        
        return uptime_check
    
    def _check_internal_endpoints(self) -> Dict:
        """Check internal application endpoints."""
        checks = {}
        
        # Default endpoints to check
        default_endpoints = [
            {'name': 'health', 'path': '/api/user-portal/health/', 'method': 'GET'},
            {'name': 'metrics', 'path': '/api/user-portal/metrics/', 'method': 'GET'},
            {'name': 'discovery', 'path': '/api/user-portal/nearby/vendors/', 'method': 'GET'},
        ]
        
        # Add custom endpoints from configuration
        all_endpoints = default_endpoints + self.endpoints
        
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        for endpoint in all_endpoints:
            check_result = self._check_endpoint(
                name=endpoint['name'],
                url=f"{base_url}{endpoint['path']}",
                method=endpoint.get('method', 'GET'),
                expected_status=endpoint.get('expected_status', 200)
            )
            
            checks[endpoint['name']] = check_result
        
        return checks
    
    def _check_endpoint(self, name: str, url: str, method: str = 'GET', 
                       expected_status: int = 200, timeout: int = None) -> Dict:
        """Check a single endpoint."""
        if timeout is None:
            timeout = self.timeout
        
        check_result = {
            'name': name,
            'url': url,
            'method': method,
            'status': 'UNKNOWN',
            'response_time': None,
            'status_code': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            start_time = time.time()
            
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            
            check_result['response_time'] = response_time
            check_result['status_code'] = response.status_code
            
            # Determine status
            if response.status_code == expected_status:
                check_result['status'] = 'UP'
            elif response.status_code >= 500:
                check_result['status'] = 'DOWN'
            else:
                check_result['status'] = 'DEGRADED'
            
            # Add response details for debugging
            if response.status_code != expected_status:
                check_result['error'] = f"Expected {expected_status}, got {response.status_code}"
            
        except requests.exceptions.Timeout:
            check_result['status'] = 'DOWN'
            check_result['error'] = f"Request timeout after {timeout}s"
        except requests.exceptions.ConnectionError:
            check_result['status'] = 'DOWN'
            check_result['error'] = "Connection error"
        except Exception as e:
            check_result['status'] = 'DOWN'
            check_result['error'] = str(e)
        
        return check_result
    
    def _check_external_services(self) -> Dict:
        """Check external monitoring services."""
        checks = {}
        
        # UptimeRobot
        if self.uptime_robot.enabled:
            try:
                uptime_robot_status = self.uptime_robot.get_status()
                checks['uptime_robot'] = {
                    'name': 'UptimeRobot',
                    'status': 'UP' if uptime_robot_status.get('available', False) else 'DOWN',
                    'details': uptime_robot_status,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                checks['uptime_robot'] = {
                    'name': 'UptimeRobot',
                    'status': 'ERROR',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        # Pingdom
        if self.pingdom.enabled:
            try:
                pingdom_status = self.pingdom.get_status()
                checks['pingdom'] = {
                    'name': 'Pingdom',
                    'status': 'UP' if pingdom_status.get('available', False) else 'DOWN',
                    'details': pingdom_status,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                checks['pingdom'] = {
                    'name': 'Pingdom',
                    'status': 'ERROR',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        # StatusPage
        if self.statuspage.enabled:
            try:
                statuspage_status = self.statuspage.get_status()
                checks['statuspage'] = {
                    'name': 'StatusPage',
                    'status': 'UP' if statuspage_status.get('available', False) else 'DOWN',
                    'details': statuspage_status,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                checks['statuspage'] = {
                    'name': 'StatusPage',
                    'status': 'ERROR',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return checks
    
    def _update_statistics(self, uptime_check: Dict):
        """Update uptime statistics."""
        # Calculate uptime for different time periods
        now = timezone.now()
        
        # Last 24 hours
        uptime_24h = self._calculate_uptime_period(now - timedelta(hours=24), now)
        
        # Last 7 days
        uptime_7d = self._calculate_uptime_period(now - timedelta(days=7), now)
        
        # Last 30 days
        uptime_30d = self._calculate_uptime_period(now - timedelta(days=30), now)
        
        self.uptime_stats = {
            'uptime_24h': uptime_24h,
            'uptime_7d': uptime_7d,
            'uptime_30d': uptime_30d,
            'last_check': uptime_check['timestamp'],
            'overall_status': uptime_check['overall_status']
        }
        
        # Cache statistics
        cache.set('uptime_statistics', self.uptime_stats, timeout=300)  # 5 minutes
    
    def _calculate_uptime_period(self, start_time: datetime, end_time: datetime) -> Dict:
        """Calculate uptime statistics for a time period."""
        # Filter checks within the time period
        period_checks = [
            check for check in self.check_history
            if start_time <= datetime.fromisoformat(check['timestamp'].replace('Z', '+00:00')) <= end_time
        ]
        
        if not period_checks:
            return {
                'uptime_percentage': 100.0,  # Assume 100% if no data
                'total_checks': 0,
                'successful_checks': 0,
                'failed_checks': 0,
                'degraded_checks': 0
            }
        
        total_checks = len(period_checks)
        successful_checks = sum(1 for check in period_checks if check['overall_status'] == 'UP')
        failed_checks = sum(1 for check in period_checks if check['overall_status'] == 'DOWN')
        degraded_checks = sum(1 for check in period_checks if check['overall_status'] == 'DEGRADED')
        
        # Calculate uptime percentage (considering degraded as partially up)
        uptime_percentage = ((successful_checks + (degraded_checks * 0.5)) / total_checks) * 100
        
        return {
            'uptime_percentage': round(uptime_percentage, 2),
            'total_checks': total_checks,
            'successful_checks': successful_checks,
            'failed_checks': failed_checks,
            'degraded_checks': degraded_checks
        }
    
    def get_uptime_statistics(self) -> Dict:
        """Get current uptime statistics."""
        # Try to get from cache first
        cached_stats = cache.get('uptime_statistics')
        if cached_stats:
            return cached_stats
        
        # If not in cache, return current stats
        return self.uptime_stats
    
    def start_continuous_monitoring(self):
        """Start continuous uptime monitoring."""
        self.logger.info(f"Starting continuous uptime monitoring with {self.check_interval}s interval")
        
        try:
            while True:
                self.check_uptime()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Uptime monitoring stopped by user")
        except Exception as e:
            self.logger.error("Uptime monitoring error", error=str(e))
            raise


class UptimeRobotMonitor:
    """UptimeRobot integration."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.api_key = config.get('api_key')
        self.base_url = 'https://api.uptimerobot.com/v2'
    
    def get_status(self) -> Dict:
        """Get UptimeRobot status."""
        if not self.enabled or not self.api_key:
            return {'available': False, 'error': 'UptimeRobot not configured'}
        
        try:
            # Get monitors
            response = requests.get(
                f"{self.base_url}/getMonitors",
                params={'api_key': self.api_key, 'format': 'json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                monitors = data.get('monitors', [])
                
                return {
                    'available': True,
                    'monitors_count': len(monitors),
                    'monitors': monitors,
                    'status': 'connected'
                }
            else:
                return {'available': False, 'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'available': False, 'error': str(e)}


class PingdomMonitor:
    """Pingdom integration."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.api_key = config.get('api_key')
        self.email = config.get('email')
        self.base_url = 'https://api.pingdom.com/api/3.1'
    
    def get_status(self) -> Dict:
        """Get Pingdom status."""
        if not self.enabled or not self.api_key:
            return {'available': False, 'error': 'Pingdom not configured'}
        
        try:
            # Get checks
            response = requests.get(
                f"{self.base_url}/checks",
                auth=(self.email, self.api_key),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                checks = data.get('checks', [])
                
                return {
                    'available': True,
                    'checks_count': len(checks),
                    'checks': checks,
                    'status': 'connected'
                }
            else:
                return {'available': False, 'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'available': False, 'error': str(e)}


class StatusPageMonitor:
    """StatusPage.io integration."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.page_id = config.get('page_id')
        self.api_key = config.get('api_key')
        self.base_url = 'https://api.statuspage.io/v1'
    
    def get_status(self) -> Dict:
        """Get StatusPage status."""
        if not self.enabled or not self.page_id:
            return {'available': False, 'error': 'StatusPage not configured'}
        
        try:
            # Get page status
            headers = {'Authorization': f'OAuth {self.api_key}'} if self.api_key else {}
            
            response = requests.get(
                f"{self.base_url}/pages/{self.page_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'available': True,
                    'page_id': self.page_id,
                    'status': data.get('status', 'unknown'),
                    'status_indicator': data.get('status_indicator', 'none'),
                    'components': data.get('components', []),
                    'status': 'connected'
                }
            else:
                return {'available': False, 'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'available': False, 'error': str(e)}


# Global uptime monitor instance
uptime_monitor = UptimeMonitor()
