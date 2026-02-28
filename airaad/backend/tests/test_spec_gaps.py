"""
AirAd — tests/test_spec_gaps.py

Regression tests for all gaps identified in the spec alignment review
against 01_AirAd_Data_Collection_and_Seed_Data.docx.

Gap #1  — Area.boundary_polygon field exists
Gap #2  — Landmark.ar_anchor_points field exists
Gap #3  — Alias uniqueness within city enforced in geo/services.py
Gap #4  — Vendor.claimed_status field exists, defaults UNCLAIMED
Gap #5  — Vendor.storefront_photo_key field exists
Gap #7  — GPS coordinate range validation in CSV import
Gap #8  — Tag.expires_at field + expire_promotion_tags task deactivates expired tags
Gap #9  — Layer 4 generate_time_context_tags task is registered (no-op scaffold)
Gap #10 — Seed tag taxonomy covers all spec-defined tag names
Gap #12 — AnalyticsEvent model exists with correct event types
Gap #14 — GDPR data export endpoint returns account + audit data
Gap #14 — GDPR account deletion endpoint anonymises personal data
"""

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Gap #1 — Area.boundary_polygon
# ---------------------------------------------------------------------------

class TestAreaBoundaryPolygon:
    def test_boundary_polygon_field_exists(self):
        from apps.geo.models import Area
        assert hasattr(Area, "boundary_polygon"), "Area must have boundary_polygon field"

    def test_boundary_polygon_nullable(self):
        from tests.factories import AreaFactory
        area = AreaFactory()
        assert area.boundary_polygon is None

    def test_boundary_polygon_can_be_set(self):
        from django.contrib.gis.geos import Polygon
        from tests.factories import AreaFactory
        poly = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)), srid=4326)
        area = AreaFactory(boundary_polygon=poly)
        area.refresh_from_db()
        assert area.boundary_polygon is not None


# ---------------------------------------------------------------------------
# Gap #2 — Landmark.ar_anchor_points
# ---------------------------------------------------------------------------

class TestLandmarkArAnchorPoints:
    def test_ar_anchor_points_field_exists(self):
        from apps.geo.models import Landmark
        assert hasattr(Landmark, "ar_anchor_points"), "Landmark must have ar_anchor_points field"

    def test_ar_anchor_points_defaults_empty_list(self):
        from tests.factories import LandmarkFactory
        lm = LandmarkFactory()
        assert lm.ar_anchor_points == []

    def test_ar_anchor_points_can_store_coordinates(self):
        from tests.factories import LandmarkFactory
        anchors = [{"lon": 67.06, "lat": 24.82}, {"lon": 67.07, "lat": 24.83}]
        lm = LandmarkFactory(ar_anchor_points=anchors)
        lm.refresh_from_db()
        assert len(lm.ar_anchor_points) == 2
        assert lm.ar_anchor_points[0]["lon"] == 67.06


# ---------------------------------------------------------------------------
# Gap #3 — Alias uniqueness within city
# ---------------------------------------------------------------------------

class TestAliasUniquenessWithinCity:
    def test_duplicate_area_alias_in_same_city_raises(self):
        from apps.geo.services import create_area
        from tests.factories import AdminUserFactory, CityFactory

        city = CityFactory()
        actor = AdminUserFactory()
        create_area(
            city=city, name="Area One", slug=f"area-one-{city.id.hex[:6]}",
            actor=actor, request=None, aliases=["Shared Alias"],
        )
        with pytest.raises(ValueError, match="already exists in another area"):
            create_area(
                city=city, name="Area Two", slug=f"area-two-{city.id.hex[:6]}",
                actor=actor, request=None, aliases=["shared alias"],
            )

    def test_same_alias_in_different_city_is_allowed(self):
        from apps.geo.services import create_area
        from tests.factories import AdminUserFactory, CityFactory

        city1 = CityFactory()
        city2 = CityFactory()
        actor = AdminUserFactory()
        create_area(
            city=city1, name="Area A", slug=f"area-a-{city1.id.hex[:6]}",
            actor=actor, request=None, aliases=["Common Name"],
        )
        area2 = create_area(
            city=city2, name="Area B", slug=f"area-b-{city2.id.hex[:6]}",
            actor=actor, request=None, aliases=["Common Name"],
        )
        assert area2.pk is not None

    def test_duplicate_landmark_alias_in_same_city_raises(self):
        from apps.geo.services import create_landmark
        from tests.factories import AdminUserFactory, AreaFactory

        area = AreaFactory()
        actor = AdminUserFactory()
        create_landmark(
            area=area, name="LM One", slug=f"lm-one-{area.id.hex[:6]}",
            location_lon=67.06, location_lat=24.82,
            actor=actor, request=None, aliases=["Shared LM Alias"],
        )
        with pytest.raises(ValueError, match="already exists in another landmark"):
            create_landmark(
                area=area, name="LM Two", slug=f"lm-two-{area.id.hex[:6]}",
                location_lon=67.07, location_lat=24.83,
                actor=actor, request=None, aliases=["shared lm alias"],
            )


# ---------------------------------------------------------------------------
# Gap #4 — Vendor.claimed_status
# ---------------------------------------------------------------------------

class TestVendorClaimedStatus:
    def test_claimed_status_field_exists(self):
        from apps.vendors.models import Vendor
        assert hasattr(Vendor, "claimed_status"), "Vendor must have claimed_status field"

    def test_claimed_status_defaults_unclaimed(self):
        from tests.factories import VendorFactory
        vendor = VendorFactory()
        assert vendor.claimed_status == "UNCLAIMED"

    def test_claimed_status_can_be_set_claimed(self):
        from tests.factories import VendorFactory
        vendor = VendorFactory(claimed_status="CLAIMED")
        vendor.refresh_from_db()
        assert vendor.claimed_status == "CLAIMED"

    def test_claimed_status_exposed_in_serializer(self):
        from apps.vendors.serializers import VendorSerializer
        from tests.factories import VendorFactory
        vendor = VendorFactory()
        data = VendorSerializer(vendor).data
        assert "claimed_status" in data
        assert data["claimed_status"] == "UNCLAIMED"


# ---------------------------------------------------------------------------
# Gap #5 — Vendor.storefront_photo_key
# ---------------------------------------------------------------------------

class TestVendorStorefrontPhotoKey:
    def test_storefront_photo_key_field_exists(self):
        from apps.vendors.models import Vendor
        assert hasattr(Vendor, "storefront_photo_key"), "Vendor must have storefront_photo_key field"

    def test_storefront_photo_key_defaults_blank(self):
        from tests.factories import VendorFactory
        vendor = VendorFactory()
        assert vendor.storefront_photo_key == ""

    def test_storefront_photo_url_in_serializer_returns_empty_when_no_key(self):
        from apps.vendors.serializers import VendorSerializer
        from tests.factories import VendorFactory
        vendor = VendorFactory(storefront_photo_key="")
        data = VendorSerializer(vendor).data
        assert "storefront_photo_url" in data
        assert data["storefront_photo_url"] == ""


# ---------------------------------------------------------------------------
# Gap #7 — GPS coordinate range validation in CSV import
# ---------------------------------------------------------------------------

class TestGPSCoordinateValidation:
    def _validate(self, row, row_num=1):
        from apps.imports.tasks import _validate_row
        return _validate_row(row, row_num)

    def test_valid_coordinates_pass(self):
        row = {
            "business_name": "Test Shop",
            "longitude": "67.06",
            "latitude": "24.82",
            "city_slug": "karachi",
            "area_slug": "dha",
        }
        assert self._validate(row) == []

    def test_out_of_range_longitude_fails(self):
        row = {
            "business_name": "Test Shop",
            "longitude": "200.0",
            "latitude": "24.82",
            "city_slug": "karachi",
            "area_slug": "dha",
        }
        errors = self._validate(row)
        assert any("out of valid range" in e["msg"] for e in errors)

    def test_out_of_range_latitude_fails(self):
        row = {
            "business_name": "Test Shop",
            "longitude": "67.06",
            "latitude": "95.0",
            "city_slug": "karachi",
            "area_slug": "dha",
        }
        errors = self._validate(row)
        assert any("out of valid range" in e["msg"] for e in errors)

    def test_zero_longitude_fails_as_null_island(self):
        row = {
            "business_name": "Test Shop",
            "longitude": "0.0",
            "latitude": "24.82",
            "city_slug": "karachi",
            "area_slug": "dha",
        }
        errors = self._validate(row)
        assert any("null-island" in e["msg"] for e in errors)

    def test_zero_latitude_fails_as_null_island(self):
        row = {
            "business_name": "Test Shop",
            "longitude": "67.06",
            "latitude": "0.0",
            "city_slug": "karachi",
            "area_slug": "dha",
        }
        errors = self._validate(row)
        assert any("null-island" in e["msg"] for e in errors)


# ---------------------------------------------------------------------------
# Gap #8 — Tag.expires_at + expire_promotion_tags task
# ---------------------------------------------------------------------------

class TestTagExpiresAt:
    def test_expires_at_field_exists(self):
        from apps.tags.models import Tag
        assert hasattr(Tag, "expires_at"), "Tag must have expires_at field"

    def test_expires_at_defaults_null(self):
        from tests.factories import TagFactory
        tag = TagFactory()
        assert tag.expires_at is None

    def test_expires_at_can_be_set(self):
        from datetime import timedelta
        from tests.factories import TagFactory
        future = timezone.now() + timedelta(hours=2)
        tag = TagFactory(expires_at=future)
        tag.refresh_from_db()
        assert tag.expires_at is not None


class TestExpirePromotionTagsTask:
    def test_expired_promotion_tag_is_deactivated(self):
        from datetime import timedelta

        from apps.tags.models import TagType
        from apps.tags.tasks import expire_promotion_tags
        from tests.factories import TagFactory

        past = timezone.now() - timedelta(minutes=10)
        tag = TagFactory(
            tag_type=TagType.PROMOTION,
            is_active=True,
            expires_at=past,
        )
        expire_promotion_tags.apply()
        tag.refresh_from_db()
        assert tag.is_active is False

    def test_non_expired_promotion_tag_stays_active(self):
        from datetime import timedelta

        from apps.tags.models import TagType
        from apps.tags.tasks import expire_promotion_tags
        from tests.factories import TagFactory

        future = timezone.now() + timedelta(hours=2)
        tag = TagFactory(
            tag_type=TagType.PROMOTION,
            is_active=True,
            expires_at=future,
        )
        expire_promotion_tags.apply()
        tag.refresh_from_db()
        assert tag.is_active is True

    def test_promotion_tag_without_expiry_stays_active(self):
        from apps.tags.models import TagType
        from apps.tags.tasks import expire_promotion_tags
        from tests.factories import TagFactory

        tag = TagFactory(
            tag_type=TagType.PROMOTION,
            is_active=True,
            expires_at=None,
        )
        expire_promotion_tags.apply()
        tag.refresh_from_db()
        assert tag.is_active is True

    def test_expired_non_promotion_tag_is_not_deactivated(self):
        from datetime import timedelta

        from apps.tags.models import TagType
        from apps.tags.tasks import expire_promotion_tags
        from tests.factories import TagFactory

        past = timezone.now() - timedelta(minutes=10)
        tag = TagFactory(
            tag_type=TagType.CATEGORY,
            is_active=True,
            expires_at=past,
        )
        expire_promotion_tags.apply()
        tag.refresh_from_db()
        assert tag.is_active is True


# ---------------------------------------------------------------------------
# Gap #10 — Seed tag taxonomy completeness
# ---------------------------------------------------------------------------

class TestSeedTagTaxonomy:
    REQUIRED_CATEGORY_SLUGS = [
        "category-food", "category-cafe", "category-bakery", "category-fastfood",
        "category-pizza", "category-bbq", "category-chinese", "category-desi",
        "category-icecream", "category-clothing", "category-electronics",
        "category-grocery", "category-pharmacy", "category-salon", "category-gym",
        "category-clinic",
    ]
    REQUIRED_INTENT_SLUGS = [
        "intent-cheap", "intent-budget-under-300", "intent-budget-under-500",
        "intent-premium", "intent-luxury", "intent-quick", "intent-grab-and-go",
        "intent-healthy", "intent-family-friendly", "intent-halal", "intent-vegan",
    ]
    REQUIRED_PROMOTION_SLUGS = [
        "promo-discount-live", "promo-happy-hour", "promo-buy1get1",
        "promo-flash-deal", "promo-free-delivery", "promo-limited-stock",
    ]
    REQUIRED_TIME_SLUGS = [
        "time-breakfast", "time-lunch", "time-evening-snacks",
        "time-dinner", "time-late-night-open", "time-open-now",
    ]
    REQUIRED_SYSTEM_SLUGS = [
        "system-new-vendor", "system-claimed-vendor", "system-ar-priority",
        "system-featured-in-area", "system-high-engagement",
    ]

    def _run_seed(self):
        from django.core.management import call_command
        call_command("seed_data", "--no-vendors", verbosity=0)

    def test_all_category_tags_seeded(self):
        from apps.tags.models import Tag
        self._run_seed()
        existing = set(Tag.objects.filter(
            slug__in=self.REQUIRED_CATEGORY_SLUGS
        ).values_list("slug", flat=True))
        missing = set(self.REQUIRED_CATEGORY_SLUGS) - existing
        assert not missing, f"Missing CATEGORY tags: {missing}"

    def test_all_intent_tags_seeded(self):
        from apps.tags.models import Tag
        self._run_seed()
        existing = set(Tag.objects.filter(
            slug__in=self.REQUIRED_INTENT_SLUGS
        ).values_list("slug", flat=True))
        missing = set(self.REQUIRED_INTENT_SLUGS) - existing
        assert not missing, f"Missing INTENT tags: {missing}"

    def test_all_promotion_tags_seeded(self):
        from apps.tags.models import Tag
        self._run_seed()
        existing = set(Tag.objects.filter(
            slug__in=self.REQUIRED_PROMOTION_SLUGS
        ).values_list("slug", flat=True))
        missing = set(self.REQUIRED_PROMOTION_SLUGS) - existing
        assert not missing, f"Missing PROMOTION tags: {missing}"

    def test_all_time_tags_seeded(self):
        from apps.tags.models import Tag
        self._run_seed()
        existing = set(Tag.objects.filter(
            slug__in=self.REQUIRED_TIME_SLUGS
        ).values_list("slug", flat=True))
        missing = set(self.REQUIRED_TIME_SLUGS) - existing
        assert not missing, f"Missing TIME tags: {missing}"

    def test_all_system_tags_seeded(self):
        from apps.tags.models import Tag
        self._run_seed()
        existing = set(Tag.objects.filter(
            slug__in=self.REQUIRED_SYSTEM_SLUGS
        ).values_list("slug", flat=True))
        missing = set(self.REQUIRED_SYSTEM_SLUGS) - existing
        assert not missing, f"Missing SYSTEM tags: {missing}"


# ---------------------------------------------------------------------------
# Gap #12 — AnalyticsEvent model
# ---------------------------------------------------------------------------

class TestAnalyticsEventModel:
    def test_analytics_event_model_exists(self):
        from apps.analytics.models import AnalyticsEvent
        assert AnalyticsEvent is not None

    def test_all_event_types_defined(self):
        from apps.analytics.models import EventType
        required = {
            "AR_VIEW_OPENED", "VENDOR_MARKER_TAPPED", "VOICE_QUERY_MADE",
            "NAVIGATION_STARTED", "REEL_VIEWED", "PROMOTION_CLICKED", "VENDOR_VIEW",
        }
        defined = {e.value for e in EventType}
        assert required <= defined, f"Missing EventType values: {required - defined}"

    def test_analytics_event_can_be_created(self):
        from tests.factories import AnalyticsEventFactory
        event = AnalyticsEventFactory()
        assert event.pk is not None

    def test_analytics_event_anonymous_actor(self):
        from tests.factories import AnalyticsEventFactory
        event = AnalyticsEventFactory(actor_id=None)
        event.refresh_from_db()
        assert event.actor_id is None

    def test_analytics_event_vendor_nullable(self):
        from apps.analytics.models import AnalyticsEvent, EventType
        event = AnalyticsEvent.objects.create(
            event_type=EventType.AR_VIEW_OPENED,
            vendor=None,
            metadata={"area": "test"},
        )
        assert event.vendor is None


# ---------------------------------------------------------------------------
# Gap #14 — GDPR endpoints
# ---------------------------------------------------------------------------

class TestGDPRDataExport:
    def test_data_export_returns_account_and_audit(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/v1/auth/me/export/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "account" in data
        assert "audit_log" in data
        assert data["account"]["email"] == admin_user.email

    def test_data_export_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/auth/me/export/")
        assert response.status_code == 401


class TestGDPRAccountDeletion:
    def test_non_super_admin_can_delete_own_account(self, api_client):
        from tests.factories import AdminUserFactory
        from apps.accounts.models import AdminRole
        user = AdminUserFactory(role=AdminRole.DATA_ENTRY)
        api_client.force_authenticate(user=user)
        response = api_client.delete("/api/v1/auth/me/")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False
        assert "purged.airaad.internal" in user.email
        assert user.full_name == "[Deleted User]"

    def test_super_admin_cannot_self_delete(self, api_client):
        from tests.factories import AdminUserFactory
        from apps.accounts.models import AdminRole
        user = AdminUserFactory(role=AdminRole.SUPER_ADMIN)
        api_client.force_authenticate(user=user)
        response = api_client.delete("/api/v1/auth/me/")
        assert response.status_code == 403

    def test_account_deletion_requires_authentication(self, api_client):
        response = api_client.delete("/api/v1/auth/me/")
        assert response.status_code == 401

    def test_account_deletion_writes_audit_log(self, api_client):
        from apps.audit.models import AuditLog
        from tests.factories import AdminUserFactory
        from apps.accounts.models import AdminRole
        user = AdminUserFactory(role=AdminRole.DATA_ENTRY)
        api_client.force_authenticate(user=user)
        api_client.delete("/api/v1/auth/me/")
        assert AuditLog.objects.filter(action="GDPR_ACCOUNT_DELETED").exists()
