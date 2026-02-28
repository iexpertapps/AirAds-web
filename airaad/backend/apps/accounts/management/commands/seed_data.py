"""
AirAd Backend — seed_data Management Command

Creates a complete Karachi geo hierarchy, 6 taxonomy tags, 1 SUPER_ADMIN user,
and 3 sample vendors with encrypted phone numbers and business hours.

Idempotent — safe to run multiple times. Uses get_or_create() throughout.
All business logic delegated to services.py (R4).
All mutations produce AuditLog entries via log_action() (R5).
Phone numbers encrypted via AES-256-GCM (R2).

Usage:
    python manage.py seed_data
    python manage.py seed_data --no-vendors   # skip vendor creation
"""

import logging
from typing import Any

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Seed the database with Karachi geo hierarchy, tags, admin user, and sample vendors."""

    help = "Seed database with Karachi geo hierarchy, tags, admin user, and 3 sample vendors"

    def add_arguments(self, parser: Any) -> None:
        """Register command-line arguments.

        Args:
            parser: ArgumentParser instance.
        """
        parser.add_argument(
            "--no-vendors",
            action="store_true",
            default=False,
            help="Skip vendor creation (geo hierarchy and tags still created).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the seed_data command.

        Args:
            *args: Positional arguments (unused).
            **options: Parsed command-line options.
        """
        self.stdout.write(self.style.MIGRATE_HEADING("AirAd seed_data starting..."))

        try:
            with transaction.atomic():
                admin_user = self._seed_admin_user()
                country = self._seed_country(admin_user)
                city = self._seed_city(country, admin_user)
                area = self._seed_area(city, admin_user)
                landmark = self._seed_landmark(area, admin_user)
                self._seed_tags(admin_user)

                if not options["no_vendors"]:
                    self._seed_vendors(city, area, landmark, admin_user)
                    self._seed_field_visits(admin_user)

        except Exception as exc:
            raise CommandError(f"seed_data failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("seed_data complete."))

    # -------------------------------------------------------------------------
    # Admin user
    # -------------------------------------------------------------------------

    def _seed_admin_user(self) -> Any:
        """Create or retrieve the SUPER_ADMIN seed user.

        Returns:
            AdminUser instance.
        """
        from apps.accounts.models import AdminRole, AdminUser

        user, created = AdminUser.objects.get_or_create(
            email="admin@airaad.com",
            defaults={
                "full_name": "AirAd Super Admin",
                "role": AdminRole.SUPER_ADMIN,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password("Admin@12345!")
            user.save(update_fields=["password"])
            self.stdout.write(f"  Created SUPER_ADMIN: {user.email}")
        else:
            self.stdout.write(f"  SUPER_ADMIN exists: {user.email}")

        return user

    # -------------------------------------------------------------------------
    # Geo hierarchy — Pakistan → Karachi → DHA → Zamzama
    # -------------------------------------------------------------------------

    def _seed_country(self, actor: Any) -> Any:
        """Create or retrieve Pakistan.

        Args:
            actor: AdminUser for AuditLog.

        Returns:
            Country instance.
        """
        from apps.geo.models import Country

        country, created = Country.objects.get_or_create(
            code="PK",
            defaults={"name": "Pakistan", "is_active": True},
        )
        if created:
            from apps.audit.utils import log_action

            log_action(
                "COUNTRY_CREATED",
                actor,
                country,
                None,
                {},
                {"name": "Pakistan", "code": "PK"},
            )
            self.stdout.write("  Created Country: Pakistan (PK)")
        else:
            self.stdout.write("  Country exists: Pakistan (PK)")
        return country

    def _seed_city(self, country: Any, actor: Any) -> Any:
        """Create or retrieve Karachi.

        Args:
            country: Parent Country instance.
            actor: AdminUser for AuditLog.

        Returns:
            City instance.
        """
        from apps.geo.models import City

        city, created = City.objects.get_or_create(
            slug="karachi",
            defaults={
                "country": country,
                "name": "Karachi",
                "aliases": ["Karāchi", "کراچی", "City of Lights"],
                "centroid": Point(67.0099, 24.8607, srid=4326),  # lon/lat
                "is_active": True,
                "display_order": 1,
            },
        )
        if created:
            from apps.audit.utils import log_action

            log_action(
                "CITY_CREATED",
                actor,
                city,
                None,
                {},
                {"name": "Karachi", "slug": "karachi"},
            )
            self.stdout.write("  Created City: Karachi")
        else:
            self.stdout.write("  City exists: Karachi")
        return city

    def _seed_area(self, city: Any, actor: Any) -> Any:
        """Create or retrieve DHA Phase 6 area.

        Args:
            city: Parent City instance.
            actor: AdminUser for AuditLog.

        Returns:
            Area instance.
        """
        from apps.geo.models import Area

        area, created = Area.objects.get_or_create(
            slug="dha-phase-6-karachi",
            defaults={
                "city": city,
                "name": "DHA Phase 6",
                "aliases": [
                    "Defence Phase 6",
                    "DHA-6",
                    "Defence Housing Authority Phase 6",
                ],
                "centroid": Point(67.0680, 24.8200, srid=4326),
                "is_active": True,
            },
        )
        if created:
            from apps.audit.utils import log_action

            log_action(
                "AREA_CREATED",
                actor,
                area,
                None,
                {},
                {"name": "DHA Phase 6", "slug": "dha-phase-6-karachi"},
            )
            self.stdout.write("  Created Area: DHA Phase 6")
        else:
            self.stdout.write("  Area exists: DHA Phase 6")
        return area

    def _seed_landmark(self, area: Any, actor: Any) -> Any:
        """Create or retrieve Zamzama Boulevard landmark.

        Args:
            area: Parent Area instance.
            actor: AdminUser for AuditLog.

        Returns:
            Landmark instance.
        """
        from apps.geo.models import Landmark

        landmark, created = Landmark.objects.get_or_create(
            slug="zamzama-boulevard-karachi",
            defaults={
                "area": area,
                "name": "Zamzama Boulevard",
                "aliases": ["Zamzama", "Zamzama Street", "Zamzama Commercial Area"],
                "location": Point(67.0600, 24.8270, srid=4326),
                "is_active": True,
            },
        )
        if created:
            from apps.audit.utils import log_action

            log_action(
                "LANDMARK_CREATED",
                actor,
                landmark,
                None,
                {},
                {"name": "Zamzama Boulevard"},
            )
            self.stdout.write("  Created Landmark: Zamzama Boulevard")
        else:
            self.stdout.write("  Landmark exists: Zamzama Boulevard")
        return landmark

    # -------------------------------------------------------------------------
    # Tags — 15 taxonomy tags (2 per non-system type + 5 SYSTEM tags for Phase B)
    # -------------------------------------------------------------------------

    def _seed_tags(self, actor: Any) -> None:
        """Create 15 seed tags covering all 6 types including SYSTEM tags for Phase B.

        SYSTEM tags are inserted directly via get_or_create (bypassing the API
        restriction that prevents SYSTEM tag creation via the service layer).
        These are required by Phase B's TagAutoAssigner (TASK-B07).

        Args:
            actor: AdminUser for AuditLog.
        """
        from apps.audit.utils import log_action
        from apps.tags.models import Tag, TagType

        seed_tags = [
            # ----------------------------------------------------------------
            # LOCATION tags (spec §2.1 — geographic hierarchy labels)
            # ----------------------------------------------------------------
            {
                "name": "Karachi",
                "slug": "location-karachi",
                "tag_type": TagType.LOCATION,
                "display_label": "Karachi",
                "display_order": 1,
                "icon_name": "map-pin",
            },
            {
                "name": "Islamabad",
                "slug": "location-islamabad",
                "tag_type": TagType.LOCATION,
                "display_label": "Islamabad",
                "display_order": 2,
                "icon_name": "map-pin",
            },
            {
                "name": "Lahore",
                "slug": "location-lahore",
                "tag_type": TagType.LOCATION,
                "display_label": "Lahore",
                "display_order": 3,
                "icon_name": "map-pin",
            },
            {
                "name": "DHA",
                "slug": "location-dha",
                "tag_type": TagType.LOCATION,
                "display_label": "DHA",
                "display_order": 4,
                "icon_name": "map-pin",
            },
            {
                "name": "Blue Area",
                "slug": "location-blue-area",
                "tag_type": TagType.LOCATION,
                "display_label": "Blue Area",
                "display_order": 5,
                "icon_name": "map-pin",
            },
            # ----------------------------------------------------------------
            # CATEGORY tags (spec §4.1 — Food & Beverage)
            # ----------------------------------------------------------------
            {
                "name": "Food",
                "slug": "category-food",
                "tag_type": TagType.CATEGORY,
                "display_label": "Food",
                "display_order": 1,
                "icon_name": "utensils",
            },
            {
                "name": "Cafe",
                "slug": "category-cafe",
                "tag_type": TagType.CATEGORY,
                "display_label": "Cafe",
                "display_order": 2,
                "icon_name": "coffee",
            },
            {
                "name": "Bakery",
                "slug": "category-bakery",
                "tag_type": TagType.CATEGORY,
                "display_label": "Bakery",
                "display_order": 3,
                "icon_name": "cake",
            },
            {
                "name": "FastFood",
                "slug": "category-fastfood",
                "tag_type": TagType.CATEGORY,
                "display_label": "Fast Food",
                "display_order": 4,
                "icon_name": "zap",
            },
            {
                "name": "Pizza",
                "slug": "category-pizza",
                "tag_type": TagType.CATEGORY,
                "display_label": "Pizza",
                "display_order": 5,
                "icon_name": "circle",
            },
            {
                "name": "BBQ",
                "slug": "category-bbq",
                "tag_type": TagType.CATEGORY,
                "display_label": "BBQ",
                "display_order": 6,
                "icon_name": "flame",
            },
            {
                "name": "Chinese",
                "slug": "category-chinese",
                "tag_type": TagType.CATEGORY,
                "display_label": "Chinese",
                "display_order": 7,
                "icon_name": "utensils",
            },
            {
                "name": "Desi",
                "slug": "category-desi",
                "tag_type": TagType.CATEGORY,
                "display_label": "Desi",
                "display_order": 8,
                "icon_name": "utensils",
            },
            {
                "name": "IceCream",
                "slug": "category-icecream",
                "tag_type": TagType.CATEGORY,
                "display_label": "Ice Cream",
                "display_order": 9,
                "icon_name": "ice-cream",
            },
            # CATEGORY tags (spec §4.1 — Retail)
            {
                "name": "Clothing",
                "slug": "category-clothing",
                "tag_type": TagType.CATEGORY,
                "display_label": "Clothing",
                "display_order": 10,
                "icon_name": "shirt",
            },
            {
                "name": "Electronics",
                "slug": "category-electronics",
                "tag_type": TagType.CATEGORY,
                "display_label": "Electronics",
                "display_order": 11,
                "icon_name": "cpu",
            },
            {
                "name": "Grocery",
                "slug": "category-grocery",
                "tag_type": TagType.CATEGORY,
                "display_label": "Grocery",
                "display_order": 12,
                "icon_name": "shopping-cart",
            },
            {
                "name": "Pharmacy",
                "slug": "category-pharmacy",
                "tag_type": TagType.CATEGORY,
                "display_label": "Pharmacy",
                "display_order": 13,
                "icon_name": "pill",
            },
            {
                "name": "Cosmetics",
                "slug": "category-cosmetics",
                "tag_type": TagType.CATEGORY,
                "display_label": "Cosmetics",
                "display_order": 14,
                "icon_name": "sparkles",
            },
            {
                "name": "Books",
                "slug": "category-books",
                "tag_type": TagType.CATEGORY,
                "display_label": "Books",
                "display_order": 15,
                "icon_name": "book",
            },
            {
                "name": "Toys",
                "slug": "category-toys",
                "tag_type": TagType.CATEGORY,
                "display_label": "Toys",
                "display_order": 16,
                "icon_name": "gift",
            },
            # CATEGORY tags (spec §4.1 — Services)
            {
                "name": "Salon",
                "slug": "category-salon",
                "tag_type": TagType.CATEGORY,
                "display_label": "Salon",
                "display_order": 17,
                "icon_name": "scissors",
            },
            {
                "name": "Gym",
                "slug": "category-gym",
                "tag_type": TagType.CATEGORY,
                "display_label": "Gym",
                "display_order": 18,
                "icon_name": "dumbbell",
            },
            {
                "name": "Clinic",
                "slug": "category-clinic",
                "tag_type": TagType.CATEGORY,
                "display_label": "Clinic",
                "display_order": 19,
                "icon_name": "stethoscope",
            },
            {
                "name": "CarWash",
                "slug": "category-carwash",
                "tag_type": TagType.CATEGORY,
                "display_label": "Car Wash",
                "display_order": 20,
                "icon_name": "car",
            },
            {
                "name": "Laundry",
                "slug": "category-laundry",
                "tag_type": TagType.CATEGORY,
                "display_label": "Laundry",
                "display_order": 21,
                "icon_name": "wind",
            },
            {
                "name": "Repair",
                "slug": "category-repair",
                "tag_type": TagType.CATEGORY,
                "display_label": "Repair",
                "display_order": 22,
                "icon_name": "wrench",
            },
            # ----------------------------------------------------------------
            # INTENT tags (spec §4.2 — Value-Based)
            # ----------------------------------------------------------------
            {
                "name": "Cheap",
                "slug": "intent-cheap",
                "tag_type": TagType.INTENT,
                "display_label": "Cheap",
                "display_order": 1,
                "icon_name": "dollar-sign",
            },
            {
                "name": "BudgetUnder300",
                "slug": "intent-budget-under-300",
                "tag_type": TagType.INTENT,
                "display_label": "Budget Under 300",
                "display_order": 2,
                "icon_name": "dollar-sign",
            },
            {
                "name": "BudgetUnder500",
                "slug": "intent-budget-under-500",
                "tag_type": TagType.INTENT,
                "display_label": "Budget Under 500",
                "display_order": 3,
                "icon_name": "dollar-sign",
            },
            {
                "name": "Premium",
                "slug": "intent-premium",
                "tag_type": TagType.INTENT,
                "display_label": "Premium",
                "display_order": 4,
                "icon_name": "star",
            },
            {
                "name": "Luxury",
                "slug": "intent-luxury",
                "tag_type": TagType.INTENT,
                "display_label": "Luxury",
                "display_order": 5,
                "icon_name": "crown",
            },
            # INTENT tags (spec §4.2 — Speed-Based)
            {
                "name": "Quick",
                "slug": "intent-quick",
                "tag_type": TagType.INTENT,
                "display_label": "Quick",
                "display_order": 6,
                "icon_name": "zap",
            },
            {
                "name": "GrabAndGo",
                "slug": "intent-grab-and-go",
                "tag_type": TagType.INTENT,
                "display_label": "Grab & Go",
                "display_order": 7,
                "icon_name": "package",
            },
            {
                "name": "FastService",
                "slug": "intent-fast-service",
                "tag_type": TagType.INTENT,
                "display_label": "Fast Service",
                "display_order": 8,
                "icon_name": "zap",
            },
            {
                "name": "DineIn",
                "slug": "intent-dine-in",
                "tag_type": TagType.INTENT,
                "display_label": "Dine In",
                "display_order": 9,
                "icon_name": "utensils",
            },
            # INTENT tags (spec §4.2 — Lifestyle)
            {
                "name": "Healthy",
                "slug": "intent-healthy",
                "tag_type": TagType.INTENT,
                "display_label": "Healthy",
                "display_order": 10,
                "icon_name": "heart",
            },
            {
                "name": "FamilyFriendly",
                "slug": "intent-family-friendly",
                "tag_type": TagType.INTENT,
                "display_label": "Family Friendly",
                "display_order": 11,
                "icon_name": "users",
            },
            {
                "name": "Romantic",
                "slug": "intent-romantic",
                "tag_type": TagType.INTENT,
                "display_label": "Romantic",
                "display_order": 12,
                "icon_name": "heart",
            },
            {
                "name": "StudentFriendly",
                "slug": "intent-student-friendly",
                "tag_type": TagType.INTENT,
                "display_label": "Student Friendly",
                "display_order": 13,
                "icon_name": "book",
            },
            {
                "name": "Halal",
                "slug": "intent-halal",
                "tag_type": TagType.INTENT,
                "display_label": "Halal",
                "display_order": 14,
                "icon_name": "check-circle",
            },
            {
                "name": "Vegan",
                "slug": "intent-vegan",
                "tag_type": TagType.INTENT,
                "display_label": "Vegan",
                "display_order": 15,
                "icon_name": "leaf",
            },
            # INTENT tags (spec §4.2 — Context)
            {
                "name": "OfficeLunch",
                "slug": "intent-office-lunch",
                "tag_type": TagType.INTENT,
                "display_label": "Office Lunch",
                "display_order": 16,
                "icon_name": "briefcase",
            },
            {
                "name": "DateSpot",
                "slug": "intent-date-spot",
                "tag_type": TagType.INTENT,
                "display_label": "Date Spot",
                "display_order": 17,
                "icon_name": "heart",
            },
            {
                "name": "Spicy",
                "slug": "intent-spicy",
                "tag_type": TagType.INTENT,
                "display_label": "Spicy",
                "display_order": 18,
                "icon_name": "flame",
            },
            {
                "name": "LateNight",
                "slug": "intent-late-night",
                "tag_type": TagType.INTENT,
                "display_label": "Late Night",
                "display_order": 19,
                "icon_name": "moon",
            },
            {
                "name": "Breakfast",
                "slug": "intent-breakfast",
                "tag_type": TagType.INTENT,
                "display_label": "Breakfast",
                "display_order": 20,
                "icon_name": "sunrise",
            },
            # ----------------------------------------------------------------
            # PROMOTION tags (spec §4.3 — Dynamic, time-bound)
            # ----------------------------------------------------------------
            {
                "name": "DiscountLive",
                "slug": "promo-discount-live",
                "tag_type": TagType.PROMOTION,
                "display_label": "Discount Live",
                "display_order": 1,
                "icon_name": "tag",
            },
            {
                "name": "HappyHour",
                "slug": "promo-happy-hour",
                "tag_type": TagType.PROMOTION,
                "display_label": "Happy Hour",
                "display_order": 2,
                "icon_name": "clock",
            },
            {
                "name": "Buy1Get1",
                "slug": "promo-buy1get1",
                "tag_type": TagType.PROMOTION,
                "display_label": "Buy 1 Get 1",
                "display_order": 3,
                "icon_name": "gift",
            },
            {
                "name": "FlashDeal",
                "slug": "promo-flash-deal",
                "tag_type": TagType.PROMOTION,
                "display_label": "Flash Deal",
                "display_order": 4,
                "icon_name": "zap",
            },
            {
                "name": "FreeDelivery",
                "slug": "promo-free-delivery",
                "tag_type": TagType.PROMOTION,
                "display_label": "Free Delivery",
                "display_order": 5,
                "icon_name": "truck",
            },
            {
                "name": "LimitedStock",
                "slug": "promo-limited-stock",
                "tag_type": TagType.PROMOTION,
                "display_label": "Limited Stock",
                "display_order": 6,
                "icon_name": "alert-triangle",
            },
            # ----------------------------------------------------------------
            # TIME tags (spec §4.4 — Auto-generated by generate_time_context_tags)
            # ----------------------------------------------------------------
            {
                "name": "BreakfastTime",
                "slug": "time-breakfast",
                "tag_type": TagType.TIME,
                "display_label": "Breakfast",
                "display_order": 1,
                "icon_name": "sunrise",
            },
            {
                "name": "LunchTime",
                "slug": "time-lunch",
                "tag_type": TagType.TIME,
                "display_label": "Lunch",
                "display_order": 2,
                "icon_name": "sun",
            },
            {
                "name": "EveningSnacks",
                "slug": "time-evening-snacks",
                "tag_type": TagType.TIME,
                "display_label": "Evening Snacks",
                "display_order": 3,
                "icon_name": "coffee",
            },
            {
                "name": "DinnerTime",
                "slug": "time-dinner",
                "tag_type": TagType.TIME,
                "display_label": "Dinner",
                "display_order": 4,
                "icon_name": "moon",
            },
            {
                "name": "LateNightOpen",
                "slug": "time-late-night-open",
                "tag_type": TagType.TIME,
                "display_label": "Late Night Open",
                "display_order": 5,
                "icon_name": "moon",
            },
            {
                "name": "OpenNow",
                "slug": "time-open-now",
                "tag_type": TagType.TIME,
                "display_label": "Open Now",
                "display_order": 6,
                "icon_name": "clock",
            },
            # ----------------------------------------------------------------
            # SYSTEM tags (spec §4.5 — invisible to users, managed by platform)
            # ----------------------------------------------------------------
            {
                "name": "New Vendor",
                "slug": "system-new-vendor",
                "tag_type": TagType.SYSTEM,
                "display_label": "NewVendor",
                "display_order": 1,
                "icon_name": "sparkles",
            },
            {
                "name": "Claimed Vendor",
                "slug": "system-claimed-vendor",
                "tag_type": TagType.SYSTEM,
                "display_label": "ClaimedVendor",
                "display_order": 2,
                "icon_name": "shield-check",
            },
            {
                "name": "AR Priority",
                "slug": "system-ar-priority",
                "tag_type": TagType.SYSTEM,
                "display_label": "ARPriority",
                "display_order": 3,
                "icon_name": "zap",
            },
            {
                "name": "Featured In Area",
                "slug": "system-featured-in-area",
                "tag_type": TagType.SYSTEM,
                "display_label": "FeaturedInArea",
                "display_order": 4,
                "icon_name": "star",
            },
            {
                "name": "High Engagement",
                "slug": "system-high-engagement",
                "tag_type": TagType.SYSTEM,
                "display_label": "HighEngagement",
                "display_order": 5,
                "icon_name": "trending-up",
            },
        ]

        new_count = 0
        existing_count = 0
        for tag_data in seed_tags:
            tag, created = Tag.objects.get_or_create(
                slug=tag_data["slug"],
                defaults=tag_data,
            )
            if created:
                log_action(
                    "TAG_CREATED",
                    actor,
                    tag,
                    None,
                    {},
                    {"name": tag.name, "tag_type": tag.tag_type},
                )
                self.stdout.write(f"  Created Tag: {tag.name} [{tag.tag_type}]")
                new_count += 1
            else:
                self.stdout.write(f"  Tag exists: {tag.name}")
                existing_count += 1
        self.stdout.write(
            f"  Seeded {new_count + existing_count} tags ({new_count} new, {existing_count} existing) "
            f"[includes 5 SYSTEM tags for Phase B TagAutoAssigner]"
        )

    # -------------------------------------------------------------------------
    # Vendors — 3 sample vendors with encrypted phones and business hours
    # -------------------------------------------------------------------------

    def _seed_vendors(self, city: Any, area: Any, landmark: Any, actor: Any) -> None:
        """Create 3 sample vendors with encrypted phone numbers and business hours.

        Args:
            city: Karachi City instance.
            area: DHA Phase 6 Area instance.
            landmark: Zamzama Landmark instance.
            actor: AdminUser for AuditLog.
        """
        from apps.vendors.models import DataSource, Vendor
        from apps.vendors.services import create_vendor

        _STANDARD_HOURS = {
            "MON": {"open": "09:00", "close": "22:00", "is_closed": False},
            "TUE": {"open": "09:00", "close": "22:00", "is_closed": False},
            "WED": {"open": "09:00", "close": "22:00", "is_closed": False},
            "THU": {"open": "09:00", "close": "22:00", "is_closed": False},
            "FRI": {"open": "09:00", "close": "23:00", "is_closed": False},
            "SAT": {"open": "10:00", "close": "23:00", "is_closed": False},
            "SUN": {"open": "00:00", "close": "00:00", "is_closed": True},
        }

        vendors_data = [
            {
                "business_name": "Zamzama Grill House",
                "slug": "zamzama-grill-house",
                "gps_lon": 67.0601,
                "gps_lat": 24.8271,
                "phone": "+923001234567",
                "address_text": "Shop 12, Zamzama Boulevard, DHA Phase 6, Karachi",
                "description": "Premium grill restaurant on Zamzama Boulevard.",
                "data_source": DataSource.MANUAL_ENTRY,
            },
            {
                "business_name": "DHA Pharmacy Plus",
                "slug": "dha-pharmacy-plus",
                "gps_lon": 67.0610,
                "gps_lat": 24.8265,
                "phone": "+923009876543",
                "address_text": "Plot 45, Phase 6 Commercial, DHA, Karachi",
                "description": "24/7 pharmacy serving DHA Phase 6.",
                "data_source": DataSource.MANUAL_ENTRY,
            },
            {
                "business_name": "Karachi Artisan Bakery",
                "slug": "karachi-artisan-bakery",
                "gps_lon": 67.0595,
                "gps_lat": 24.8280,
                "phone": "+923331122334",
                "address_text": "Unit 3, Zamzama Lane, DHA Phase 6, Karachi",
                "description": "Artisan breads and pastries, freshly baked daily.",
                "data_source": DataSource.MANUAL_ENTRY,
            },
        ]

        for vd in vendors_data:
            if Vendor.all_objects.filter(slug=vd["slug"]).exists():
                self.stdout.write(f"  Vendor exists: {vd['business_name']}")
                continue

            vendor = create_vendor(
                business_name=vd["business_name"],
                slug=vd["slug"],
                city_id=str(city.id),
                area_id=str(area.id),
                gps_lon=vd["gps_lon"],
                gps_lat=vd["gps_lat"],
                actor=actor,
                request=None,
                phone=vd["phone"],
                description=vd["description"],
                address_text=vd["address_text"],
                landmark_id=str(landmark.id),
                business_hours=_STANDARD_HOURS,
                data_source=vd["data_source"],
            )
            self.stdout.write(f"  Created Vendor: {vendor.business_name}")

        # =================================================================
        # Step 7 — Seed SubscriptionPackage tiers (Phase B §3.1)
        # =================================================================
        self.stdout.write(self.style.MIGRATE_HEADING("\n— Seeding Subscription Packages —"))
        self._seed_subscription_packages()

    def _seed_field_visits(self, actor: Any) -> None:
        """Create sample FieldVisit records for the Field Ops page.

        Uses the existing FIELD_AGENT seed user and first 5 vendors.
        Idempotent — skips if any FieldVisit already exists.

        Args:
            actor: AdminUser used to look up or create the FIELD_AGENT user.
        """
        from datetime import timedelta

        from django.utils import timezone

        from apps.accounts.models import AdminRole, AdminUser
        from apps.field_ops.models import FieldVisit
        from apps.vendors.models import Vendor

        self.stdout.write(self.style.MIGRATE_HEADING("\n— Seeding Field Visits —"))

        if FieldVisit.objects.exists():
            self.stdout.write("  Field visits exist — skipping")
            return

        agent, _ = AdminUser.objects.get_or_create(
            email="fieldagent@airads.test",
            defaults={
                "full_name": "Field Agent",
                "role": AdminRole.FIELD_AGENT,
                "is_active": True,
            },
        )

        vendors = list(Vendor.objects.filter(is_deleted=False).order_by("created_at")[:5])
        if not vendors:
            self.stdout.write("  No vendors found — skipping field visits")
            return

        now = timezone.now()
        visits_data = [
            {
                "vendor": vendors[0],
                "visited_at": now - timedelta(days=7),
                "visit_notes": "Verified location and business signage. GPS confirmed on-site.",
                "gps_lon": 67.0601,
                "gps_lat": 24.8271,
            },
            {
                "vendor": vendors[1] if len(vendors) > 1 else vendors[0],
                "visited_at": now - timedelta(days=5),
                "visit_notes": "Confirmed operating hours match records. Minor discrepancy in phone number noted.",
                "gps_lon": 67.0610,
                "gps_lat": 24.8265,
            },
            {
                "vendor": vendors[2] if len(vendors) > 2 else vendors[0],
                "visited_at": now - timedelta(days=3),
                "visit_notes": "Vendor closed during visit — returned next day. Business confirmed active.",
                "gps_lon": 67.0595,
                "gps_lat": 24.8280,
            },
            {
                "vendor": vendors[3] if len(vendors) > 3 else vendors[0],
                "visited_at": now - timedelta(days=1),
                "visit_notes": "New signage installed. Updated photos collected.",
                "gps_lon": 67.0598,
                "gps_lat": 24.8269,
            },
            {
                "vendor": vendors[4] if len(vendors) > 4 else vendors[0],
                "visited_at": now - timedelta(hours=6),
                "visit_notes": "Routine verification visit. All details match database records.",
                "gps_lon": 67.0605,
                "gps_lat": 24.8275,
            },
        ]

        from django.contrib.gis.geos import Point

        from apps.audit.utils import log_action

        for vd in visits_data:
            visit = FieldVisit.objects.create(
                vendor=vd["vendor"],
                agent=agent,
                visited_at=vd["visited_at"],
                visit_notes=vd["visit_notes"],
                gps_confirmed_point=Point(vd["gps_lon"], vd["gps_lat"], srid=4326),
            )
            log_action(
                action="FIELD_VISIT_CREATED",
                actor=actor,
                target_obj=visit,
                request=None,
                before={},
                after={"vendor_id": str(vd["vendor"].id), "agent_id": str(agent.id)},
            )
            self.stdout.write(f"  Created FieldVisit: {vd['vendor'].business_name}")

    def _seed_subscription_packages(self) -> None:
        """Seed the 4 subscription tiers: SILVER, GOLD, DIAMOND, PLATINUM.

        Idempotent — uses get_or_create on level.
        Values match the Tiered Vendor Subscription Architecture doc.
        """
        from decimal import Decimal

        from apps.subscriptions.models import SubscriptionLevel, SubscriptionPackage

        packages = [
            {
                "level": SubscriptionLevel.SILVER,
                "name": "Silver — Visibility",
                "price_monthly": Decimal("0.00"),
                "max_videos": 1,
                "daily_happy_hours_allowed": 0,
                "has_voice_bot": False,
                "has_predictive_reports": False,
                "sponsored_placement_level": "NONE",
                "campaign_scheduling_level": "NONE",
                "voice_search_priority": "NONE",
                "visibility_boost_weight": 1.0,
            },
            {
                "level": SubscriptionLevel.GOLD,
                "name": "Gold — Control",
                "price_monthly": Decimal("2999.00"),
                "max_videos": 3,
                "daily_happy_hours_allowed": 1,
                "has_voice_bot": True,
                "has_predictive_reports": False,
                "sponsored_placement_level": "LIMITED_TIME",
                "campaign_scheduling_level": "BASIC",
                "voice_search_priority": "LOW",
                "visibility_boost_weight": 1.2,
            },
            {
                "level": SubscriptionLevel.DIAMOND,
                "name": "Diamond — Automation",
                "price_monthly": Decimal("7999.00"),
                "max_videos": 6,
                "daily_happy_hours_allowed": 3,
                "has_voice_bot": True,
                "has_predictive_reports": False,
                "sponsored_placement_level": "AREA_BOOST",
                "campaign_scheduling_level": "ADVANCED",
                "voice_search_priority": "MEDIUM",
                "visibility_boost_weight": 1.5,
            },
            {
                "level": SubscriptionLevel.PLATINUM,
                "name": "Platinum — Dominance",
                "price_monthly": Decimal("14999.00"),
                "max_videos": 999,
                "daily_happy_hours_allowed": 99,
                "has_voice_bot": True,
                "has_predictive_reports": True,
                "sponsored_placement_level": "AREA_EXCLUSIVE",
                "campaign_scheduling_level": "SMART_AUTOMATION",
                "voice_search_priority": "HIGHEST",
                "visibility_boost_weight": 2.0,
            },
        ]

        for pkg_data in packages:
            level = pkg_data.pop("level")
            obj, created = SubscriptionPackage.objects.get_or_create(
                level=level,
                defaults=pkg_data,
            )
            if created:
                self.stdout.write(f"  Created: {obj}")
            else:
                for field, value in pkg_data.items():
                    setattr(obj, field, value)
                obj.save()
                self.stdout.write(f"  Updated: {obj}")
