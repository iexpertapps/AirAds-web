"""
AirAd Backend — RBAC Permission Classes (R3)

RolePermission.for_roles() is the ONLY RBAC mechanism in the entire codebase.
No scattered `if user.role ==` checks are permitted anywhere.

Usage in views:
    permission_classes = [RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.CITY_MANAGER)]
"""

import logging

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import AdminRole

logger = logging.getLogger(__name__)


class RolePermission(BasePermission):
    """Base RBAC permission class. Use for_roles() — never instantiate directly.

    Subclasses are created dynamically by for_roles() with the allowed_roles
    tuple set as a class attribute. This ensures each view's permission class
    is a distinct type, which DRF inspects correctly for OpenAPI generation.

    No __call__ method — class-based only.

    Attributes:
        allowed_roles: Tuple of AdminRole values permitted to access the view.
            Empty by default — denies all access unless overridden by for_roles().
    """

    allowed_roles: tuple[AdminRole, ...] = ()

    @classmethod
    def for_roles(cls, *roles: AdminRole) -> type["RolePermission"]:
        """Create a permission class restricted to the given roles.

        Uses Python's type() factory to produce a named subclass with
        allowed_roles set. Each call produces a distinct class, which is
        required for DRF's permission introspection to work correctly.

        Args:
            *roles: One or more AdminRole values that are permitted.

        Returns:
            A new RolePermission subclass with allowed_roles set to roles.

        Raises:
            ValueError: If no roles are provided.

        Example:
            >>> perm = RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.QA_REVIEWER)
            >>> perm.allowed_roles
            (<AdminRole.SUPER_ADMIN: 'SUPER_ADMIN'>, <AdminRole.QA_REVIEWER: 'QA_REVIEWER'>)
        """
        if not roles:
            raise ValueError("for_roles() requires at least one AdminRole argument")

        return type(
            "DynamicRolePermission",
            (cls,),
            {"allowed_roles": roles},
        )

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check that the request user is authenticated and has an allowed role.

        Args:
            request: The DRF request object.
            view: The view being accessed.

        Returns:
            True if the user is authenticated and their role is in allowed_roles.
            False otherwise.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        user_role: str = getattr(request.user, "role", "")
        allowed: bool = user_role in self.allowed_roles

        if not allowed:
            logger.warning(
                "RBAC denied",
                extra={
                    "user_id": str(request.user.pk),
                    "user_role": user_role,
                    "allowed_roles": [r for r in self.allowed_roles],
                    "view": view.__class__.__name__,
                },
            )
            # Fire security alert for privilege escalation attempts
            from core.security_alerts import alert_privilege_escalation
            from core.utils import get_client_ip

            alert_privilege_escalation(
                user_id=str(request.user.pk),
                user_role=user_role,
                attempted_resource=view.__class__.__name__,
                ip_address=get_client_ip(request._request)
                if hasattr(request, "_request")
                else "unknown",
            )

        return allowed
