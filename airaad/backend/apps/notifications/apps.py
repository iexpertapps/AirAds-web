"""
AirAd Backend — Notifications App Configuration (Phase B §B-10)
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """AppConfig for the notifications app.

    Handles push notifications (FCM), email, and SMS dispatch
    with template rendering and delivery logging.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"
