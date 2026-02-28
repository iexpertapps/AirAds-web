"""
AirAd Backend — Reels App Configuration (Phase B §3.1, §B-9)
"""

from django.apps import AppConfig


class ReelsConfig(AppConfig):
    """AppConfig for the reels app.

    Handles vendor reel/video uploads with tier-based limits,
    moderation workflow, and public display.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reels"
    verbose_name = "Reels"
