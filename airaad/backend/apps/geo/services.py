"""
AirAd Backend — Geo Service Layer (R4)

All geo business logic lives here. Views delegate entirely to these functions.
slug fields are immutable after creation — enforced here, not in models.
Every mutation calls log_action() (R5).
Multi-step mutations wrapped in @transaction.atomic.
"""

import logging
from typing import Any

from apps.audit.utils import log_action
from django.db import transaction
from django.http import HttpRequest

from .models import Area, City, Country, Landmark

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Country
# ---------------------------------------------------------------------------


def create_country(
    name: str,
    code: str,
    actor: Any,
    request: HttpRequest,
) -> Country:
    """Create a new Country record.

    Args:
        name: Full country name.
        code: ISO 3166-1 alpha-2 code (2 chars, uppercase).
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Newly created Country instance.

    Raises:
        ValueError: If code is not 2 characters or country already exists.
    """
    code = code.upper().strip()
    if len(code) != 2:
        raise ValueError(f"Country code must be exactly 2 characters, got '{code}'")
    if Country.objects.filter(code=code).exists():
        raise ValueError(f"Country with code '{code}' already exists")

    country = Country.objects.create(name=name.strip(), code=code)
    log_action(
        action="COUNTRY_CREATED",
        actor=actor,
        target_obj=country,
        request=request,
        before={},
        after={"name": country.name, "code": country.code},
    )
    return country


# ---------------------------------------------------------------------------
# City
# ---------------------------------------------------------------------------


@transaction.atomic
def create_city(
    country: Country,
    name: str,
    slug: str,
    centroid_lon: float,
    centroid_lat: float,
    actor: Any,
    request: HttpRequest,
    aliases: list[str] | None = None,
    display_order: int = 0,
) -> City:
    """Create a new City with a GPS centroid.

    slug is set on creation and is immutable thereafter.
    centroid is stored as a PostGIS Point(longitude, latitude) — lon/lat order.

    Args:
        country: Parent Country instance.
        name: City name.
        slug: URL-safe slug — immutable after creation.
        centroid_lon: Longitude of the city centre.
        centroid_lat: Latitude of the city centre.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        aliases: Optional list of alternate names.
        display_order: UI ordering integer.

    Returns:
        Newly created City instance.

    Raises:
        ValueError: If slug is already in use.
    """
    from django.contrib.gis.geos import Point

    if aliases is None:
        aliases = []

    slug = slug.strip()
    if City.objects.filter(slug=slug).exists():
        raise ValueError(f"City with slug '{slug}' already exists")

    city = City.objects.create(
        country=country,
        name=name.strip(),
        slug=slug,
        aliases=aliases,
        centroid=Point(centroid_lon, centroid_lat, srid=4326),  # lon/lat order
        display_order=display_order,
    )
    log_action(
        action="CITY_CREATED",
        actor=actor,
        target_obj=city,
        request=request,
        before={},
        after={"name": city.name, "slug": city.slug, "country": str(country.id)},
    )
    return city


@transaction.atomic
def update_city(
    city: City,
    updates: dict[str, Any],
    actor: Any,
    request: HttpRequest,
) -> City:
    """Update a City record. slug is immutable and cannot be changed.

    Args:
        city: City instance to update.
        updates: Dict of field names to new values. 'slug' is rejected.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Updated City instance.

    Raises:
        ValueError: If 'slug' is included in updates.
    """
    if "slug" in updates:
        raise ValueError("City slug is immutable and cannot be changed after creation")

    before = {
        "name": city.name,
        "aliases": city.aliases,
        "display_order": city.display_order,
        "is_active": city.is_active,
    }

    allowed_fields = {
        "name",
        "aliases",
        "display_order",
        "is_active",
        "centroid",
        "bounding_box",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(city, field, value)

    city.save()
    log_action(
        action="CITY_UPDATED",
        actor=actor,
        target_obj=city,
        request=request,
        before=before,
        after={"name": city.name, "is_active": city.is_active},
    )
    return city


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------


@transaction.atomic
def create_area(
    city: City,
    name: str,
    slug: str,
    actor: Any,
    request: HttpRequest,
    parent_area: Area | None = None,
    aliases: list[str] | None = None,
    centroid_lon: float | None = None,
    centroid_lat: float | None = None,
) -> Area:
    """Create a new Area within a city.

    Args:
        city: Parent City instance.
        name: Area name.
        slug: URL-safe slug — immutable after creation.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        parent_area: Optional parent Area for nested hierarchy.
        aliases: Optional list of alternate names (spec §2.3: no duplicates within same city).
        centroid_lon: Optional longitude of area centre.
        centroid_lat: Optional latitude of area centre.

    Returns:
        Newly created Area instance.

    Raises:
        ValueError: If slug is already in use or an alias already exists in the same city.
    """
    from django.contrib.gis.geos import Point

    if aliases is None:
        aliases = []

    slug = slug.strip()
    if Area.objects.filter(slug=slug).exists():
        raise ValueError(f"Area with slug '{slug}' already exists")

    # Spec §2.3: no duplicate aliases across locations in same city
    normalised = [a.lower().strip() for a in aliases]
    existing_areas = Area.objects.filter(city=city).values_list("aliases", flat=True)
    for existing_aliases in existing_areas:
        for existing in existing_aliases:
            if existing.lower().strip() in normalised:
                raise ValueError(
                    f"Alias '{existing}' already exists in another area within the same city."
                )

    centroid = None
    if centroid_lon is not None and centroid_lat is not None:
        centroid = Point(centroid_lon, centroid_lat, srid=4326)

    area = Area.objects.create(
        city=city,
        parent_area=parent_area,
        name=name.strip(),
        slug=slug,
        aliases=aliases,
        centroid=centroid,
    )
    log_action(
        action="AREA_CREATED",
        actor=actor,
        target_obj=area,
        request=request,
        before={},
        after={"name": area.name, "slug": area.slug, "city": str(city.id)},
    )
    return area


@transaction.atomic
def update_area(
    area: Area,
    updates: dict[str, Any],
    actor: Any,
    request: HttpRequest,
) -> Area:
    """Update an Area record. slug is immutable and cannot be changed.

    Args:
        area: Area instance to update.
        updates: Dict of field names to new values. 'slug' is rejected.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Updated Area instance.

    Raises:
        ValueError: If 'slug' is included in updates.
    """
    if "slug" in updates:
        raise ValueError("Area slug is immutable and cannot be changed after creation")

    before = {
        "name": area.name,
        "aliases": area.aliases,
        "is_active": area.is_active,
    }

    allowed_fields = {
        "name",
        "aliases",
        "is_active",
        "centroid",
        "boundary_polygon",
        "parent_area",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(area, field, value)

    area.save()
    log_action(
        action="AREA_UPDATED",
        actor=actor,
        target_obj=area,
        request=request,
        before=before,
        after={"name": area.name, "is_active": area.is_active},
    )
    return area


# ---------------------------------------------------------------------------
# Landmark
# ---------------------------------------------------------------------------


@transaction.atomic
def create_landmark(
    area: Area,
    name: str,
    slug: str,
    location_lon: float,
    location_lat: float,
    actor: Any,
    request: HttpRequest,
    aliases: list[str] | None = None,
) -> Landmark:
    """Create a new Landmark within an area.

    Args:
        area: Parent Area instance.
        name: Landmark name.
        slug: URL-safe slug — immutable after creation.
        location_lon: Longitude of the landmark.
        location_lat: Latitude of the landmark.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        aliases: Optional list of alternate names (seed data provides ≥3).
            spec §2.3: no duplicate aliases across locations in same city.

    Returns:
        Newly created Landmark instance.

    Raises:
        ValueError: If slug is already in use or an alias already exists in the same city.
    """
    from django.contrib.gis.geos import Point

    if aliases is None:
        aliases = []

    slug = slug.strip()
    if Landmark.objects.filter(slug=slug).exists():
        raise ValueError(f"Landmark with slug '{slug}' already exists")

    # Spec §2.3: no duplicate aliases across locations in same city
    normalised = [a.lower().strip() for a in aliases]
    city = area.city
    existing_landmarks = Landmark.objects.filter(area__city=city).values_list(
        "aliases", flat=True
    )
    for existing_aliases in existing_landmarks:
        for existing in existing_aliases:
            if existing.lower().strip() in normalised:
                raise ValueError(
                    f"Alias '{existing}' already exists in another landmark within the same city."
                )

    landmark = Landmark.objects.create(
        area=area,
        name=name.strip(),
        slug=slug,
        aliases=aliases,
        location=Point(location_lon, location_lat, srid=4326),
    )
    log_action(
        action="LANDMARK_CREATED",
        actor=actor,
        target_obj=landmark,
        request=request,
        before={},
        after={"name": landmark.name, "slug": landmark.slug, "area": str(area.id)},
    )
    return landmark


@transaction.atomic
def update_landmark(
    landmark: Landmark,
    updates: dict[str, Any],
    actor: Any,
    request: HttpRequest,
) -> Landmark:
    """Update a Landmark record. slug is immutable and cannot be changed.

    Args:
        landmark: Landmark instance to update.
        updates: Dict of field names to new values. 'slug' is rejected.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Updated Landmark instance.

    Raises:
        ValueError: If 'slug' is included in updates.
    """
    if "slug" in updates:
        raise ValueError(
            "Landmark slug is immutable and cannot be changed after creation"
        )

    before = {
        "name": landmark.name,
        "aliases": landmark.aliases,
        "is_active": landmark.is_active,
    }

    allowed_fields = {"name", "aliases", "is_active", "ar_anchor_points"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(landmark, field, value)

    landmark.save()
    log_action(
        action="LANDMARK_UPDATED",
        actor=actor,
        target_obj=landmark,
        request=request,
        before=before,
        after={"name": landmark.name, "is_active": landmark.is_active},
    )
    return landmark
