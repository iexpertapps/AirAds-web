"""
AirAd Backend — Vendors URL Configuration
Mounted at: /api/v1/vendors/

Phase A: CRUD, QC, photos, visits, tags, analytics.
Phase B: Claim flow endpoints (§3.2).
"""

from django.urls import path

from .claim_views import (
    ClaimableVendorsView,
    ClaimStatusView,
    ClaimUploadProofView,
    ClaimVerifyOTPView,
    SubmitClaimView,
    WithdrawClaimView,
)
from .views import (
    VendorAnalyticsView,
    VendorDetailView,
    VendorListCreateView,
    VendorPhotosView,
    VendorQCStatusView,
    VendorTagDetailView,
    VendorTagsView,
    VendorVisitsView,
)

urlpatterns = [
    # --- Phase A ---
    path("", VendorListCreateView.as_view(), name="vendor-list"),
    path("<uuid:pk>/", VendorDetailView.as_view(), name="vendor-detail"),
    path("<uuid:pk>/qc-status/", VendorQCStatusView.as_view(), name="vendor-qc-status"),
    path("<uuid:vendor_pk>/photos/", VendorPhotosView.as_view(), name="vendor-photos"),
    path("<uuid:vendor_pk>/visits/", VendorVisitsView.as_view(), name="vendor-visits"),
    path("<uuid:vendor_pk>/tags/", VendorTagsView.as_view(), name="vendor-tags"),
    path(
        "<uuid:vendor_pk>/tags/<uuid:tag_pk>/",
        VendorTagDetailView.as_view(),
        name="vendor-tag-detail",
    ),
    path(
        "<uuid:vendor_pk>/analytics/",
        VendorAnalyticsView.as_view(),
        name="vendor-analytics",
    ),
    # --- Phase B — Claim Flow (§3.2) ---
    path("claimable/", ClaimableVendorsView.as_view(), name="vendor-claimable"),
    path("claim/", SubmitClaimView.as_view(), name="vendor-submit-claim"),
    path(
        "<str:vendor_id>/claim/",
        WithdrawClaimView.as_view(),
        name="vendor-withdraw-claim",
    ),
    path(
        "<str:vendor_id>/claim/verify-otp/",
        ClaimVerifyOTPView.as_view(),
        name="vendor-claim-verify-otp",
    ),
    path(
        "<str:vendor_id>/claim/upload-proof/",
        ClaimUploadProofView.as_view(),
        name="vendor-claim-upload-proof",
    ),
    path(
        "<str:vendor_id>/claim/status/",
        ClaimStatusView.as_view(),
        name="vendor-claim-status",
    ),
]
