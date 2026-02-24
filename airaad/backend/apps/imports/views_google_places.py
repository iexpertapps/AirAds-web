"""
POST /api/v1/imports/google-places/

Request body:
  { "area_id": "<uuid>", "search_query": "restaurants food", "radius_m": 1500 }

Response 202:
  { "success": true, "data": { "batch_id": "...", "status": "QUEUED", "poll_url": "..." } }
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from apps.geo.models import Area
from apps.imports.models import ImportBatch
from apps.imports.tasks_google_places import process_google_places_import
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class GooglePlacesImportRequestSerializer(serializers.Serializer):
    area_id = serializers.UUIDField()
    search_query = serializers.CharField(max_length=255, default="restaurants food")
    radius_m = serializers.IntegerField(min_value=100, max_value=5000, default=1500)

    def validate_area_id(self, value):
        try:
            return Area.objects.get(id=value)
        except Area.DoesNotExist:
            raise serializers.ValidationError(f"Area {value} does not exist.")


class GooglePlacesImportView(APIView):
    """POST /api/v1/imports/google-places/"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN, AdminRole.CITY_MANAGER, AdminRole.OPERATIONS_MANAGER
        )
    ]

    def post(self, request):
        ser = GooglePlacesImportRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Validation failed",
                    "errors": ser.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        vd = ser.validated_data
        area: Area = vd["area_id"]  # validate_area_id returns Area object

        centroid = getattr(area, "centroid", None)
        if not centroid:
            return Response(
                {
                    "success": False,
                    "message": f"Area '{area.name}' has no centroid. Set area.centroid first.",
                    "errors": {"area_id": ["Area centroid required."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Batch-level dedup ─────────────────────────────────────────
        in_flight = ImportBatch.objects.filter(
            area=area,
            search_query=vd["search_query"],
            radius_m=vd["radius_m"],
            status__in=["QUEUED", "PROCESSING"],
        ).first()
        if in_flight:
            return Response(
                {
                    "success": False,
                    "data": {
                        "existing_batch_id": str(in_flight.id),
                        "status": in_flight.status,
                    },
                    "message": (
                        f"An identical import for area '{area.name}' is already {in_flight.status}. "
                        f"Wait for it to finish or cancel it first."
                    ),
                    "errors": {"area_id": ["Duplicate in-flight batch"]},
                },
                status=status.HTTP_409_CONFLICT,
            )

        batch = ImportBatch.objects.create(
            import_type="GOOGLE_PLACES",
            area=area,
            search_query=vd["search_query"],
            radius_m=vd["radius_m"],
            search_lat=centroid.y,  # PostGIS Point(lng,lat) -> .y = lat
            search_lng=centroid.x,
            status="QUEUED",
            created_by=request.user,
        )

        # Pass ONLY batch_id to Celery — never raw data
        process_google_places_import.delay(str(batch.id))
        logger.info(
            f"Google Places import queued | batch={batch.id} | area={area.name}"
        )

        return Response(
            {
                "success": True,
                "data": {
                    "batch_id": str(batch.id),
                    "status": "QUEUED",
                    "area": area.name,
                    "search_query": vd["search_query"],
                    "radius_m": vd["radius_m"],
                    "poll_url": f"/api/v1/imports/{batch.id}/",
                },
                "message": "Import queued. Poll poll_url for progress.",
                "errors": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )
