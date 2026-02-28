"""
AirAd Backend — Discovery Views (Phase B §3.3)

Zero business logic — all delegated to discovery/services.py.
Unauthenticated search endpoints for public discovery.
Voice bot query endpoint requires authentication + feature gate.
"""

import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import success_response

from .services import (
    nearby_vendors,
    search_vendors,
    voice_query_vendor,
    voice_search,
)

logger = logging.getLogger(__name__)


class SearchVendorsView(APIView):
    """GET /api/v1/discovery/search/ — search vendors by location + query + tags."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Discovery"],
        summary="Search vendors by location, query, and tags",
        parameters=[
            OpenApiParameter(name="lat", description="Latitude", required=True, type=float),
            OpenApiParameter(name="lng", description="Longitude", required=True, type=float),
            OpenApiParameter(name="radius", description="Radius in metres (default 2000, max 10000)", required=False, type=float),
            OpenApiParameter(name="q", description="Text search query", required=False, type=str),
            OpenApiParameter(name="tags", description="Comma-separated tag UUIDs", required=False, type=str),
            OpenApiParameter(name="tag_types", description="Comma-separated tag types", required=False, type=str),
        ],
        responses={200: OpenApiResponse(description="Ranked vendor list")},
    )
    def get(self, request: Request) -> Response:
        """Search for vendors near a location with optional text/tag filters.

        Args:
            request: HTTP request with query params.

        Returns:
            200 with ranked list of vendor results.
        """
        try:
            lat = float(request.query_params.get("lat", 0))
            lng = float(request.query_params.get("lng", 0))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "data": None, "message": "lat and lng must be valid numbers", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lat == 0 and lng == 0:
            return Response(
                {"success": False, "data": None, "message": "lat and lng are required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = float(request.query_params.get("radius", 2000))
        query = request.query_params.get("q", "")

        tag_ids = None
        tags_param = request.query_params.get("tags", "")
        if tags_param:
            tag_ids = [t.strip() for t in tags_param.split(",") if t.strip()]

        tag_types = None
        tag_types_param = request.query_params.get("tag_types", "")
        if tag_types_param:
            tag_types = [t.strip() for t in tag_types_param.split(",") if t.strip()]

        results = search_vendors(
            lat=lat,
            lng=lng,
            radius=radius,
            query=query,
            tag_ids=tag_ids,
            tag_types=tag_types,
        )

        return success_response(data=results, message=f"{len(results)} vendors found")


class NearbyVendorsView(APIView):
    """GET /api/v1/discovery/nearby/ — nearby vendors ranked by distance + subscription."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Discovery"],
        summary="Get nearby vendors ranked by distance",
        parameters=[
            OpenApiParameter(name="lat", description="Latitude", required=True, type=float),
            OpenApiParameter(name="lng", description="Longitude", required=True, type=float),
            OpenApiParameter(name="radius", description="Radius in metres (default 2000)", required=False, type=float),
        ],
        responses={200: OpenApiResponse(description="Nearby vendor list")},
    )
    def get(self, request: Request) -> Response:
        """Return nearby vendors ordered by distance with subscription boost.

        Args:
            request: HTTP request with lat/lng params.

        Returns:
            200 with nearby vendor results.
        """
        try:
            lat = float(request.query_params.get("lat", 0))
            lng = float(request.query_params.get("lng", 0))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "data": None, "message": "lat and lng must be valid numbers", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lat == 0 and lng == 0:
            return Response(
                {"success": False, "data": None, "message": "lat and lng are required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = float(request.query_params.get("radius", 2000))
        results = nearby_vendors(lat=lat, lng=lng, radius=radius)

        return success_response(data=results, message=f"{len(results)} vendors found")


class VoiceSearchView(APIView):
    """POST /api/v1/discovery/voice-search/ — rule-based NLP voice search."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Discovery"],
        summary="Voice search — rule-based NLP, no ML",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "transcript": {"type": "string"},
                    "radius": {"type": "number"},
                },
                "required": ["lat", "lng", "transcript"],
            }
        },
        responses={200: OpenApiResponse(description="Ranked vendor list from voice query")},
    )
    def post(self, request: Request) -> Response:
        """Process a voice search transcript and return ranked vendors.

        Args:
            request: HTTP request with lat, lng, transcript.

        Returns:
            200 with ranked vendor results.
        """
        try:
            lat = float(request.data.get("lat", 0))
            lng = float(request.data.get("lng", 0))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "data": None, "message": "lat and lng must be valid numbers", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transcript = request.data.get("transcript", "")
        if not transcript:
            return Response(
                {"success": False, "data": None, "message": "transcript is required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = float(request.data.get("radius", 2000))

        results = voice_search(
            lat=lat,
            lng=lng,
            transcript=transcript,
            radius=radius,
        )

        return success_response(data=results, message=f"{len(results)} vendors found")


class VoiceQueryVendorView(APIView):
    """POST /api/v1/vendors/{slug}/voice-query/ — ask a specific vendor a question."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Discovery"],
        summary="Voice query a specific vendor (requires VOICE_BOT feature)",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
            }
        },
        responses={
            200: OpenApiResponse(description="Voice bot answer"),
            400: OpenApiResponse(description="Feature not available or vendor not found"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        """Ask a voice question about a specific vendor.

        Args:
            request: Authenticated HTTP request with question.
            slug: Vendor slug.

        Returns:
            200 with answer from VoiceBotConfig.
        """
        question = request.data.get("question", "")
        if not question:
            return Response(
                {"success": False, "data": None, "message": "question is required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = voice_query_vendor(vendor_slug=slug, question=question)
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Voice query answered")


class NearbyReelsView(APIView):
    """GET /api/v1/discovery/nearby/reels/ — nearby reels feed (§B-8).

    Returns approved, active reels from vendors near the given lat/lng.
    Used by the Flutter customer app TikTok-style vertical feed.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Discovery"],
        summary="Nearby vendor reels feed",
        parameters=[
            OpenApiParameter(name="lat", type=float, required=True),
            OpenApiParameter(name="lng", type=float, required=True),
            OpenApiParameter(name="radius", type=int, required=False, description="Radius in metres (default 5000)"),
            OpenApiParameter(name="limit", type=int, required=False, description="Max results (default 20)"),
        ],
        responses={200: OpenApiResponse(description="List of nearby reels")},
    )
    def get(self, request: Request) -> Response:
        """Return nearby reels based on lat/lng."""
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")

        if not lat or not lng:
            return Response(
                {"success": False, "data": None, "message": "lat and lng are required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "data": None, "message": "Invalid lat/lng values", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = int(request.query_params.get("radius", 5000))
        limit = min(int(request.query_params.get("limit", 20)), 50)

        from .services import get_nearby_reels

        results = get_nearby_reels(lat=lat_f, lng=lng_f, radius_m=radius, limit=limit)
        return success_response(data=results, message=f"{len(results)} nearby reels found")
