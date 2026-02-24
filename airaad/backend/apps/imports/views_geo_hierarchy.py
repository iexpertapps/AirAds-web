"""
Helper Views for Enhanced Google Places Import
Provides endpoints for frontend dropdowns: Country->City->Area->Category
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from apps.geo.models import Area, City, Country
from apps.tags.models import Tag, TagType
from core.exceptions import success_response
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code", "is_active"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "is_active", "display_order"]


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name", "slug", "is_active", "parent_area_id"]


class CategoryTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "display_label", "display_order", "icon_name"]


class CountriesListView(APIView):
    """GET /api/v1/imports/geo/countries/ - List active countries"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def get(self, request):
        countries = Country.objects.filter(is_active=True).order_by("name")
        serializer = CountrySerializer(countries, many=True)
        return success_response(data=serializer.data)


class CitiesByCountryView(APIView):
    """GET /api/v1/imports/geo/countries/{country_id}/cities/ - List cities by country"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def get(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id, is_active=True)
        except Country.DoesNotExist:
            return Response(
                {"success": False, "message": "Country not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        cities = City.objects.filter(country=country, is_active=True).order_by(
            "display_order", "name"
        )
        serializer = CitySerializer(cities, many=True)
        return success_response(data=serializer.data)


class AreasByCityView(APIView):
    """GET /api/v1/imports/geo/cities/{city_id}/areas/ - List areas by city"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def get(self, request, city_id):
        try:
            city = City.objects.get(id=city_id, is_active=True)
        except City.DoesNotExist:
            return Response(
                {"success": False, "message": "City not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        areas = Area.objects.filter(city=city, is_active=True).order_by("name")
        serializer = AreaSerializer(areas, many=True)
        return success_response(data=serializer.data)


class CategoryTagsListView(APIView):
    """GET /api/v1/imports/tags/categories/ - List active category tags"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def get(self, request):
        tags = Tag.objects.filter(tag_type=TagType.CATEGORY, is_active=True).order_by(
            "display_order", "name"
        )
        serializer = CategoryTagSerializer(tags, many=True)
        return success_response(data=serializer.data)


class AreaWithCentroidView(APIView):
    """GET /api/v1/imports/geo/areas/{area_id}/ - Get area details with centroid info"""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    def get(self, request, area_id):
        try:
            area = Area.objects.select_related("city", "city__country").get(
                id=area_id, is_active=True
            )
        except Area.DoesNotExist:
            return Response(
                {"success": False, "message": "Area not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "id": str(area.id),
            "name": area.name,
            "slug": area.slug,
            "city": {
                "id": str(area.city.id),
                "name": area.city.name,
                "slug": area.city.slug,
            },
            "country": {
                "id": str(area.city.country.id),
                "name": area.city.country.name,
                "code": area.city.country.code,
            },
            "has_centroid": bool(area.centroid),
            "centroid": (
                {"lat": area.centroid.y, "lng": area.centroid.x}
                if area.centroid
                else None
            ),
            "parent_area_id": str(area.parent_area.id) if area.parent_area else None,
        }

        return success_response(data=data)
