"""
AirAd Backend — Root URL Configuration

Phase A: 12 API prefixes for admin portal.
Phase B: +3 prefixes (discovery, admin management, voice-query on vendors).
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.discovery.views import VoiceQueryVendorView
from apps.reels.views import PublicVendorReelsView, ReelViewEventView
from apps.vendors.admin_views import (
    AdminApproveClaimView,
    AdminApproveLocationView,
    AdminBulkAssignTagsView,
    AdminLaunchCityView,
    AdminModerateReelApproveView,
    AdminModerateReelRejectView,
    AdminModerationQueueView,
    AdminRejectClaimView,
    AdminRejectLocationView,
    AdminRemoveDiscountView,
    AdminSuspendVendorView,
    AdminVerifyVendorView,
)

urlpatterns = [
    # Django admin (internal use only)
    path("django-admin/", admin.site.urls),
    # -------------------------------------------------------------------------
    # API v1 — Phase A routes
    # -------------------------------------------------------------------------
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/geo/", include("apps.geo.urls")),
    path("api/v1/tags/", include("apps.tags.urls")),
    path("api/v1/vendors/", include("apps.vendors.urls")),
    path("api/v1/imports/", include("apps.imports.urls")),
    path("api/v1/field-ops/", include("apps.field_ops.urls")),
    path("api/v1/qa/", include("apps.qa.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/health/", include("apps.health.urls")),
    path("api/v1/governance/", include("apps.governance.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    # -------------------------------------------------------------------------
    # API v1 — Phase B routes (§3.3 Discovery, §3.7 Admin Management)
    # -------------------------------------------------------------------------
    path("api/v1/discovery/", include("apps.discovery.urls")),
    # Voice query on a specific vendor (§3.3)
    path(
        "api/v1/vendors/<str:slug>/voice-query/",
        VoiceQueryVendorView.as_view(),
        name="vendor-voice-query",
    ),
    # Admin vendor management (§3.7)
    path(
        "api/v1/admin/vendors/<str:vendor_id>/verify/",
        AdminVerifyVendorView.as_view(),
        name="admin-vendor-verify",
    ),
    path(
        "api/v1/admin/vendors/<str:vendor_id>/suspend/",
        AdminSuspendVendorView.as_view(),
        name="admin-vendor-suspend",
    ),
    path(
        "api/v1/admin/vendors/<str:vendor_id>/approve-claim/",
        AdminApproveClaimView.as_view(),
        name="admin-vendor-approve-claim",
    ),
    path(
        "api/v1/admin/vendors/<str:vendor_id>/reject-claim/",
        AdminRejectClaimView.as_view(),
        name="admin-vendor-reject-claim",
    ),
    path(
        "api/v1/admin/vendors/<str:vendor_id>/approve-location/",
        AdminApproveLocationView.as_view(),
        name="admin-vendor-approve-location",
    ),
    path(
        "api/v1/admin/vendors/<str:vendor_id>/reject-location/",
        AdminRejectLocationView.as_view(),
        name="admin-vendor-reject-location",
    ),
    path(
        "api/v1/admin/geo/cities/<str:city_id>/launch/",
        AdminLaunchCityView.as_view(),
        name="admin-city-launch",
    ),
    path(
        "api/v1/admin/tags/bulk-assign/",
        AdminBulkAssignTagsView.as_view(),
        name="admin-bulk-assign-tags",
    ),
    # -------------------------------------------------------------------------
    # API v1 — Phase B — Admin Moderation (§B-12)
    # -------------------------------------------------------------------------
    path(
        "api/v1/admin/moderation/reels/<str:reel_id>/approve/",
        AdminModerateReelApproveView.as_view(),
        name="admin-moderate-reel-approve",
    ),
    path(
        "api/v1/admin/moderation/reels/<str:reel_id>/reject/",
        AdminModerateReelRejectView.as_view(),
        name="admin-moderate-reel-reject",
    ),
    path(
        "api/v1/admin/moderation/discounts/<str:discount_id>/remove/",
        AdminRemoveDiscountView.as_view(),
        name="admin-remove-discount",
    ),
    path(
        "api/v1/admin/moderation/queue/",
        AdminModerationQueueView.as_view(),
        name="admin-moderation-queue",
    ),
    # -------------------------------------------------------------------------
    # API v1 — Phase B — Reels (§B-9)
    # -------------------------------------------------------------------------
    path(
        "api/v1/vendors/<str:slug>/reels/",
        PublicVendorReelsView.as_view(),
        name="vendor-public-reels",
    ),
    path(
        "api/v1/reels/<str:reel_id>/view/",
        ReelViewEventView.as_view(),
        name="reel-view-event",
    ),
    # -------------------------------------------------------------------------
    # API v1 — Phase C routes (Vendor Portal + Payments)
    # -------------------------------------------------------------------------
    path("api/v1/vendor-portal/", include("apps.vendor_portal.urls")),
    path("api/v1/vendor-portal/reels/", include("apps.reels.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    # -------------------------------------------------------------------------
    # API v1 — User Portal (Customer Authentication + Discovery)
    # -------------------------------------------------------------------------
    path("api/user-portal/", include("config.urls_user_portal")),
    # -------------------------------------------------------------------------
    # OpenAPI schema + Swagger UI
    # -------------------------------------------------------------------------
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
] + (
    [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]
    if settings.DEBUG
    else []
)
