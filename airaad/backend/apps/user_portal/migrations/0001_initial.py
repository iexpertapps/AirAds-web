"""
SQLite-compatible migration for user_portal models
Removes PostGIS dependencies and foreign key conflicts for test environment
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=50, unique=True)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("icon_url", models.URLField(blank=True)),
                (
                    "color",
                    models.CharField(
                        default="#007bff", help_text="Hex color code", max_length=7
                    ),
                ),
                ("category", models.CharField(db_index=True, max_length=30)),
                ("sort_order", models.IntegerField(default=0)),
                ("vendor_count", models.IntegerField(db_index=True, default=0)),
                ("search_count", models.IntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "user_portal_tags",
                "ordering": ["category", "sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="UserPortalConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(db_index=True, max_length=100, unique=True)),
                ("value", models.JSONField(default=dict)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "user_portal_config",
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="Promotion",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("PERCENTAGE", "Percentage"),
                            ("FIXED", "Fixed Amount"),
                            ("BOGO", "Buy One Get One"),
                            ("FREE_ITEM", "Free Item"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "discount_percent",
                    models.IntegerField(
                        blank=True, help_text="For percentage discounts", null=True
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("is_flash_deal", models.BooleanField(db_index=True, default=False)),
                (
                    "flash_duration_minutes",
                    models.IntegerField(
                        default=60, help_text="Duration in minutes for flash deals"
                    ),
                ),
                ("start_time", models.DateTimeField(db_index=True)),
                ("end_time", models.DateTimeField(db_index=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "usage_limit",
                    models.IntegerField(
                        blank=True,
                        help_text="Maximum uses, null for unlimited",
                        null=True,
                    ),
                ),
                ("usage_count", models.IntegerField(default=0)),
                ("image_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # Replace foreign key with UUID field for SQLite compatibility
                ("vendor_id", models.UUIDField(null=True, blank=True)),
            ],
            options={
                "db_table": "user_portal_promotions",
                "ordering": ["-is_flash_deal", "-discount_percent", "start_time"],
            },
        ),
        migrations.CreateModel(
            name="Vendor",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=200)),
                ("description", models.TextField(blank=True)),
                ("address", models.CharField(blank=True, max_length=500)),
                # Replace PointField with separate lat/lng fields for SQLite
                ("lat", models.FloatField(null=True, blank=True)),
                ("lng", models.FloatField(null=True, blank=True)),
                ("category", models.CharField(db_index=True, max_length=50)),
                (
                    "subcategory",
                    models.CharField(blank=True, db_index=True, max_length=50),
                ),
                ("tags", models.JSONField(blank=True, default=list)),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("SILVER", "Silver"),
                            ("GOLD", "Gold"),
                            ("DIAMOND", "Diamond"),
                            ("PLATINUM", "Platinum"),
                        ],
                        db_index=True,
                        default="SILVER",
                        max_length=10,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_verified", models.BooleanField(db_index=True, default=False)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
                ("business_hours", models.JSONField(blank=True, default=dict)),
                ("logo_url", models.URLField(blank=True)),
                ("cover_image_url", models.URLField(blank=True)),
                ("popularity_score", models.FloatField(db_index=True, default=0.0)),
                ("interaction_count", models.IntegerField(db_index=True, default=0)),
                ("system_tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "user_portal_vendors",
                "ordering": ["-popularity_score", "name"],
            },
        ),
        migrations.CreateModel(
            name="VendorReel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("video_url", models.URLField()),
                ("thumbnail_url", models.URLField()),
                ("duration_seconds", models.IntegerField()),
                ("view_count", models.IntegerField(db_index=True, default=0)),
                ("cta_tap_count", models.IntegerField(default=0)),
                ("completion_count", models.IntegerField(default=0)),
                ("cta_text", models.CharField(blank=True, max_length=100)),
                ("cta_url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_approved", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # Replace foreign key with UUID field for SQLite compatibility
                ("vendor_id", models.UUIDField(null=True, blank=True)),
            ],
            options={
                "db_table": "user_portal_vendor_reels",
                "ordering": ["-view_count", "-created_at"],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="vendor",
            index=models.Index(
                fields=["category", "is_active"], name="user_portal_categor_cb3f84_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="vendor",
            index=models.Index(
                fields=["tier", "is_active"], name="user_portal_tier_807ef8_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="vendor",
            index=models.Index(
                fields=["is_verified", "is_active"],
                name="user_portal_is_veri_2eded2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="vendor",
            index=models.Index(
                fields=["popularity_score", "is_active"],
                name="user_portal_popular_afd4fa_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(
                fields=["category", "sort_order", "is_active"],
                name="user_portal_categor_e5f551_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="promotion",
            index=models.Index(
                fields=["is_flash_deal", "is_active", "start_time"],
                name="user_portal_is_flas_82441a_idx"
            ),
        ),
    ]
