"""
AirAd Backend — Reels URL Configuration (Phase B §B-9)
Mounted at: /api/v1/vendor-portal/reels/ (vendor portal)
Additional public URLs registered in config/urls.py.
"""

from django.urls import path

from .views import VendorReelDetailView, VendorReelListCreateView

urlpatterns = [
    path("", VendorReelListCreateView.as_view(), name="vendor-reel-list-create"),
    path("<str:reel_id>/", VendorReelDetailView.as_view(), name="vendor-reel-detail"),
]
