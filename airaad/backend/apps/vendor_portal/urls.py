"""
AirAd Backend — Vendor Portal URL Configuration
Mounted at: /api/v1/vendor-portal/

C-1: Auth (send-otp, verify-otp, refresh, logout, me)
C-2: Profile (CRUD, hours, services, logo, cover, location-change, completeness)
C-3: Dashboard (aggregated data)
C-4: Landing (public stats)
C-5: Claim flow (search, nearby, submit, verify-otp, upload-proof, status)
"""

from django.urls import path

from apps.vendors.claim_views import (
    ClaimableVendorsView,
    ClaimStatusView,
    ClaimUploadProofView,
    ClaimVerifyOTPView,
    SubmitClaimView,
)
from apps.vendors.discount_views import (
    VendorDiscountAnalyticsView,
    VendorDiscountDetailView,
    VendorDiscountListCreateView,
    VendorHappyHourCreateView,
)
from apps.vendors.voicebot_views import (
    VendorVoiceBotTestView,
    VendorVoiceBotView,
)

from .views import (
    VendorPortalActivationStageView,
    VendorPortalCompletenessView,
    VendorPortalCoverUploadView,
    VendorPortalDashboardView,
    VendorPortalHoursView,
    VendorPortalLandingStatsView,
    VendorPortalLocationChangeView,
    VendorPortalLogoutView,
    VendorPortalLogoUploadView,
    VendorPortalMeView,
    VendorPortalProfileView,
    VendorPortalRefreshView,
    VendorPortalSendOTPView,
    VendorPortalServicesView,
    VendorPortalVerifyOTPView,
)

urlpatterns = [
    # --- C-1: Auth ---
    path("auth/send-otp/", VendorPortalSendOTPView.as_view(), name="vendor-portal-send-otp"),
    path("auth/verify-otp/", VendorPortalVerifyOTPView.as_view(), name="vendor-portal-verify-otp"),
    path("auth/refresh/", VendorPortalRefreshView.as_view(), name="vendor-portal-refresh"),
    path("auth/logout/", VendorPortalLogoutView.as_view(), name="vendor-portal-logout"),
    path("auth/me/", VendorPortalMeView.as_view(), name="vendor-portal-me"),
    # --- C-2: Profile ---
    path("profile/", VendorPortalProfileView.as_view(), name="vendor-portal-profile"),
    path("profile/hours/", VendorPortalHoursView.as_view(), name="vendor-portal-hours"),
    path("profile/services/", VendorPortalServicesView.as_view(), name="vendor-portal-services"),
    path("profile/logo/", VendorPortalLogoUploadView.as_view(), name="vendor-portal-logo"),
    path("profile/cover/", VendorPortalCoverUploadView.as_view(), name="vendor-portal-cover"),
    path(
        "profile/request-location-change/",
        VendorPortalLocationChangeView.as_view(),
        name="vendor-portal-location-change",
    ),
    path(
        "profile/completeness/",
        VendorPortalCompletenessView.as_view(),
        name="vendor-portal-completeness",
    ),
    # --- C-3: Dashboard ---
    path("dashboard/", VendorPortalDashboardView.as_view(), name="vendor-portal-dashboard"),
    # --- C-4: Landing ---
    path("landing/stats/", VendorPortalLandingStatsView.as_view(), name="vendor-portal-landing-stats"),
    # --- B-6: Discounts ---
    path("discounts/", VendorDiscountListCreateView.as_view(), name="vendor-portal-discount-list"),
    path("discounts/<str:discount_id>/", VendorDiscountDetailView.as_view(), name="vendor-portal-discount-detail"),
    path("discounts/<str:discount_id>/analytics/", VendorDiscountAnalyticsView.as_view(), name="vendor-portal-discount-analytics"),
    path("happy-hours/", VendorHappyHourCreateView.as_view(), name="vendor-portal-happy-hour"),
    # --- B-7: Voice Bot ---
    path("voice-bot/", VendorVoiceBotView.as_view(), name="vendor-portal-voicebot"),
    path("voice-bot/test/", VendorVoiceBotTestView.as_view(), name="vendor-portal-voicebot-test"),
    # --- B-3: Activation Stage ---
    path("activation-stage/", VendorPortalActivationStageView.as_view(), name="vendor-portal-activation-stage"),
    # --- C-5: Claim Flow ---
    path("claim/search/", ClaimableVendorsView.as_view(), name="vendor-portal-claim-search"),
    path("claim/submit/", SubmitClaimView.as_view(), name="vendor-portal-claim-submit"),
    path("claim/<str:vendor_id>/verify-otp/", ClaimVerifyOTPView.as_view(), name="vendor-portal-claim-verify-otp"),
    path("claim/<str:vendor_id>/upload-proof/", ClaimUploadProofView.as_view(), name="vendor-portal-claim-upload-proof"),
    path("claim/<str:vendor_id>/status/", ClaimStatusView.as_view(), name="vendor-portal-claim-status"),
]
