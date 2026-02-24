"""
AirAd Backend — Tags Views

Zero business logic — all delegated to tags/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
SYSTEM tag enforcement happens in services.py.
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from django.db.models import Count
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tag
from .serializers import CreateTagSerializer, TagSerializer, UpdateTagSerializer
from .services import create_tag, delete_tag, update_tag

logger = logging.getLogger(__name__)


class TagListCreateView(APIView):
    """List all tags or create a new one. SYSTEM tags cannot be created via API."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
        AdminRole.DATA_QUALITY_ANALYST,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Tags"], summary="List tags", responses={200: TagSerializer(many=True)}
    )
    def get(self, request: Request) -> Response:
        """Return all active tags, optionally filtered by tag_type."""
        qs = Tag.objects.annotate(usage_count=Count("vendors")).filter(is_active=True)
        tag_type = request.query_params.get("tag_type")
        if tag_type:
            qs = qs.filter(tag_type=tag_type)
        return success_response(data=TagSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Tags"],
        summary="Create tag (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY) — SYSTEM type rejected",
        request=CreateTagSerializer,
        responses={
            201: TagSerializer,
            403: OpenApiResponse(description="SYSTEM tag rejected"),
        },
    )
    def post(self, request: Request) -> Response:
        """Create a new tag. SYSTEM type is rejected."""
        serializer = CreateTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            tag = create_tag(
                name=d["name"],
                slug=d["slug"],
                tag_type=d["tag_type"],
                actor=request.user,
                request=request._request,
                display_label=d.get("display_label", ""),
                display_order=d.get("display_order", 0),
                icon_name=d.get("icon_name", ""),
            )
        except PermissionError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=TagSerializer(tag).data,
            message="Tag created",
            status_code=status.HTTP_201_CREATED,
        )


class TagDetailView(APIView):
    """Retrieve, update, or delete a single tag."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def _get_tag(self, pk: str) -> Tag | None:
        """Fetch tag by PK or return None."""
        try:
            return Tag.objects.annotate(usage_count=Count("vendors")).get(id=pk)
        except Tag.DoesNotExist:
            return None

    @extend_schema(
        tags=["Tags"], summary="Get tag detail", responses={200: TagSerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single tag."""
        tag = self._get_tag(pk)
        if tag is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Tag not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=TagSerializer(tag).data)

    @extend_schema(
        tags=["Tags"],
        summary="Update tag — SYSTEM tags and slug changes rejected",
        request=UpdateTagSerializer,
        responses={200: TagSerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update a tag."""
        tag = self._get_tag(pk)
        if tag is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Tag not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UpdateTagSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            tag = update_tag(
                tag=tag,
                updates=serializer.validated_data,
                actor=request.user,
                request=request._request,
            )
        except PermissionError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=TagSerializer(tag).data)

    @extend_schema(
        tags=["Tags"],
        summary="Delete tag — SYSTEM tags cannot be deleted",
        responses={204: OpenApiResponse(description="Deleted")},
    )
    def delete(self, request: Request, pk: str) -> Response:
        """Delete a tag. SYSTEM tags are rejected."""
        tag = self._get_tag(pk)
        if tag is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Tag not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            delete_tag(tag=tag, actor=request.user, request=request._request)
        except PermissionError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
