"""
AirAd Backend — Tags URL Configuration
Mounted at: /api/v1/tags/
Full implementation in TASK-020 (SESSION A-S5).
"""

from django.urls import path

from .views import TagDetailView, TagDiscoveryView, TagListCreateView

urlpatterns = [
    path("", TagListCreateView.as_view(), name="tag-list"),
    path("discovery/", TagDiscoveryView.as_view(), name="tag-discovery"),
    path("<uuid:pk>/", TagDetailView.as_view(), name="tag-detail"),
]
