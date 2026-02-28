"""AirAd — Vendor Portal app configuration."""

from django.apps import AppConfig


class VendorPortalConfig(AppConfig):
    """Configuration for the vendor portal application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vendor_portal"
    verbose_name = "Vendor Portal"
