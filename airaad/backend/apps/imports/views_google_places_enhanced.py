"""
Enhanced Google Places Import with County->City->Area->Category Selection

POST /api/v1/imports/google-places/enhanced/

Request body:
{
  "country_id": "<uuid>",
  "city_id": "<uuid>",
  "area_id": "<uuid>",
  "category_tags": ["<uuid>", "<uuid>"],
  "search_query": "restaurants food",
  "radius_m": 1500
}

Response 202:
{
  "success": true,
  "data": {
    "batch_id": "...",
    "status": "QUEUED",
    "poll_url": "..."
  }
}
"""

import logging

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from apps.geo.models import Area, City, Country
from apps.imports.models import ImportBatch
from apps.imports.tasks_google_places import process_google_places_import
from apps.tags.models import Tag, TagType

logger = logging.getLogger(__name__)


class EnhancedGooglePlacesImportRequestSerializer(serializers.Serializer):
    country_id = serializers.UUIDField(required=True)
    city_id = serializers.UUIDField(required=True)
    area_id = serializers.UUIDField(required=True)
    category_tags = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of category tag UUIDs to filter import by",
    )
    search_query = serializers.CharField(
        max_length=255,
        default="restaurants food",
        help_text="Search query for Google Places API",
    )
    radius_m = serializers.IntegerField(
        min_value=100, max_value=5000, default=1500, help_text="Search radius in meters"
    )

    def validate_country_id(self, value):
        try:
            return Country.objects.get(id=value, is_active=True)
        except Country.DoesNotExist:
            raise serializers.ValidationError(f"Active country {value} does not exist.")

    def validate_city_id(self, value):
        try:
            return City.objects.get(id=value, is_active=True)
        except City.DoesNotExist:
            raise serializers.ValidationError(f"Active city {value} does not exist.")

    def validate_area_id(self, value):
        try:
            return Area.objects.get(id=value, is_active=True)
        except Area.DoesNotExist:
            raise serializers.ValidationError(f"Active area {value} does not exist.")

    def validate_category_tags(self, value):
        """Validate that all category tags exist and are of type CATEGORY."""
        if not value:
            return []

        tag_uuids = value
        tags = Tag.objects.filter(
            id__in=tag_uuids, tag_type=TagType.CATEGORY, is_active=True
        )

        if len(tags) != len(tag_uuids):
            found_ids = set(str(tag.id) for tag in tags)
            missing_ids = set(str(uuid) for uuid in tag_uuids) - found_ids
            raise serializers.ValidationError(
                f"Invalid or inactive category tag IDs: {list(missing_ids)}"
            )

        return tags

    def validate(self, attrs):
        """Validate geo hierarchy consistency."""
        country = attrs["country_id"]
        city = attrs["city_id"]
        area = attrs["area_id"]

        # Validate city belongs to country
        if city.country != country:
            raise serializers.ValidationError(
                {
                    "city_id": f"City {city.name} does not belong to country {country.name}"
                }
            )

        # Validate area belongs to city
        if area.city != city:
            raise serializers.ValidationError(
                {"area_id": f"Area {area.name} does not belong to city {city.name}"}
            )

        # Validate area has centroid for GPS search
        if not area.centroid:
            raise serializers.ValidationError(
                {"area_id": f"Area {area.name} has no centroid coordinates set"}
            )

        return attrs


class EnhancedGooglePlacesImportView(APIView):
    """Enhanced Google Places Import with County->City->Area->Category selection.

    Allows OPERATIONS_MANAGER to seed data from Google Places by selecting:
    - Country (County level)
    - City
    - Area
    - Category tags (optional filtering)
    """

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN, AdminRole.CITY_MANAGER, AdminRole.OPERATIONS_MANAGER
        )
    ]

    def post(self, request):
        """Create enhanced Google Places import batch with category filtering.

        Batch-level dedup: rejects if an identical area + query batch is
        already QUEUED or PROCESSING, preventing duplicate API spend.
        """
        serializer = EnhancedGooglePlacesImportRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Validation failed",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data
        country = validated_data["country_id"]
        city = validated_data["city_id"]
        area = validated_data["area_id"]
        category_tags = validated_data["category_tags"]
        search_query = validated_data["search_query"]
        radius_m = validated_data["radius_m"]

        # Enhance search query with category tags if provided
        enhanced_search_query = search_query
        if category_tags:
            category_names = [tag.name for tag in category_tags]
            enhanced_search_query = f"{search_query} {' '.join(category_names)}"

        # ── Batch-level dedup ─────────────────────────────────────────
        # Reject if an identical area + query batch is already in-flight.
        in_flight = ImportBatch.objects.filter(
            area=area,
            search_query=enhanced_search_query,
            radius_m=radius_m,
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
                        f"An identical import for area '{area.name}' with the same query "
                        f"is already {in_flight.status}. Wait for it to finish or cancel it first."
                    ),
                    "errors": {"area_id": ["Duplicate in-flight batch"]},
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Create import batch
        batch = ImportBatch.objects.create(
            import_type="GOOGLE_PLACES_ENHANCED",
            area=area,
            search_query=enhanced_search_query,
            radius_m=radius_m,
            search_lat=area.centroid.y,  # PostGIS Point(lng,lat) -> .y = lat
            search_lng=area.centroid.x,
            status="QUEUED",
            created_by=request.user,
            # Store additional metadata for enhanced processing
            metadata={
                "country_id": str(country.id),
                "country_name": country.name,
                "city_id": str(city.id),
                "city_name": city.name,
                "area_id": str(area.id),
                "area_name": area.name,
                "category_tags": [
                    {"id": str(tag.id), "name": tag.name} for tag in category_tags
                ],
                "original_search_query": search_query,
                "enhanced_search_query": enhanced_search_query,
            },
        )

        # Queue the import task
        process_google_places_import.delay(str(batch.id))

        logger.info(
            f"Enhanced Google Places import queued | "
            f"batch={batch.id} | "
            f"country={country.name} | "
            f"city={city.name} | "
            f"area={area.name} | "
            f"categories={[tag.name for tag in category_tags]} | "
            f"user={request.user.email}"
        )

        return Response(
            {
                "success": True,
                "data": {
                    "batch_id": str(batch.id),
                    "status": "QUEUED",
                    "country": country.name,
                    "city": city.name,
                    "area": area.name,
                    "categories": [tag.name for tag in category_tags],
                    "search_query": enhanced_search_query,
                    "radius_m": radius_m,
                    "poll_url": f"/api/v1/imports/{batch.id}/",
                },
                "message": "Enhanced Google Places import queued successfully. Poll poll_url for progress.",
                "errors": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )
