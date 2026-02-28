"""
AirAd Backend — Discovery URL Configuration (Phase B §3.3)
Mounted at: /api/v1/discovery/
"""

from django.urls import path

from .views import NearbyReelsView, NearbyVendorsView, SearchVendorsView, VoiceSearchView

urlpatterns = [
    path("search/", SearchVendorsView.as_view(), name="discovery-search"),
    path("nearby/", NearbyVendorsView.as_view(), name="discovery-nearby"),
    path("nearby/reels/", NearbyReelsView.as_view(), name="discovery-nearby-reels"),
    path("voice-search/", VoiceSearchView.as_view(), name="discovery-voice-search"),
]
