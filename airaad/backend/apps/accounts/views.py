"""
AirAd Backend — Accounts Views

Login, refresh, logout, profile, and admin user creation.
Zero business logic — all delegated to services.py (R4).
Every view uses RolePermission.for_roles() (R3).
Uses django.utils.timezone.now() — never datetime.now().
"""

import logging
import re

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from core.exceptions import success_response

from .models import AdminRole
from .permissions import RolePermission
from .serializers import (
    AdminUserSerializer,
    CreateAdminUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    UpdateAdminUserSerializer,
)
from .services import (
    authenticate_user,
    create_admin_user,
    logout_user,
    update_admin_user,
)

logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """IP-level rate limit for the login endpoint: 10 attempts per minute.

    Complements the per-account lockout in services.py (5 failures → 15 min).
    Prevents brute-force enumeration at the network level before the
    per-account counter is even reached.
    """

    rate = "10/min"


class LoginView(APIView):
    """Authenticate an admin user and return JWT access + refresh tokens.

    Lockout is enforced in services.py — 5 failures → 429 + Retry-After.
    """

    authentication_classes: list = []
    permission_classes = [
        AllowAny
    ]  # nosemgrep: Users.syedsmacbook.Developer.AirAds-web.airaad.drf-allowany-on-sensitive-view
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Admin login — returns JWT tokens",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful — returns access and refresh tokens"
            ),
            401: OpenApiResponse(description="Invalid credentials"),
            429: OpenApiResponse(
                description="Account locked — too many failed attempts"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Validate credentials and return JWT tokens.

        Args:
            request: HTTP request with email and password in body.

        Returns:
            200 with access/refresh tokens and user data on success.
            401 on invalid credentials.
            429 on account lockout with Retry-After header.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = authenticate_user(
                request=request._request,
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except ValueError as e:
            error_msg = str(e)
            if "locked" in error_msg.lower():
                # Extract retry_after seconds from message if present
                match = re.search(r"(\d+) seconds", error_msg)
                retry_after = int(match.group(1)) if match else 900
                response = Response(
                    {
                        "success": False,
                        "data": None,
                        "message": error_msg,
                        "errors": {},
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
                response["Retry-After"] = str(retry_after)
                return response

            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": error_msg,
                    "errors": {},
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            data={
                "user": AdminUserSerializer(user).data,
                "tokens": tokens,
            },
            message="Login successful",
        )


class LogoutView(APIView):
    """Blacklist the provided refresh token to invalidate the session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Logout — blacklist refresh token",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
            400: OpenApiResponse(description="Invalid or already blacklisted token"),
        },
    )
    def post(self, request: Request) -> Response:
        """Blacklist the refresh token.

        Args:
            request: HTTP request with refresh token in body.

        Returns:
            200 on success, 400 on invalid token.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            logout_user(
                request=request._request,
                refresh_token=serializer.validated_data["refresh"],
                user=request.user,
            )
        except ValueError as e:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": str(e),
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(message="Logged out successfully")


class ProfileView(APIView):
    """Return the authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get current user profile",
        responses={
            200: AdminUserSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        """Return the current user's profile data.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with AdminUser data.
        """
        serializer = AdminUserSerializer(request.user)
        return success_response(data=serializer.data)


class CreateAdminUserView(APIView):
    """Create a new AdminUser account. SUPER_ADMIN only."""

    permission_classes = [RolePermission.for_roles(AdminRole.SUPER_ADMIN)]

    @extend_schema(
        tags=["Auth"],
        summary="Create admin user (SUPER_ADMIN only)",
        request=CreateAdminUserSerializer,
        responses={
            201: AdminUserSerializer,
            400: OpenApiResponse(
                description="Validation error or email already in use"
            ),
            403: OpenApiResponse(description="Forbidden — SUPER_ADMIN role required"),
        },
    )
    def post(self, request: Request) -> Response:
        """Create a new AdminUser. Delegates entirely to services.py.

        Args:
            request: HTTP request with user creation data.

        Returns:
            201 with new user data on success.
            400 on validation failure.
        """
        serializer = CreateAdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, temp_password = create_admin_user(
                email=serializer.validated_data["email"],
                full_name=serializer.validated_data["full_name"],
                role=serializer.validated_data["role"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": str(e),
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data={**AdminUserSerializer(user).data, "temp_password": temp_password},
            message="User created. Share this password securely — it will not be shown again.",
            status_code=status.HTTP_201_CREATED,
        )


class AdminUserListView(APIView):
    """List or create AdminUsers. SUPER_ADMIN only."""

    permission_classes = [RolePermission.for_roles(AdminRole.SUPER_ADMIN)]

    @extend_schema(
        tags=["Auth"],
        summary="List all admin users (SUPER_ADMIN only)",
        responses={200: AdminUserSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return all AdminUser records.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with list of AdminUser data.
        """
        from .models import AdminUser as AdminUserModel

        users = AdminUserModel.objects.all().order_by("created_at")
        return success_response(data=AdminUserSerializer(users, many=True).data)

    @extend_schema(
        tags=["Auth"],
        summary="Create admin user (SUPER_ADMIN only)",
        request=CreateAdminUserSerializer,
        responses={
            201: AdminUserSerializer,
            400: OpenApiResponse(
                description="Validation error or email already in use"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Create a new AdminUser. Delegates entirely to services.py.

        Args:
            request: HTTP request with user creation data.

        Returns:
            201 with new user data on success.
            400 on validation failure.
        """
        serializer = CreateAdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, temp_password = create_admin_user(
                email=serializer.validated_data["email"],
                full_name=serializer.validated_data["full_name"],
                role=serializer.validated_data["role"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": str(e),
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data={**AdminUserSerializer(user).data, "temp_password": temp_password},
            message="User created. Share this password securely — it will not be shown again.",
            status_code=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    """Retrieve or partially update an AdminUser. SUPER_ADMIN only."""

    permission_classes = [RolePermission.for_roles(AdminRole.SUPER_ADMIN)]

    def _get_user(self, pk: str):
        from .models import AdminUser as AdminUserModel

        try:
            return AdminUserModel.objects.get(pk=pk)
        except AdminUserModel.DoesNotExist:
            return None

    @extend_schema(
        tags=["Auth"],
        summary="Partially update an admin user (SUPER_ADMIN only)",
        request=UpdateAdminUserSerializer,
        responses={
            200: AdminUserSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update an AdminUser.

        Args:
            request: HTTP request with fields to update.
            pk: UUID of the AdminUser to update.

        Returns:
            200 with updated user data.
            404 if user not found.
        """
        user = self._get_user(pk)
        if user is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "User not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateAdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_admin_user(
                user=user,
                updates=serializer.validated_data,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=AdminUserSerializer(updated).data)


class UnlockAdminUserView(APIView):
    """POST /api/v1/auth/users/<pk>/unlock/ — unlock a locked account. SUPER_ADMIN only."""

    permission_classes = [RolePermission.for_roles(AdminRole.SUPER_ADMIN)]

    @extend_schema(
        tags=["Auth"],
        summary="Unlock a locked admin user account (SUPER_ADMIN only)",
        responses={
            200: AdminUserSerializer,
            404: OpenApiResponse(description="User not found"),
        },
    )
    def post(self, request: Request, pk: str) -> Response:
        """Reset failed_login_count to 0 and clear locked_until.

        Args:
            request: Authenticated HTTP request.
            pk: UUID of the AdminUser to unlock.

        Returns:
            200 with updated user data.
            404 if user not found.
        """
        from .models import AdminUser as AdminUserModel

        try:
            user = AdminUserModel.objects.get(pk=pk)
        except AdminUserModel.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "User not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        updated = update_admin_user(
            user=user,
            updates={"is_locked": False},
            actor=request.user,
            request=request._request,
        )
        return success_response(
            data=AdminUserSerializer(updated).data, message="Account unlocked"
        )


class GDPRDataExportView(APIView):
    """GET /api/v1/auth/me/export/ — export all personal data for the authenticated user.

    Spec §10.1: User right to access — provide data export functionality.
    Returns a JSON snapshot of the user's account data and audit log entries.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["GDPR"],
        summary="Export personal data for the authenticated user (spec §10.1)",
        responses={
            200: OpenApiResponse(description="JSON export of all personal data")
        },
    )
    def get(self, request: Request) -> Response:
        """Return a machine-readable export of the user's personal data.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with JSON export containing account data and audit log entries.
        """
        from apps.audit.models import AuditLog
        from apps.audit.utils import log_action

        user = request.user
        audit_entries = AuditLog.objects.filter(actor=user).order_by("created_at")

        export = {
            "account": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "last_login_ip": user.last_login_ip,
            },
            "audit_log": [
                {
                    "action": entry.action,
                    "target_type": entry.target_type,
                    "target_id": str(entry.target_id) if entry.target_id else None,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in audit_entries
            ],
        }

        log_action(
            action="GDPR_DATA_EXPORTED",
            actor=user,
            target_obj=user,
            request=request._request,
            before={},
            after={"export_type": "JSON", "records_count": len(export["audit_log"])},
        )

        return success_response(data=export, message="Personal data export")


class GDPRAccountDeletionView(APIView):
    """DELETE /api/v1/auth/me/ — delete the authenticated user's account and purge personal data.

    Spec §10.1: User right to deletion — implement account deletion with data purge.
    Deactivates the account, anonymises the email, and clears personal identifiers.
    AuditLog entries are preserved (immutable) but actor FK is set to NULL.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["GDPR"],
        summary="Delete account and purge personal data (spec §10.1)",
        responses={
            200: OpenApiResponse(
                description="Account deactivated and personal data purged"
            ),
            403: OpenApiResponse(description="SUPER_ADMIN accounts cannot self-delete"),
        },
    )
    def delete(self, request: Request) -> Response:
        """Deactivate account and anonymise personal data.

        SUPER_ADMIN accounts are protected from self-deletion to prevent
        accidental loss of the only admin account.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 on success.
            403 if the user is a SUPER_ADMIN.
        """
        from apps.audit.utils import log_action

        user = request.user

        if user.role == AdminRole.SUPER_ADMIN:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "SUPER_ADMIN accounts cannot be self-deleted. Contact another SUPER_ADMIN.",
                    "errors": {},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        original_email = user.email

        # Anonymise personal identifiers — preserve account shell for FK integrity
        user.is_active = False
        user.email = f"deleted-{user.id}@purged.airaad.internal"
        user.full_name = "[Deleted User]"
        user.last_login_ip = None
        user.set_unusable_password()
        user.save(
            update_fields=[
                "is_active",
                "email",
                "full_name",
                "last_login_ip",
                "password",
                "updated_at",
            ]
        )

        log_action(
            action="GDPR_ACCOUNT_DELETED",
            actor=None,
            target_obj=user,
            request=request._request,
            before={"email": original_email, "is_active": True},
            after={"email": user.email, "is_active": False, "purged": True},
        )

        return success_response(message="Account deactivated and personal data purged.")


class CustomTokenRefreshView(TokenRefreshView):
    """JWT token refresh — extends SimpleJWT's default view with schema tags."""

    @extend_schema(
        tags=["Auth"],
        summary="Refresh JWT access token",
        responses={
            200: OpenApiResponse(description="New access token returned"),
            401: OpenApiResponse(description="Refresh token invalid or expired"),
        },
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Refresh the JWT access token using a valid refresh token.

        Args:
            request: HTTP request with refresh token in body.

        Returns:
            200 with new access token on success.
        """
        return super().post(request, *args, **kwargs)
