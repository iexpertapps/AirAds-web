"""
AirAd Backend — Security Alerting Framework

Detects and logs security-relevant anomalies:
- Repeated login failures from the same IP
- Privilege escalation attempts (accessing above role)
- Large data exports (bulk download anomaly)

Phase A: Alerts are logged to the structured logger with level CRITICAL.
Phase B: Integrate with an external alerting service (PagerDuty, Slack webhook, etc.).

All alert functions are designed to be called from services.py or middleware.
They NEVER block the request — fire-and-forget logging only.
"""

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger("security.alerts")


def alert_repeated_login_failures(email: str, ip_address: str, attempt_count: int) -> None:
    """Fire an alert when login failures exceed the threshold.

    Called from accounts/services.py when failed_login_count reaches MAX_FAILED_ATTEMPTS.

    Args:
        email: Email of the targeted account.
        ip_address: IP address of the attacker.
        attempt_count: Number of consecutive failed attempts.
    """
    logger.critical(
        "SECURITY_ALERT: Repeated login failures — account locked",
        extra={
            "alert_type": "REPEATED_LOGIN_FAILURES",
            "email": email,
            "ip_address": ip_address,
            "attempt_count": attempt_count,
            "timestamp": timezone.now().isoformat(),
        },
    )


def alert_privilege_escalation(
    user_id: str, user_role: str, attempted_resource: str, ip_address: str
) -> None:
    """Fire an alert when a user attempts to access above their role.

    Called from permissions.py when RBAC denies access.

    Args:
        user_id: UUID string of the user.
        user_role: Current role of the user.
        attempted_resource: View/endpoint the user tried to access.
        ip_address: IP address of the user.
    """
    logger.critical(
        "SECURITY_ALERT: Privilege escalation attempt",
        extra={
            "alert_type": "PRIVILEGE_ESCALATION",
            "user_id": user_id,
            "user_role": user_role,
            "attempted_resource": attempted_resource,
            "ip_address": ip_address,
            "timestamp": timezone.now().isoformat(),
        },
    )


def alert_large_data_export(
    user_id: str, user_email: str, record_count: int, export_type: str
) -> None:
    """Fire an alert when an unusually large data export is detected.

    Called from GDPR export or any bulk data endpoint when the record
    count exceeds a threshold.

    Args:
        user_id: UUID string of the exporting user.
        user_email: Email of the exporting user.
        record_count: Number of records exported.
        export_type: Type of export (e.g. "GDPR_EXPORT", "CSV_EXPORT").
    """
    LARGE_EXPORT_THRESHOLD = 1000

    if record_count < LARGE_EXPORT_THRESHOLD:
        return

    logger.critical(
        "SECURITY_ALERT: Large data export detected",
        extra={
            "alert_type": "LARGE_DATA_EXPORT",
            "user_id": user_id,
            "user_email": user_email,
            "record_count": record_count,
            "export_type": export_type,
            "threshold": LARGE_EXPORT_THRESHOLD,
            "timestamp": timezone.now().isoformat(),
        },
    )


def alert_unusual_access_pattern(
    user_id: str, user_email: str, resource: str, access_count: int, window_minutes: int = 5
) -> None:
    """Fire an alert when a user accesses a resource at an unusual rate.

    Args:
        user_id: UUID string of the user.
        user_email: Email of the user.
        resource: Resource being accessed at high rate.
        access_count: Number of accesses in the window.
        window_minutes: Time window in minutes.
    """
    logger.critical(
        "SECURITY_ALERT: Unusual access pattern detected",
        extra={
            "alert_type": "UNUSUAL_ACCESS_PATTERN",
            "user_id": user_id,
            "user_email": user_email,
            "resource": resource,
            "access_count": access_count,
            "window_minutes": window_minutes,
            "timestamp": timezone.now().isoformat(),
        },
    )
