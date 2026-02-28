"""
AirAd — tests/factories.py

factory_boy factories for all AirAd models.
Use these in tests instead of raw ORM calls for isolated, repeatable test data.
"""
from __future__ import annotations

import uuid

import factory
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.accounts.models import AdminRole, AdminUser
from apps.analytics.models import AnalyticsEvent, EventType
from apps.audit.models import AuditLog
from apps.field_ops.models import FieldPhoto, FieldVisit
from apps.geo.models import Area, City, Country, Landmark
from apps.imports.models import ImportBatch, ImportStatus
from apps.tags.models import Tag, TagType
from apps.vendors.models import QCStatus, Vendor
from core.encryption import encrypt


class AdminUserFactory(factory.django.DjangoModelFactory):
    """Factory for AdminUser. Default role: DATA_ENTRY."""

    class Meta:
        model = AdminUser

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@test.airaad.com")
    full_name = factory.Sequence(lambda n: f"Test User {n}")
    role = AdminRole.DATA_ENTRY
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(obj, create: bool, extracted: str | None, **kwargs) -> None:
        """Set password after creation. Defaults to TestPass@123!."""
        raw = extracted if extracted is not None else "TestPass@123!"
        obj.set_password(raw)
        if create:
            obj.save(update_fields=["password"])


class CountryFactory(factory.django.DjangoModelFactory):
    """Factory for Country."""

    class Meta:
        model = Country

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Country {n}")
    code = factory.Sequence(lambda n: f"{chr(65 + (n // 26) % 26)}{chr(65 + n % 26)}")


class CityFactory(factory.django.DjangoModelFactory):
    """Factory for City."""

    class Meta:
        model = City

    id = factory.LazyFunction(uuid.uuid4)
    country = factory.SubFactory(CountryFactory)
    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.LazyAttribute(lambda o: f"city-{uuid.uuid4().hex[:8]}")
    centroid = factory.LazyFunction(lambda: Point(67.0099, 24.8607, srid=4326))


class AreaFactory(factory.django.DjangoModelFactory):
    """Factory for Area."""

    class Meta:
        model = Area

    id = factory.LazyFunction(uuid.uuid4)
    city = factory.SubFactory(CityFactory)
    name = factory.Sequence(lambda n: f"Area {n}")
    slug = factory.LazyAttribute(lambda o: f"area-{uuid.uuid4().hex[:8]}")
    centroid = factory.LazyFunction(lambda: Point(67.068, 24.82, srid=4326))


class LandmarkFactory(factory.django.DjangoModelFactory):
    """Factory for Landmark."""

    class Meta:
        model = Landmark

    id = factory.LazyFunction(uuid.uuid4)
    area = factory.SubFactory(AreaFactory)
    name = factory.Sequence(lambda n: f"Landmark {n}")
    slug = factory.Sequence(lambda n: f"landmark-{n}")
    location = factory.LazyFunction(lambda: Point(67.06, 24.827, srid=4326))


class TagFactory(factory.django.DjangoModelFactory):
    """Factory for Tag. Default type: CATEGORY."""

    class Meta:
        model = Tag

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")
    tag_type = TagType.CATEGORY
    is_active = True


class VendorFactory(factory.django.DjangoModelFactory):
    """Factory for Vendor with encrypted phone and valid business hours."""

    class Meta:
        model = Vendor

    id = factory.LazyFunction(uuid.uuid4)
    business_name = factory.Sequence(lambda n: f"Test Vendor {n}")
    slug = factory.LazyAttribute(lambda o: f"test-vendor-{uuid.uuid4().hex[:8]}")
    city = factory.SubFactory(CityFactory)
    area = factory.SubFactory(AreaFactory)
    gps_point = factory.LazyFunction(lambda: Point(67.06, 24.82, srid=4326))
    phone_number_encrypted = factory.LazyFunction(lambda: encrypt("+923001234567"))
    qc_status = QCStatus.PENDING
    is_deleted = False
    claimed_status = "UNCLAIMED"
    storefront_photo_key = ""
    business_hours = factory.LazyFunction(
        lambda: {
            day: {"open": "09:00", "close": "21:00", "is_closed": False}
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    )


class ImportBatchFactory(factory.django.DjangoModelFactory):
    """Factory for ImportBatch. Default status: QUEUED."""

    class Meta:
        model = ImportBatch

    id = factory.LazyFunction(uuid.uuid4)
    created_by = factory.SubFactory(AdminUserFactory)
    file_key = factory.Sequence(lambda n: f"imports/test-batch-{n}.csv")
    status = ImportStatus.QUEUED
    total_rows = 0
    processed_rows = 0
    error_count = 0
    error_log = factory.LazyFunction(list)


class FieldVisitFactory(factory.django.DjangoModelFactory):
    """Factory for FieldVisit with a default GPS confirmed point."""

    class Meta:
        model = FieldVisit

    id = factory.LazyFunction(uuid.uuid4)
    vendor = factory.SubFactory(VendorFactory)
    agent = factory.SubFactory(AdminUserFactory, role=AdminRole.FIELD_AGENT)
    visited_at = factory.LazyFunction(timezone.now)
    gps_confirmed_point = factory.LazyFunction(lambda: Point(67.06, 24.82, srid=4326))
    visit_notes = ""


class FieldPhotoFactory(factory.django.DjangoModelFactory):
    """Factory for FieldPhoto with a unique S3 key."""

    class Meta:
        model = FieldPhoto

    id = factory.LazyFunction(uuid.uuid4)
    field_visit = factory.SubFactory(FieldVisitFactory)
    s3_key = factory.Sequence(lambda n: f"field-photos/test-photo-{n}.jpg")


class AnalyticsEventFactory(factory.django.DjangoModelFactory):
    """Factory for AnalyticsEvent. Default type: VENDOR_VIEW."""

    class Meta:
        model = AnalyticsEvent

    id = factory.LazyFunction(uuid.uuid4)
    event_type = EventType.VENDOR_VIEW
    vendor = factory.SubFactory(VendorFactory)
    actor_id = factory.LazyFunction(uuid.uuid4)
    metadata = factory.LazyFunction(dict)


class AuditLogFactory(factory.django.DjangoModelFactory):
    """Factory for AuditLog. Actor is None by default (Celery context)."""

    class Meta:
        model = AuditLog

    id = factory.LazyFunction(uuid.uuid4)
    actor = None
    actor_label = ""
    action = "TEST_ACTION"
    target_type = "Vendor"
    target_id = factory.LazyFunction(uuid.uuid4)
    before_state = factory.LazyFunction(dict)
    after_state = factory.LazyFunction(dict)
    request_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    ip_address = "127.0.0.1"
