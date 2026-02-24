"""
AirAd Backend — Accounts Service Layer (R4)

All business logic for authentication lives here.
Views delegate entirely to these functions — zero logic in views.
Every auth event writes an AuditLog entry (R5).
Uses django.utils.timezone.now() — never datetime.now().
"""

import logging
import secrets
import string
from datetime import timedelta

from django.contrib.auth import authenticate
from django.http import HttpRequest
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from core.security_alerts import alert_repeated_login_failures
from core.utils import get_client_ip

from .models import AdminRole, AdminUser

logger = logging.getLogger(__name__)

# Lockout policy constants
MAX_FAILED_ATTEMPTS: int = 5
LOCKOUT_DURATION_MINUTES: int = 15


def generate_temp_password(length: int = 16) -> str:
    """Generate a cryptographically secure temporary password.

    Args:
        length: Length of the generated password. Defaults to 16.

    Returns:
        Random password string using letters, digits, and safe symbols.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def authenticate_user(
    request: HttpRequest,
    email: str,
    password: str,
) -> tuple[AdminUser, dict[str, str]]:
    """Authenticate an admin user and return JWT tokens.

    Lockout check is performed BEFORE password verification to prevent
    timing attacks that could reveal account existence.

    On 5 consecutive failures the account is locked for 15 minutes.
    On success, failed_login_count is reset to 0 and last_login_ip updated.
    Every attempt (success or failure) writes an AuditLog entry (R5).

    Args:
        request: The incoming HTTP request (used for IP extraction).
        email: The user's email address.
        password: The raw password to verify.

    Returns:
        Tuple of (AdminUser instance, {"access": ..., "refresh": ...}).

    Raises:
        ValueError: If the account is locked, credentials are invalid,
            or the account is inactive.
    """
    from apps.audit.utils import log_action

    ip_address: str = get_client_ip(request)

    # Step 1 — Look up user (do not reveal existence via timing)
    try:
        user = AdminUser.objects.get(email=email)
    except AdminUser.DoesNotExist:
        logger.warning(
            "Login attempt for unknown email", extra={"email": email, "ip": ip_address}
        )
        raise ValueError("Invalid credentials")

    # Step 2 — Lockout check BEFORE password verification (R3 / timing safety)
    if user.is_locked():
        retry_after: int = max(
            0,
            int((user.locked_until - timezone.now()).total_seconds()),  # type: ignore[operator]
        )
        log_action(
            action="AUTH_LOGIN_LOCKED",
            actor=None,
            target_obj=user,
            request=request,
            before={},
            after={
                "email": email,
                "ip": ip_address,
                "retry_after_seconds": retry_after,
            },
        )
        raise ValueError(f"Account locked. Retry after {retry_after} seconds.")

    # Step 3 — Password verification
    authenticated_user = authenticate(
        request=request, username=email, password=password
    )

    if authenticated_user is None:
        # Increment failure counter
        user.failed_login_count += 1

        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = timezone.now() + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
            log_action(
                action="AUTH_ACCOUNT_LOCKED",
                actor=None,
                target_obj=user,
                request=request,
                before={"failed_login_count": user.failed_login_count - 1},
                after={
                    "failed_login_count": user.failed_login_count,
                    "locked_until": user.locked_until.isoformat(),
                    "ip": ip_address,
                },
            )
            # Fire security alert for monitoring/incident response
            alert_repeated_login_failures(
                email=email,
                ip_address=ip_address,
                attempt_count=user.failed_login_count,
            )
        else:
            log_action(
                action="AUTH_LOGIN_FAILED",
                actor=None,
                target_obj=user,
                request=request,
                before={"failed_login_count": user.failed_login_count - 1},
                after={"failed_login_count": user.failed_login_count, "ip": ip_address},
            )

        user.save(update_fields=["failed_login_count", "locked_until"])
        raise ValueError("Invalid credentials")

    # Step 4 — Active check
    if not authenticated_user.is_active:
        log_action(
            action="AUTH_LOGIN_INACTIVE",
            actor=None,
            target_obj=authenticated_user,
            request=request,
            before={},
            after={"email": email, "ip": ip_address},
        )
        raise ValueError("Account is inactive")

    # Step 5 — Success: reset counter, update IP, clear must_change_password flag
    authenticated_user.failed_login_count = 0
    authenticated_user.locked_until = None
    authenticated_user.last_login_ip = ip_address
    authenticated_user.must_change_password = False
    authenticated_user.save(
        update_fields=[
            "failed_login_count",
            "locked_until",
            "last_login_ip",
            "must_change_password",
        ]
    )

    # Step 6 — Generate JWT tokens
    refresh = RefreshToken.for_user(authenticated_user)
    tokens: dict[str, str] = {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }

    log_action(
        action="AUTH_LOGIN_SUCCESS",
        actor=authenticated_user,
        target_obj=authenticated_user,
        request=request,
        before={},
        after={"email": email, "role": authenticated_user.role, "ip": ip_address},
    )

    return authenticated_user, tokens


def logout_user(request: HttpRequest, refresh_token: str, user: AdminUser) -> None:
    """Blacklist the provided refresh token to invalidate the session.

    Args:
        request: The incoming HTTP request.
        refresh_token: The refresh token string to blacklist.
        user: The authenticated AdminUser performing the logout.

    Raises:
        ValueError: If the refresh token is invalid or already blacklisted.
    """
    from apps.audit.utils import log_action

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception as e:
        raise ValueError(f"Invalid or already blacklisted refresh token: {e}") from e

    log_action(
        action="AUTH_LOGOUT",
        actor=user,
        target_obj=user,
        request=request,
        before={},
        after={"email": user.email, "ip": get_client_ip(request)},
    )


def create_admin_user(
    email: str,
    full_name: str,
    role: AdminRole,
    actor: AdminUser,
    request: HttpRequest,
    password: str | None = None,
    must_change_password: bool = True,
) -> tuple[AdminUser, str]:
    """Create a new AdminUser account.

    If password is provided it is used directly; otherwise a secure temporary
    password is auto-generated. The plaintext password is always returned so
    the caller can deliver it securely. It is NOT stored in plaintext — only
    the hash via set_password().

    Args:
        email: Unique email address for the new user.
        full_name: Display name.
        role: AdminRole value to assign.
        actor: The AdminUser performing the creation (for AuditLog).
        request: The incoming HTTP request.
        password: Optional plaintext password. Auto-generated if not supplied.
        must_change_password: Whether the user must change password on first
            login. Defaults to True.

    Returns:
        Tuple of (AdminUser instance, plaintext password).

    Raises:
        ValueError: If email is already in use.
    """
    from apps.audit.utils import log_action

    if AdminUser.objects.filter(email=email).exists():
        raise ValueError(f"An account with email '{email}' already exists")

    temp_password = password if password is not None else generate_temp_password()

    user = AdminUser.objects.create_user(
        email=email,
        password=temp_password,
        full_name=full_name,
        role=role,
        must_change_password=must_change_password,
    )

    log_action(
        action="ADMIN_USER_CREATED",
        actor=actor,
        target_obj=user,
        request=request,
        before={},
        after={"email": email, "role": role, "full_name": full_name},
    )

    return user, temp_password


def update_admin_user(
    user: AdminUser,
    updates: dict,
    actor: AdminUser | None,
    request,
) -> AdminUser:
    """Partially update an AdminUser record.

    Allowed fields: full_name, role, is_active, is_locked, failed_attempts.
    Unlocking (is_locked=False) also clears locked_until.
    All mutations are audit-logged (R5).

    Args:
        user: The AdminUser instance to update.
        updates: Dict of fields to update.
        actor: The AdminUser performing the update.
        request: The HTTP request (for audit logging).

    Returns:
        The updated AdminUser instance.
    """
    from apps.audit.utils import log_action

    before = {
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "failed_login_count": user.failed_login_count,
        "locked_until": str(user.locked_until) if user.locked_until else None,
    }

    update_fields = []

    if "full_name" in updates:
        user.full_name = updates["full_name"]
        update_fields.append("full_name")

    if "role" in updates:
        user.role = updates["role"]
        update_fields.append("role")

    if "is_active" in updates:
        user.is_active = updates["is_active"]
        update_fields.append("is_active")

    if "failed_login_count" in updates:
        user.failed_login_count = updates["failed_login_count"]
        update_fields.append("failed_login_count")

    if "is_locked" in updates and updates["is_locked"] is False:
        user.locked_until = None
        user.failed_login_count = 0
        update_fields.extend(["locked_until", "failed_login_count"])

    if update_fields:
        user.save(update_fields=list(set(update_fields)))

    after = {
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "failed_login_count": user.failed_login_count,
        "locked_until": str(user.locked_until) if user.locked_until else None,
    }

    log_action(
        action="ADMIN_USER_UPDATED",
        actor=actor,
        target_obj=user,
        request=request,
        before=before,
        after=after,
    )

    return user
