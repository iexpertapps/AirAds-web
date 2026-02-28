"""
AirAd Backend — Accounts URL Configuration
Mounted at: /api/v1/auth/

Phase A: Admin JWT login/logout/refresh, user management, GDPR.
Phase B: Customer/Vendor OTP auth endpoints (§3.2).
"""

from django.urls import path

from .otp_views import (
    CustomerAccountDeleteView,
    CustomerProfileView,
    CustomerRefreshView,
    CustomerSendOTPView,
    CustomerVerifyOTPView,
    VendorAuthRefreshView,
    VendorEmailVerifyView,
    VendorProfileView,
    VendorSendOTPView,
    VendorVerifyOTPView,
)
from .views import (
    AdminUserDetailView,
    AdminUserListView,
    CustomTokenRefreshView,
    GDPRAccountDeletionView,
    GDPRDataExportView,
    LoginView,
    LogoutView,
    ProfileView,
    UnlockAdminUserView,
)

urlpatterns = [
    # --- Admin Auth (Phase A) ---
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("users/", AdminUserListView.as_view(), name="auth-user-list"),
    path("users/create/", AdminUserListView.as_view(), name="auth-create-user"),
    path("users/<str:pk>/", AdminUserDetailView.as_view(), name="auth-user-detail"),
    path(
        "users/<str:pk>/unlock/", UnlockAdminUserView.as_view(), name="auth-user-unlock"
    ),
    # GDPR endpoints (spec §10.1)
    path("me/export/", GDPRDataExportView.as_view(), name="gdpr-data-export"),
    path("me/", GDPRAccountDeletionView.as_view(), name="gdpr-account-deletion"),
    # --- Customer OTP Auth (Phase B §3.2) ---
    path(
        "customer/send-otp/",
        CustomerSendOTPView.as_view(),
        name="customer-send-otp",
    ),
    path(
        "customer/verify-otp/",
        CustomerVerifyOTPView.as_view(),
        name="customer-verify-otp",
    ),
    path(
        "customer/profile/",
        CustomerProfileView.as_view(),
        name="customer-profile",
    ),
    path(
        "customer/account/",
        CustomerAccountDeleteView.as_view(),
        name="customer-account-delete",
    ),
    path(
        "customer/refresh/",
        CustomerRefreshView.as_view(),
        name="customer-refresh",
    ),
    # --- Vendor OTP Auth (Phase B §3.2) ---
    path(
        "vendor/send-otp/",
        VendorSendOTPView.as_view(),
        name="vendor-send-otp",
    ),
    path(
        "vendor/verify-otp/",
        VendorVerifyOTPView.as_view(),
        name="vendor-verify-otp",
    ),
    path(
        "vendor/me/",
        VendorProfileView.as_view(),
        name="vendor-profile",
    ),
    path(
        "vendor/refresh/",
        VendorAuthRefreshView.as_view(),
        name="vendor-refresh",
    ),
    path(
        "vendor/verify-email/",
        VendorEmailVerifyView.as_view(),
        name="vendor-verify-email",
    ),
]
