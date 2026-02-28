"""
AirAd Backend — Geo URL Configuration
Mounted at: /api/v1/geo/
"""

from django.urls import path

from .views import (
    AreaDetailView,
    AreaListCreateView,
    CityDetailView,
    CityListCreateView,
    CountryDetailView,
    CountryListCreateView,
    LandmarkDetailView,
    LandmarkListCreateView,
)

urlpatterns = [
    path("countries/", CountryListCreateView.as_view(), name="geo-country-list"),
    path("countries/<uuid:pk>/", CountryDetailView.as_view(), name="geo-country-detail"),
    path("cities/", CityListCreateView.as_view(), name="geo-city-list"),
    path("cities/<uuid:pk>/", CityDetailView.as_view(), name="geo-city-detail"),
    path("areas/", AreaListCreateView.as_view(), name="geo-area-list"),
    path("areas/<uuid:pk>/", AreaDetailView.as_view(), name="geo-area-detail"),
    path("landmarks/", LandmarkListCreateView.as_view(), name="geo-landmark-list"),
    path(
        "landmarks/<uuid:pk>/", LandmarkDetailView.as_view(), name="geo-landmark-detail"
    ),
]
