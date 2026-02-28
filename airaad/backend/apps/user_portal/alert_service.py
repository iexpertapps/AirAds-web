"""
Alert Service for AirAds User Portal
Comprehensive alerting system for monitoring and notifications
"""

import json
import time
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from enum import Enum
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import requests
import logging

from .system_health import SystemHealthMonitor
from .replication_monitor import ReplicationMonitor
from .logging import structured_logger

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    component: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []


class AlertChannel:
    """Base class for alert channels."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = structured_logger
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert through this channel."""
        if not self.enabled:
            return False
        
        try:
            return self._send_alert(alert)
        except Exception as e:
            self.logger.error(
                f"Failed to send alert via {self.name}",
                error=str(e),
                alert_id=alert.id
            )
            return False
    
    def _send_alert(self, alert: Alert) -> bool:
        """Implement channel-specific alert sending."""
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Email alert channel."""
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            smtp_config = self.config.get('smtp', {})
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config.get('from_email')
            msg['To'] = ', '.join(self.config.get('recipients', []))
            msg['Subject'] = f"[{alert.severity.value}] {alert.title}"
            
            # Create email body
            body = self._format_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(
                smtp_config.get('host'),
                smtp_config.get('port', 587)
            ) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()
                
                if smtp_config.get('username') and smtp_config.get('password'):
                    server.login(
                        smtp_config.get('username'),
                        smtp_config.get('password')
                    )
                
                server.send_message(msg)
            
            self.logger.info(
                "Email alert sent successfully",
                alert_id=alert.id,
                recipients=self.config.get('recipients', [])
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to send email alert", error=str(e))
            return False
    
    def _format_email_body(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .alert-header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
                .alert-body {{ padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }}
                .metadata {{ margin-top: 15px; font-size: 12px; color: #666; }}
                .footer {{ margin-top: 20px; font-size: 11px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="alert-header">
                <h2>{alert.title}</h2>
                <p>Severity: {alert.severity.value} | Component: {alert.component}</p>
            </div>
            
            <div class="alert-body">
                <p><strong>Message:</strong></p>
                <p>{alert.message}</p>
                
                <p><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                
                {self._format_metadata(alert.metadata) if alert.metadata else ''}
            </div>
            
            <div class="footer">
                <p>This alert was generated by the AirAds User Portal monitoring system.</p>
                <p>Alert ID: {alert.id}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for email."""
        if not metadata:
            return ""
        
        html = '<div class="metadata"><p><strong>Additional Details:</strong></p><ul>'
        
        for key, value in metadata.items():
            html += f'<li><strong>{key}:</strong> {value}</li>'
        
        html += '</ul></div>'
        
        return html


class SlackAlertChannel(AlertChannel):
    """Slack alert channel."""
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            webhook_url = self.config.get('webhook_url')
            if not webhook_url:
                self.logger.warning("Slack webhook URL not configured")
                return False
            
            # Format Slack message
            payload = self._format_slack_message(alert)
            
            # Send to Slack
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(
                    "Slack alert sent successfully",
                    alert_id=alert.id
                )
                return True
            else:
                self.logger.error(
                    "Slack API error",
                    status_code=response.status_code,
                    response_text=response.text
                )
                return False
                
        except Exception as e:
            self.logger.error("Failed to send Slack alert", error=str(e))
            return False
    
    def _format_slack_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Slack."""
        severity_colors = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }
        
        color = severity_colors.get(alert.severity, "good")
        
        payload = {
            "text": f"[{alert.severity.value}] {alert.title}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Component",
                            "value": alert.component,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.value,
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert.message,
                            "short": False
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": True
                        },
                        {
                            "title": "Alert ID",
                            "value": alert.id,
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        # Add metadata if present
        if alert.metadata:
            metadata_text = "\n".join([f"• *{key}*: {value}" for key, value in alert.metadata.items()])
            
            payload["attachments"][0]["fields"].append({
                "title": "Additional Details",
                "value": metadata_text,
                "short": False
            })
        
        return payload


class PagerDutyAlertChannel(AlertChannel):
    """PagerDuty alert channel."""
    
    def _send_alert(self, alert: Alert) -> bool:
        """Send alert to PagerDuty."""
        try:
            integration_key = self.config.get('integration_key')
            if not integration_key:
                self.logger.warning("PagerDuty integration key not configured")
                return False
            
            # PagerDuty API endpoint
            url = f"https://events.pagerduty.com/v2/enqueue"
            
            # Format PagerDuty event
            payload = {
                "routing_key": integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": alert.title,
                    "source": alert.component,
                    "severity": self._map_severity(alert.severity),
                    "timestamp": alert.timestamp.isoformat(),
                    "custom_details": {
                        "message": alert.message,
                        "alert_id": alert.id,
                        "metadata": alert.metadata
                    }
                }
            }
            
            # Send to PagerDuty
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 202:
                self.logger.info(
                    "PagerDuty alert sent successfully",
                    alert_id=alert.id
                )
                return True
            else:
                self.logger.error(
                    "PagerDuty API error",
                    status_code=response.status_code,
                    response_text=response.text
                )
                return False
                
        except Exception as e:
            self.logger.error("Failed to send PagerDuty alert", error=str(e))
            return False
    
    def _map_severity(self, severity: AlertSeverity) -> str:
        """Map alert severity to PagerDuty severity."""
        mapping = {
            AlertSeverity.LOW: "info",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "error",
            AlertSeverity.CRITICAL: "critical"
        }
        return mapping.get(severity, "info")


class AlertService:
    """
    Main alert service.
    Manages alert generation, routing, and suppression.
    """
    
    def __init__(self):
        self.logger = structured_logger
        self.channels: Dict[str, AlertChannel] = {}
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.suppression_rules: List[SuppressionRule] = []
        self.health_monitor = SystemHealthMonitor()
        self.replication_monitor = ReplicationMonitor()
        
        # Configuration
        self.config = getattr(settings, 'ALERT_SERVICE_CONFIG', {})
        self.alert_cooldown = self.config.get('alert_cooldown', 300)  # 5 minutes
        self.max_active_alerts = self.config.get('max_active_alerts', 1000)
        
        # Initialize channels
        self._initialize_channels()
        
        # Initialize alert rules
        self._initialize_alert_rules()
    
    def _initialize_channels(self):
        """Initialize alert channels from configuration."""
        channels_config = self.config.get('channels', {})
        
        # Email channel
        if 'email' in channels_config:
            self.channels['email'] = EmailAlertChannel('email', channels_config['email'])
        
        # Slack channel
        if 'slack' in channels_config:
            self.channels['slack'] = SlackAlertChannel('slack', channels_config['slack'])
        
        # PagerDuty channel
        if 'pagerduty' in channels_config:
            self.channels['pagerduty'] = PagerDutyAlertChannel('pagerduty', channels_config['pagerduty'])
        
        self.logger.info(f"Initialized {len(self.channels)} alert channels")
    
    def _initialize_alert_rules(self):
        """Initialize alert rules."""
        # System health alerts
        self.alert_rules.extend([
            AlertRule(
                name="system_health_critical",
                condition=self._check_system_health_critical,
                severity=AlertSeverity.CRITICAL,
                channels=['email', 'slack', 'pagerduty'],
                cooldown=300  # 5 minutes
            ),
            AlertRule(
                name="system_health_warning",
                condition=self._check_system_health_warning,
                severity=AlertSeverity.MEDIUM,
                channels=['email', 'slack'],
                cooldown=600  # 10 minutes
            ),
            AlertRule(
                name="replication_lag",
                condition=self._check_replication_lag,
                severity=AlertSeverity.HIGH,
                channels=['email', 'slack'],
                cooldown=300  # 5 minutes
            ),
            AlertRule(
                name="high_error_rate",
                condition=self._check_high_error_rate,
                severity=AlertSeverity.HIGH,
                channels=['email', 'slack'],
                cooldown=600  # 10 minutes
            ),
            AlertRule(
                name="backup_failure",
                condition=self._check_backup_failure,
                severity=AlertSeverity.CRITICAL,
                channels=['email', 'slack', 'pagerduty'],
                cooldown=300  # 5 minutes
            )
        ])
        
        self.logger.info(f"Initialized {len(self.alert_rules)} alert rules")
    
    def check_alerts(self) -> List[Alert]:
        """Check all alert rules and generate alerts."""
        generated_alerts = []
        
        for rule in self.alert_rules:
            try:
                if rule.should_trigger():
                    alert = rule.generate_alert()
                    
                    # Check suppression
                    if not self._is_suppressed(alert):
                        # Check cooldown
                        if self._should_send_alert(alert):
                            generated_alerts.append(alert)
                            self.active_alerts[alert.id] = alert
                            
                            # Send alert through channels
                            self._send_alert(alert)
                        else:
                            self.logger.info(
                                "Alert suppressed due to cooldown",
                                alert_id=alert.id,
                                rule_name=rule.name
                            )
                    else:
                        self.logger.info(
                            "Alert suppressed by suppression rule",
                            alert_id=alert.id,
                            rule_name=rule.name
                        )
                        
            except Exception as e:
                self.logger.error(
                    f"Error checking alert rule {rule.name}",
                    error=str(e)
                )
        
        # Clean up old alerts
        self._cleanup_old_alerts()
        
        return generated_alerts
    
    def _send_alert(self, alert: Alert):
        """Send alert through configured channels."""
        for channel_name in alert.metadata.get('channels', []):
            if channel_name in self.channels:
                success = self.channels[channel_name].send_alert(alert)
                
                if success:
                    self.logger.info(
                        f"Alert sent via {channel_name}",
                        alert_id=alert.id
                    )
                else:
                    self.logger.error(
                        f"Failed to send alert via {channel_name}",
                        alert_id=alert.id
                    )
    
    def _is_suppressed(self, alert: Alert) -> bool:
        """Check if alert is suppressed by any suppression rule."""
        for rule in self.suppression_rules:
            if rule.suppresses(alert):
                return True
        return False
    
    def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on cooldown."""
        cache_key = f"alert_cooldown:{alert.component}:{alert.severity.value}"
        
        if cache.get(cache_key):
            return False
        
        # Set cooldown
        cooldown = alert.metadata.get('cooldown', self.alert_cooldown)
        cache.set(cache_key, True, timeout=cooldown)
        
        return True
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts."""
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        alerts_to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if alert.status == AlertStatus.RESOLVED and alert.resolved_at:
                if alert.resolved_at < cutoff_time:
                    alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.active_alerts[alert_id]
        
        if alerts_to_remove:
            self.logger.info(f"Cleaned up {len(alerts_to_remove)} old alerts")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = timezone.now()
            
            self.logger.info(
                "Alert acknowledged",
                alert_id=alert_id,
                acknowledged_by=acknowledged_by
            )
            
            return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = timezone.now()
            
            self.logger.info(
                "Alert resolved",
                alert_id=alert_id
            )
            
            return True
        
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    # Alert condition methods
    def _check_system_health_critical(self) -> bool:
        """Check for critical system health issues."""
        health = self.health_monitor.get_system_health()
        return health['overall_status'] == 'CRITICAL'
    
    def _check_system_health_warning(self) -> bool:
        """Check for system health warnings."""
        health = self.health_monitor.get_system_health()
        return health['overall_status'] == 'WARNING'
    
    def _check_replication_lag(self) -> bool:
        """Check for replication lag issues."""
        monitoring = self.replication_monitor.monitor_replication()
        
        db_status = monitoring['database_replication']
        if db_status.get('replication_lag', 0) > 300:  # 5 minutes
            return True
        
        return False
    
    def _check_high_error_rate(self) -> bool:
        """Check for high error rate."""
        from django.utils import timezone
        from .models_error import ErrorLog
        
        # Check errors in last 5 minutes
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        error_count = ErrorLog.objects.filter(occurred_at__gte=five_minutes_ago).count()
        
        return error_count > 10  # More than 10 errors in 5 minutes
    
    def _check_backup_failure(self) -> bool:
        """Check for backup failures."""
        from django.utils import timezone
        from .models_backup import BackupLog
        
        # Check for failed backups in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        failed_backups = BackupLog.objects.filter(
            started_at__gte=one_hour_ago,
            success=False
        ).count()
        
        return failed_backups > 0


class AlertRule:
    """Alert rule definition."""
    
    def __init__(self, name: str, condition: Callable[[], bool], severity: AlertSeverity, 
                 channels: List[str], cooldown: int = 300):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.channels = channels
        self.cooldown = cooldown
        self.last_triggered = None
    
    def should_trigger(self) -> bool:
        """Check if alert should be triggered."""
        try:
            return self.condition()
        except Exception as e:
            logger.error(f"Error in alert rule {self.name}", error=str(e))
            return False
    
    def generate_alert(self) -> Alert:
        """Generate alert from this rule."""
        alert_id = f"{self.name}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            title=self._get_alert_title(),
            message=self._get_alert_message(),
            severity=self.severity,
            component=self._get_component(),
            timestamp=timezone.now(),
            metadata={
                'rule_name': self.name,
                'channels': self.channels,
                'cooldown': self.cooldown
            }
        )
        
        self.last_triggered = timezone.now()
        return alert
    
    def _get_alert_title(self) -> str:
        """Get alert title."""
        titles = {
            "system_health_critical": "Critical System Health Issue",
            "system_health_warning": "System Health Warning",
            "replication_lag": "Database Replication Lag",
            "high_error_rate": "High Error Rate Detected",
            "backup_failure": "Backup Operation Failed"
        }
        return titles.get(self.name, f"Alert: {self.name}")
    
    def _get_alert_message(self) -> str:
        """Get alert message."""
        messages = {
            "system_health_critical": "One or more system components are in critical state",
            "system_health_warning": "System health issues detected",
            "replication_lag": "Database replication lag exceeds threshold",
            "high_error_rate": "Error rate is above normal threshold",
            "backup_failure": "Recent backup operations have failed"
        }
        return messages.get(self.name, f"Alert triggered by rule {self.name}")
    
    def _get_component(self) -> str:
        """Get component name."""
        components = {
            "system_health_critical": "system",
            "system_health_warning": "system",
            "replication_lag": "database",
            "high_error_rate": "application",
            "backup_failure": "backup"
        }
        return components.get(self.name, "unknown")


class SuppressionRule:
    """Alert suppression rule."""
    
    def __init__(self, name: str, condition: Callable[[Alert], bool]):
        self.name = name
        self.condition = condition
    
    def suppresses(self, alert: Alert) -> bool:
        """Check if this rule suppresses the alert."""
        try:
            return self.condition(alert)
        except Exception as e:
            logger.error(f"Error in suppression rule {self.name}", error=str(e))
            return False


# Global alert service instance
alert_service = AlertService()
