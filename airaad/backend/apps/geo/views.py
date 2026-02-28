"""
AirAd Backend — Geo Views

Zero business logic — all delegated to geo/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
All views decorated with @extend_schema.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response

from .models import Area, City, Country, Landmark
from .serializers import (
    AreaSerializer,
    CitySerializer,
    CountrySerializer,
    LandmarkSerializer,
)
from .services import (
    create_area,
    create_city,
    create_country,
    create_landmark,
    delete_country,
    update_area,
    update_city,
    update_country,
    update_landmark,
)

logger = logging.getLogger(__name__)


class CountryListCreateView(APIView):
    """List all countries or create a new one."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN, AdminRole.CITY_MANAGER
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"],
        summary="List countries",
        responses={200: CountrySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return all active countries."""
        countries = Country.objects.filter(is_active=True).order_by("name")
        return success_response(data=CountrySerializer(countries, many=True).data)

    @extend_schema(
        tags=["Geo"],
        summary="Create country (SUPER_ADMIN, CITY_MANAGER)",
        responses={201: CountrySerializer},
    )
    def post(self, request: Request) -> Response:
        """Create a new country."""
        try:
            country = create_country(
                name=request.data.get("name", ""),
                code=request.data.get("code", ""),
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=CountrySerializer(country).data,
            message="Country created",
            status_code=status.HTTP_201_CREATED,
        )


class CountryDetailView(APIView):
    """Retrieve, update, or delete a single country."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN, AdminRole.CITY_MANAGER
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="Get country detail", responses={200: CountrySerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single country by ID."""
        try:
            country = Country.objects.get(id=pk, is_active=True)
        except Country.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Country not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=CountrySerializer(country).data)

    @extend_schema(
        tags=["Geo"],
        summary="Update country (SUPER_ADMIN, CITY_MANAGER)",
        responses={200: CountrySerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update a country."""
        try:
            country = Country.objects.get(id=pk)
            country = update_country(
                country=country,
                updates=dict(request.data),
                actor=request.user,
                request=request._request,
            )
        except Country.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Country not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=CountrySerializer(country).data)

    @extend_schema(
        tags=["Geo"],
        summary="Delete country (SUPER_ADMIN, CITY_MANAGER)",
        responses={200: None},
    )
    def delete(self, request: Request, pk: str) -> Response:
        """Soft-delete a country."""
        try:
            country = Country.objects.get(id=pk)
            delete_country(
                country=country,
                actor=request.user,
                request=request._request,
            )
        except Country.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Country not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(message="Country deleted")


class CityListCreateView(APIView):
    """List all cities or create a new one."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="List cities", responses={200: CitySerializer(many=True)}
    )
    def get(self, request: Request) -> Response:
        """Return all active cities."""
        cities = (
            City.objects.filter(is_active=True)
            .select_related("country")
            .order_by("display_order", "name")
        )
        return success_response(data=CitySerializer(cities, many=True).data)

    @extend_schema(
        tags=["Geo"],
        summary="Create city (SUPER_ADMIN, CITY_MANAGER)",
        responses={201: CitySerializer},
    )
    def post(self, request: Request) -> Response:
        """Create a new city."""
        try:
            from .models import Country as CountryModel

            country_id = request.data.get("country_id") or request.data.get("country")
            country = CountryModel.objects.get(id=country_id)
            city = create_city(
                country=country,
                name=request.data.get("name", ""),
                slug=request.data.get("slug", ""),
                centroid_lon=request.data.get("centroid_lon")
                or request.data.get("longitude", 0),
                centroid_lat=request.data.get("centroid_lat")
                or request.data.get("latitude", 0),
                actor=request.user,
                request=request._request,
                aliases=request.data.get("aliases", []),
                display_order=request.data.get("display_order", 0),
            )
        except (ValueError, CountryModel.DoesNotExist) as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=CitySerializer(city).data,
            message="City created",
            status_code=status.HTTP_201_CREATED,
        )


class CityDetailView(APIView):
    """Retrieve or update a single city."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="Get city detail", responses={200: CitySerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single city by ID."""
        try:
            city = City.objects.select_related("country").get(id=pk)
        except City.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "City not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=CitySerializer(city).data)

    @extend_schema(
        tags=["Geo"],
        summary="Update city (SUPER_ADMIN, CITY_MANAGER)",
        responses={200: CitySerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update a city. slug is immutable."""
        try:
            city = City.objects.get(id=pk)
            city = update_city(
                city=city,
                updates=dict(request.data),
                actor=request.user,
                request=request._request,
            )
        except City.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "City not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=CitySerializer(city).data)


class AreaListCreateView(APIView):
    """List areas or create a new one."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="List areas", responses={200: AreaSerializer(many=True)}
    )
    def get(self, request: Request) -> Response:
        """Return all active areas, optionally filtered by city."""
        qs = Area.objects.filter(is_active=True).select_related("city")
        city_id = request.query_params.get("city_id")
        if city_id:
            qs = qs.filter(city_id=city_id)
        return success_response(data=AreaSerializer(qs, many=True).data)

    @extend_schema(tags=["Geo"], summary="Create area", responses={201: AreaSerializer})
    def post(self, request: Request) -> Response:
        """Create a new area."""
        try:
            city_id = request.data.get("city_id") or request.data.get("city")
            city = City.objects.get(id=city_id)
            area = create_area(
                city=city,
                name=request.data.get("name", ""),
                slug=request.data.get("slug", ""),
                actor=request.user,
                request=request._request,
                aliases=request.data.get("aliases", []),
                centroid_lon=request.data.get("centroid_lon")
                or request.data.get("longitude"),
                centroid_lat=request.data.get("centroid_lat")
                or request.data.get("latitude"),
            )
        except (ValueError, City.DoesNotExist) as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=AreaSerializer(area).data,
            message="Area created",
            status_code=status.HTTP_201_CREATED,
        )


class AreaDetailView(APIView):
    """Retrieve or update a single area."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="Get area detail", responses={200: AreaSerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single area by ID."""
        try:
            area = Area.objects.select_related("city").get(id=pk)
        except Area.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Area not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=AreaSerializer(area).data)

    @extend_schema(
        tags=["Geo"],
        summary="Update area (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY)",
        responses={200: AreaSerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update an area. slug is immutable."""
        try:
            area = Area.objects.get(id=pk)
            area = update_area(
                area=area,
                updates=dict(request.data),
                actor=request.user,
                request=request._request,
            )
        except Area.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Area not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=AreaSerializer(area).data)


class LandmarkDetailView(APIView):
    """Retrieve or update a single landmark."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"], summary="Get landmark detail", responses={200: LandmarkSerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single landmark by ID."""
        try:
            landmark = Landmark.objects.select_related("area").get(id=pk)
        except Landmark.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Landmark not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=LandmarkSerializer(landmark).data)

    @extend_schema(
        tags=["Geo"],
        summary="Update landmark (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY)",
        responses={200: LandmarkSerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update a landmark. slug is immutable."""
        try:
            landmark = Landmark.objects.get(id=pk)
            landmark = update_landmark(
                landmark=landmark,
                updates=dict(request.data),
                actor=request.user,
                request=request._request,
            )
        except Landmark.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Landmark not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=LandmarkSerializer(landmark).data)


class LandmarkListCreateView(APIView):
    """List landmarks or create a new one."""

    _read_roles = RolePermission.for_roles(*AdminRole.values)
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Geo"],
        summary="List landmarks",
        responses={200: LandmarkSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return all active landmarks, optionally filtered by area."""
        qs = Landmark.objects.filter(is_active=True).select_related("area")
        area_id = request.query_params.get("area_id")
        if area_id:
            qs = qs.filter(area_id=area_id)
        return success_response(data=LandmarkSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Geo"], summary="Create landmark", responses={201: LandmarkSerializer}
    )
    def post(self, request: Request) -> Response:
        """Create a new landmark."""
        try:
            area_id = request.data.get("area_id") or request.data.get("area")
            area = Area.objects.get(id=area_id)
            landmark = create_landmark(
                area=area,
                name=request.data.get("name", ""),
                slug=request.data.get("slug", ""),
                location_lon=request.data.get("location_lon")
                or request.data.get("longitude", 0),
                location_lat=request.data.get("location_lat")
                or request.data.get("latitude", 0),
                actor=request.user,
                request=request._request,
                aliases=request.data.get("aliases", []),
            )
        except (ValueError, Area.DoesNotExist) as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=LandmarkSerializer(landmark).data,
            message="Landmark created",
            status_code=status.HTTP_201_CREATED,
        )
