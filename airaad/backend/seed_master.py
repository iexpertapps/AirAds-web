"""
AirAd Master Seed Script
Idempotent — safe to run multiple times.
FK order: geo → accounts → vendors → discounts → voicebot →
          analytics → payments → governance → notifications → reels → field_photos
"""
import os
import sys
import django
from datetime import timedelta

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
sys.path.insert(0, ".")
django.setup()

import random
import uuid
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import AdminUser, AdminRole
from apps.vendors.models import Vendor, Discount, DiscountType, ClaimedStatus, VoiceBotConfig
from apps.reels.models import VendorReel, ModerationStatus, ReelStatus
from apps.analytics.models import AnalyticsEvent, EventType
from apps.payments.models import StripeCustomer, VendorSubscription, SubscriptionStatus
from apps.governance.models import (
    FraudScore, FraudSignal, Blacklist, BlacklistType,
    VendorSuspension, EnforcementAction,
)
from apps.notifications.models import (
    NotificationTemplate, NotificationLog,
    NotificationType, NotificationChannel, NotificationStatus, RecipientType,
)
from apps.field_ops.models import FieldVisit, FieldPhoto
from apps.subscriptions.models import SubscriptionPackage
from apps.geo.models import Landmark, City, Area

NOW = timezone.now()
actor = AdminUser.objects.filter(role=AdminRole.SUPER_ADMIN).first()
vendors = list(Vendor.objects.filter(is_deleted=False).order_by("created_at"))

print(f"\n{'='*60}")
print(f"AirAd Master Seed  |  {len(vendors)} vendors available")
print(f"{'='*60}\n")


# ── 1. Landmarks ──────────────────────────────────────────────────────────────
def seed_landmarks() -> None:
    """Seed realistic Karachi landmarks."""
    from django.contrib.gis.geos import Point
    from django.utils.text import slugify

    karachi = City.objects.filter(name__icontains="Karachi").first()
    if not karachi:
        print("  [SKIP] No Karachi city found")
        return
    dha = Area.objects.filter(name__icontains="DHA", city=karachi).first()
    clifton = Area.objects.filter(name__icontains="Clifton", city=karachi).first()
    gulshan = Area.objects.filter(name__icontains="Gulshan", city=karachi).first()
    fallback = Area.objects.filter(city=karachi).first()

    landmarks_data = [
        ("Do Talwar Roundabout", dha or fallback, Point(67.0601, 24.8271, srid=4326), ["Do Talwar", "Talwar Chowk"]),
        ("Bilawal House Intersection", clifton or fallback, Point(67.0321, 24.8455, srid=4326), ["Bilawal Chowk", "Clifton Bridge"]),
        ("Gulshan Chowrangi", gulshan or fallback, Point(67.0951, 24.9271, srid=4326), ["Gulshan Circle", "Gulshan Roundabout"]),
        ("Numaish Chowrangi", fallback, Point(67.0271, 24.8671, srid=4326), ["Numaish", "Numaish Chowk"]),
        ("Seaview Beach Entrance", clifton or fallback, Point(67.0221, 24.8121, srid=4326), ["Seaview", "Sea View Karachi"]),
    ]
    created = 0
    for name, area, point, aliases in landmarks_data:
        if not area:
            continue
        slug = slugify(name)
        if Landmark.objects.filter(name=name).exists():
            continue
        # ensure unique slug
        if Landmark.objects.filter(slug=slug).exists():
            slug = f"{slug}-karachi"
        Landmark.objects.create(
            name=name,
            slug=slug,
            area=area,
            location=point,
            aliases=aliases,
            is_active=True,
        )
        created += 1
    print(f"  [Landmarks] Created {created} | Total: {Landmark.objects.count()}")


# ── 2. VoiceBotConfig ─────────────────────────────────────────────────────────
def seed_voicebot() -> None:
    """Seed VoiceBotConfig for vendors that don't have one."""
    menus = [
        {
            "items": [
                {"name": "Lahori Chargha", "price": 850, "description": "Full roasted chicken with spices"},
                {"name": "Nihari", "price": 450, "description": "Slow-cooked beef shank curry"},
                {"name": "Paye", "price": 380, "description": "Traditional trotters curry"},
                {"name": "Karahi Gosht", "price": 1200, "description": "Fresh wok-cooked mutton"},
                {"name": "Seekh Kebab (6 pcs)", "price": 320, "description": "Minced beef skewer kebabs"},
            ],
            "faqs": [
                {"q": "Kya home delivery available hai?", "a": "Haan, 5km radius mein free delivery hai 500 rupee se upar orders par."},
                {"q": "Timing kya hai?", "a": "Subah 11 baje se raat 11 baje tak, saat din."},
                {"q": "Kya online payment accept karte hain?", "a": "Haan, JazzCash, EasyPaisa aur credit/debit card sab accept hai."},
            ],
        },
        {
            "items": [
                {"name": "Cappuccino", "price": 380, "description": "Double shot espresso with steamed milk foam"},
                {"name": "Croissant", "price": 220, "description": "Butter croissant, freshly baked"},
                {"name": "Club Sandwich", "price": 550, "description": "Triple-decker with chicken, egg and veggies"},
                {"name": "Brownie Sundae", "price": 480, "description": "Warm chocolate brownie with vanilla ice cream"},
                {"name": "Strawberry Cheesecake", "price": 420, "description": "New York style baked cheesecake"},
            ],
            "faqs": [
                {"q": "WiFi available hai?", "a": "Haan, free WiFi available hai. Password counter par puchein."},
                {"q": "Kya birthday parties arrange ho sakti hain?", "a": "Bilkul! Advance booking ke liye 03XX-XXXXXXX par call karein."},
                {"q": "Vegetarian options hain?", "a": "Haan, hamare menu ka 40% vegetarian hai."},
            ],
        },
        {
            "items": [
                {"name": "Sourdough Loaf", "price": 680, "description": "48-hour fermented artisan sourdough"},
                {"name": "Cinnamon Roll", "price": 280, "description": "Freshly baked with cream cheese glaze"},
                {"name": "Almond Croissant", "price": 320, "description": "Flaky croissant filled with almond cream"},
                {"name": "Custom Birthday Cake (1kg)", "price": 2500, "description": "Custom design, 48hr advance order"},
                {"name": "Assorted Cookies Box (12pcs)", "price": 750, "description": "Mix of chocolate chip, oatmeal, shortbread"},
            ],
            "faqs": [
                {"q": "Custom cake orders kab tak dete hain?", "a": "Minimum 48 ghante advance order zaroori hai."},
                {"q": "Kya gluten-free options hain?", "a": "Haan, limited gluten-free items available hain — pehle confirm karein."},
                {"q": "Bulk corporate orders possible hain?", "a": "Haan, 10% discount milta hai 20+ items par."},
            ],
        },
        {
            "items": [
                {"name": "Panadol Tablet (10s)", "price": 45, "description": "Standard paracetamol 500mg"},
                {"name": "Disprin (10s)", "price": 35, "description": "Aspirin 325mg effervescent"},
                {"name": "Multivitamin (30 tabs)", "price": 450, "description": "Complete daily nutrition support"},
                {"name": "Betadine Antiseptic", "price": 280, "description": "Povidone iodine antiseptic solution"},
                {"name": "ORS Sachets (10s)", "price": 120, "description": "Oral rehydration salts for dehydration"},
            ],
            "faqs": [
                {"q": "Kya 24 ghante open ho?", "a": "Haan, hum 24/7 open hain aur home delivery bhi karte hain."},
                {"q": "Doctor ki prescription zaroori hai?", "a": "Schedule drugs ke liye prescription zaroori hai. OTC drugs bina prescription ke mil jaate hain."},
                {"q": "Kya medical equipment rent par milti hai?", "a": "Haan, wheelchair aur crutches rent par available hain."},
            ],
        },
        {
            "items": [
                {"name": "Mutton Biryani (Full)", "price": 1800, "description": "Serves 4-5 persons, dum cooked"},
                {"name": "Chicken Biryani (Half)", "price": 700, "description": "Serves 2 persons, aromatic basmati"},
                {"name": "Raita", "price": 80, "description": "Fresh yogurt with roasted cumin"},
                {"name": "Shami Kebab (4 pcs)", "price": 280, "description": "Pan-fried lentil and minced meat patties"},
                {"name": "Qeema Naan", "price": 180, "description": "Tandoor bread stuffed with spiced mince"},
            ],
            "faqs": [
                {"q": "Catering service available hai?", "a": "Haan, 50+ log ke events ke liye special catering packages hain."},
                {"q": "Halal certified hain?", "a": "Bilkul! Hum fully halal certified restaurant hain."},
                {"q": "Kya outdoor seating hai?", "a": "Haan, 20 persons ki outdoor seating available hai."},
            ],
        },
    ]

    existing_vendor_ids = set(VoiceBotConfig.objects.values_list("vendor_id", flat=True))
    vendors_needing = [v for v in vendors if v.id not in existing_vendor_ids]
    created = 0
    for i, vendor in enumerate(vendors_needing):
        menu_data = menus[i % len(menus)]
        VoiceBotConfig.objects.create(
            vendor=vendor,
            menu_items=menu_data["items"],
            faq_pairs=menu_data["faqs"],
            is_active=True,
            language_code="ur-PK",
            custom_greeting=f"Salam! {vendor.business_name} mein khush aamdeed. Mein aapki kaise madad kar sakta hoon?",
        )
        created += 1
    print(f"  [VoiceBotConfig] Created {created} | Total: {VoiceBotConfig.objects.count()}")


# ── 3. Discounts ──────────────────────────────────────────────────────────────
def seed_discounts() -> None:
    """Seed realistic Pakistani promotional discounts."""
    existing_vendor_ids = set(Discount.objects.values_list("vendor_id", flat=True))
    vendors_needing = [v for v in vendors if v.id not in existing_vendor_ids][:20]

    discount_templates = [
        {
            "title": "Ramadan Special — 20% Off All Orders",
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": 20,
            "description": "Celebrate Ramadan with a 20% discount on all dine-in orders during Iftar hours (6pm–9pm).",
            "min_order_value": 500,
            "days_offset": 30,
        },
        {
            "title": "Happy Hour Deal — Buy 1 Get 1 Free",
            "discount_type": DiscountType.BUY_ONE_GET_ONE,
            "discount_value": 100,
            "description": "Every weekday 3pm–6pm, buy any main course and get one free. Dine-in only.",
            "min_order_value": 0,
            "days_offset": 14,
        },
        {
            "title": "Weekend Flash Sale — Rs. 200 Off",
            "discount_type": DiscountType.FIXED_AMOUNT,
            "discount_value": 200,
            "description": "Every Saturday and Sunday, get Rs. 200 off on orders above Rs. 1000.",
            "min_order_value": 1000,
            "days_offset": 7,
        },
        {
            "title": "Student Discount — 15% Off",
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": 15,
            "description": "Show your student ID and get 15% off on all orders. Valid Monday to Thursday.",
            "min_order_value": 300,
            "days_offset": 60,
        },
        {
            "title": "Lunch Special — 25% Off Combo",
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": 25,
            "description": "Weekday lunch combo (12pm–3pm): any main + drink + dessert at 25% off.",
            "min_order_value": 600,
            "days_offset": 21,
        },
        {
            "title": "Family Pack — Rs. 500 Off Large Orders",
            "discount_type": DiscountType.FIXED_AMOUNT,
            "discount_value": 500,
            "description": "Order for 4 or more people and get Rs. 500 off. Perfect for family gatherings.",
            "min_order_value": 2500,
            "days_offset": 45,
        },
        {
            "title": "New Customer Welcome — 10% Off First Order",
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": 10,
            "description": "First time visiting us? Get 10% off your entire order. Welcome to the family!",
            "min_order_value": 200,
            "days_offset": 90,
        },
        {
            "title": "Evening Flash Deal — 30% Off (6pm–8pm)",
            "discount_type": DiscountType.FLASH_DEAL,
            "discount_value": 30,
            "description": "Limited time evening flash deal every day from 6pm to 8pm. First come first served.",
            "min_order_value": 400,
            "days_offset": 3,
        },
    ]

    created = 0
    for i, vendor in enumerate(vendors_needing):
        template = discount_templates[i % len(discount_templates)]
        start = NOW - timedelta(days=random.randint(1, 5))
        end = start + timedelta(days=template["days_offset"])
        Discount.objects.create(
            vendor=vendor,
            title=template["title"],
            description=template["description"],
            discount_type=template["discount_type"],
            discount_value=template["discount_value"],
            min_order_value=template["min_order_value"],
            valid_from=start,
            valid_until=end,
            is_active=True,
        )
        created += 1
    print(f"  [Discounts] Created {created} | Total: {Discount.objects.count()}")


# ── 4. Analytics Events ───────────────────────────────────────────────────────
def seed_analytics() -> None:
    """Seed realistic analytics events per vendor."""
    if AnalyticsEvent.objects.count() > 100:
        print(f"  [Analytics] Already seeded ({AnalyticsEvent.objects.count()} events) — skipping")
        return

    event_configs = [
        (EventType.VENDOR_VIEW, 0.35),
        (EventType.PROFILE_TAP, 0.20),
        (EventType.REEL_VIEW, 0.15),
        (EventType.DISCOUNT_TAP, 0.12),
        (EventType.NAVIGATION_STARTED, 0.10),
        (EventType.VOICE_QUERY_MADE, 0.05),
        (EventType.REEL_SHARE, 0.03),
    ]

    karachi_areas = list(Area.objects.filter(city__name__icontains="Karachi")[:10])
    created = 0

    for vendor in vendors:
        base_views = random.randint(80, 800)
        for event_type, ratio in event_configs:
            count = max(1, int(base_views * ratio))
            events = []
            for _ in range(count):
                days_ago = random.randint(0, 30)
                events.append(AnalyticsEvent(
                    event_type=event_type,
                    vendor=vendor,
                    gps_lat=24.8271 + random.uniform(-0.05, 0.05),
                    gps_lon=67.0601 + random.uniform(-0.05, 0.05),
                    area=random.choice(karachi_areas) if karachi_areas else None,
                    metadata={"source": "mobile_app", "session_id": str(uuid.uuid4())[:8]},
                    created_at=NOW - timedelta(days=days_ago, hours=random.randint(0, 23)),
                ))
            AnalyticsEvent.objects.bulk_create(events, ignore_conflicts=True)
            created += count

        vendor.total_views = random.randint(100, 2500)
        vendor.total_profile_taps = random.randint(20, 800)
        vendor.save(update_fields=["total_views", "total_profile_taps", "updated_at"])

    print(f"  [Analytics] Created {created} events | Vendor stats updated")


# ── 5. Payments / Subscriptions ───────────────────────────────────────────────
def seed_payments() -> None:
    """Seed Stripe customers and subscriptions for claimed vendors."""
    packages = {p.level: p for p in SubscriptionPackage.objects.all()}
    if not packages:
        print("  [Payments] No subscription packages found — skipping")
        return

    claimed_vendors = [v for v in vendors if v.claimed_status == ClaimedStatus.CLAIMED]
    if not claimed_vendors:
        print("  [Payments] No CLAIMED vendors found — skipping")
        return

    tier_map = [
        ("SILVER", 0.5),
        ("GOLD", 0.3),
        ("DIAMOND", 0.2),
    ]

    existing_customer_ids = set(StripeCustomer.objects.values_list("vendor_id", flat=True))
    existing_sub_ids = set(VendorSubscription.objects.values_list("vendor_id", flat=True))
    created_c = created_s = 0

    for i, vendor in enumerate(claimed_vendors):
        cus_id = f"cus_seed_{str(vendor.id)[:8]}"
        sub_id = f"sub_seed_{str(vendor.id)[:8]}"

        if vendor.id not in existing_customer_ids:
            StripeCustomer.objects.create(vendor=vendor, stripe_customer_id=cus_id)
            created_c += 1

        if vendor.id not in existing_sub_ids:
            tier_name = random.choices(
                [t[0] for t in tier_map],
                weights=[t[1] for t in tier_map],
            )[0]
            pkg = packages.get(tier_name)
            period_start = NOW - timedelta(days=random.randint(1, 25))
            period_end = period_start + timedelta(days=30)
            VendorSubscription.objects.create(
                vendor=vendor,
                package=pkg,
                stripe_subscription_id=sub_id,
                stripe_customer_id=cus_id,
                stripe_price_id=f"price_{tier_name.lower()}_monthly",
                status=SubscriptionStatus.ACTIVE,
                current_period_start=period_start,
                current_period_end=period_end,
            )
            if pkg:
                vendor.subscription_level = tier_name
                vendor.subscription_valid_until = period_end
                vendor.save(update_fields=["subscription_level", "subscription_valid_until", "updated_at"])
            created_s += 1

    print(f"  [Payments] StripeCustomers: +{created_c} | VendorSubscriptions: +{created_s}")


# ── 6. Field Photos ───────────────────────────────────────────────────────────
def seed_field_photos() -> None:
    """Seed FieldPhoto records linked to existing field visits."""
    if FieldPhoto.objects.count() > 0:
        print(f"  [FieldPhotos] Already seeded ({FieldPhoto.objects.count()}) — skipping")
        return

    visits = list(FieldVisit.objects.select_related("vendor").all())
    photo_captions = [
        "Business signage and entrance", "Interior seating area",
        "Display counter and menu board", "GPS confirmation screenshot",
        "Parking area and building exterior",
    ]
    created = 0
    for visit in visits:
        for j in range(random.randint(2, 3)):
            slug = visit.vendor.slug or str(visit.vendor.id)[:8]
            FieldPhoto.objects.create(
                visit=visit,
                s3_key=f"field-photos/{slug}/visit_{str(visit.id)[:8]}_{j+1}.jpg",
                caption=photo_captions[j % len(photo_captions)],
            )
            created += 1
    print(f"  [FieldPhotos] Created {created} | Total: {FieldPhoto.objects.count()}")


# ── 7. Notification Templates ─────────────────────────────────────────────────
def seed_notification_templates() -> None:
    """Seed all notification templates the system needs."""
    templates = [
        {
            "slug": "claim_approved",
            "title_template": "Your claim for {vendor_name} has been approved!",
            "body_template": (
                "Congratulations {full_name}! Your ownership claim for {vendor_name} "
                "has been approved. You can now manage your business profile, add promotions, "
                "upload reels, and access analytics from your vendor dashboard."
            ),
            "notification_type": NotificationType.CLAIM_STATUS,
        },
        {
            "slug": "claim_rejected",
            "title_template": "Your claim for {vendor_name} could not be verified",
            "body_template": (
                "Hi {full_name}, unfortunately your ownership claim for {vendor_name} "
                "has been rejected. Reason: {rejection_reason}. "
                "You may resubmit with additional documentation within 7 days."
            ),
            "notification_type": NotificationType.CLAIM_STATUS,
        },
        {
            "slug": "reel_approved",
            "title_template": "Your reel '{reel_title}' is now live!",
            "body_template": (
                "Great news! Your video '{reel_title}' for {vendor_name} has passed moderation "
                "and is now visible to customers on AirAds."
            ),
            "notification_type": NotificationType.MODERATION,
        },
        {
            "slug": "reel_rejected",
            "title_template": "Your reel '{reel_title}' was not approved",
            "body_template": (
                "Hi {full_name}, your video '{reel_title}' did not pass our content review. "
                "Reason: {rejection_reason}. Please review our content guidelines and resubmit."
            ),
            "notification_type": NotificationType.MODERATION,
        },
        {
            "slug": "subscription_activated",
            "title_template": "Welcome to {tier_name} tier — your subscription is active!",
            "body_template": (
                "Hi {full_name}! Your {tier_name} subscription for {vendor_name} is now active "
                "until {valid_until}. Enjoy your new features including {feature_highlight}."
            ),
            "notification_type": NotificationType.SUBSCRIPTION,
        },
        {
            "slug": "subscription_expiring_soon",
            "title_template": "Your subscription expires in {days_left} days",
            "body_template": (
                "Hi {full_name}, your {tier_name} subscription for {vendor_name} expires on "
                "{expiry_date}. Renew now to keep your premium features active."
            ),
            "notification_type": NotificationType.SUBSCRIPTION,
        },
        {
            "slug": "promotion_approved",
            "title_template": "Your promotion '{promo_title}' is live!",
            "body_template": (
                "Your promotion '{promo_title}' for {vendor_name} is now visible to customers. "
                "It will run until {valid_until}. Track performance in your analytics dashboard."
            ),
            "notification_type": NotificationType.PROMOTION,
        },
        {
            "slug": "vendor_suspension_warning",
            "title_template": "Important: Policy violation warning for {vendor_name}",
            "body_template": (
                "Your account {vendor_name} has received a policy violation warning. "
                "Reason: {reason}. Please review our terms of service. "
                "Continued violations may result in account suspension."
            ),
            "notification_type": NotificationType.SYSTEM,
        },
    ]
    created = 0
    for tpl in templates:
        _, was_created = NotificationTemplate.objects.get_or_create(
            slug=tpl["slug"],
            defaults={
                "title_template": tpl["title_template"],
                "body_template": tpl["body_template"],
                "notification_type": tpl["notification_type"],
                "is_active": True,
            },
        )
        if was_created:
            created += 1
    print(f"  [NotificationTemplates] Created {created} | Total: {NotificationTemplate.objects.count()}")


# ── 8. Governance — FraudScore + Blacklist + Suspension ───────────────────────
def seed_governance() -> None:
    """Seed fraud scores, blacklist entries, and suspensions."""
    existing_fraud_ids = set(FraudScore.objects.values_list("vendor_id", flat=True))
    fraud_vendors = [v for v in vendors[:10] if v.id not in existing_fraud_ids]
    created_f = 0

    signals_pool = [
        FraudSignal.USER_REPORT,
        FraudSignal.GPS_ANOMALY,
        FraudSignal.EXCESSIVE_PROMOTIONS,
        FraudSignal.DUPLICATE_CLAIM,
    ]

    for i, vendor in enumerate(fraud_vendors):
        num_signals = random.randint(1, 3)
        chosen_signals = random.sample(signals_pool, min(num_signals, len(signals_pool)))
        score = sum({"USER_REPORT": 1, "GPS_ANOMALY": 2, "EXCESSIVE_PROMOTIONS": 1, "DUPLICATE_CLAIM": 2}.get(s, 1) for s in chosen_signals)
        signal_log = [
            {
                "signal": s,
                "score_delta": {"USER_REPORT": 1, "GPS_ANOMALY": 2, "EXCESSIVE_PROMOTIONS": 1, "DUPLICATE_CLAIM": 2}.get(s, 1),
                "reason": f"Automated signal: {s.lower().replace('_', ' ')}",
                "ts": (NOW - timedelta(days=random.randint(1, 14))).isoformat(),
            }
            for s in chosen_signals
        ]
        FraudScore.objects.create(
            vendor=vendor,
            actor_email=vendor.slug + "@vendor.airads.test",
            score=score,
            is_auto_suspended=score >= 6,
            signals=signal_log,
        )
        created_f += 1

    # Blacklist entries
    blacklist_data = [
        (BlacklistType.PHONE_NUMBER, "+923001110001", "Multiple fraudulent claim attempts from this number"),
        (BlacklistType.PHONE_NUMBER, "+923002220002", "Verified scam operator — police complaint filed"),
        (BlacklistType.GPS_COORDINATE, "24.8500,67.0100", "GPS coordinates fall in restricted zone"),
        (BlacklistType.DEVICE_ID, "android_dev_abc123def456", "Device linked to 3 rejected claims"),
        (BlacklistType.DEVICE_ID, "ios_dev_xyz789uvw012", "Reported for fake promotion flooding"),
    ]
    created_b = 0
    for btype, value, reason in blacklist_data:
        _, created = Blacklist.objects.get_or_create(
            blacklist_type=btype,
            value=value,
            defaults={"reason": reason, "added_by": actor, "is_active": True},
        )
        if created:
            created_b += 1

    # Suspensions
    suspension_vendors = [v for v in vendors[:3] if not v.suspensions.exists()]
    created_s = 0
    suspension_templates = [
        (EnforcementAction.WARNING, "Misleading promotion — discount amount not honoured at checkout.", "Section 3.2 — Promotion Accuracy"),
        (EnforcementAction.CONTENT_REMOVAL, "Reel contained third-party copyrighted music without license.", "Section 5.1 — Content Ownership"),
        (EnforcementAction.TEMPORARY_SUSPENSION, "Multiple verified customer complaints about fake discounts.", "Section 8.2 — Enforcement Ladder"),
    ]
    for vendor, (action, reason, policy) in zip(suspension_vendors, suspension_templates):
        ends_at = NOW + timedelta(days=7) if action == EnforcementAction.TEMPORARY_SUSPENSION else None
        VendorSuspension.objects.create(
            vendor=vendor,
            action=action,
            reason=reason,
            policy_reference=policy,
            issued_by=actor,
            suspension_ends_at=ends_at,
            is_active=True,
        )
        created_s += 1

    print(f"  [Governance] FraudScores: +{created_f} | Blacklist: +{created_b} | Suspensions: +{created_s}")


# ── 9. More Reels (top-up to 15 pending) ─────────────────────────────────────
def seed_reels() -> None:
    """Top up pending moderation reels to 15."""
    current_pending = VendorReel.objects.filter(moderation_status=ModerationStatus.PENDING).count()
    target = 15
    needed = target - current_pending
    if needed <= 0:
        print(f"  [Reels] Already {current_pending} pending — skipping")
        return

    reel_titles = [
        "Grand Opening Celebration Highlights",
        "Behind the Kitchen — Chef Special",
        "Customer Reviews & Testimonials",
        "New Menu Launch — Spring 2025",
        "Ramadan Iftar Buffet Preview",
        "Store Tour & Product Showcase",
        "Daily Deals Announcement",
        "Team Introduction & Welcome",
        "Special Event Coverage",
        "Monthly Promotion Spotlight",
    ]

    existing_vendor_ids = set(VendorReel.objects.values_list("vendor_id", flat=True))
    reel_vendors = [v for v in vendors if v.id not in existing_vendor_ids] or vendors
    created = 0

    for i in range(needed):
        vendor = reel_vendors[i % len(reel_vendors)]
        slug = vendor.slug or str(vendor.id)[:8]
        title = reel_titles[i % len(reel_titles)]
        VendorReel.objects.create(
            vendor=vendor,
            title=title,
            s3_key=f"reels/{slug}/{title.lower().replace(' ', '_')[:30]}_{i}.mp4",
            thumbnail_s3_key=f"reels/{slug}/thumb_{i}.jpg",
            duration_seconds=random.randint(15, 90),
            status=ReelStatus.PROCESSING,
            moderation_status=ModerationStatus.PENDING,
            display_order=i,
        )
        created += 1

    print(f"  [Reels] Created {created} | Total pending: {VendorReel.objects.filter(moderation_status=ModerationStatus.PENDING).count()}")


# ── 10. Vendor stats top-up ───────────────────────────────────────────────────
def seed_vendor_stats() -> None:
    """Ensure all vendors have realistic view/tap counts."""
    no_views = Vendor.objects.filter(total_views=0)
    updated = 0
    for v in no_views:
        v.total_views = random.randint(50, 1500)
        v.total_profile_taps = random.randint(10, 400)
        v.total_navigation_clicks = random.randint(5, 200)
        v.save(update_fields=["total_views", "total_profile_taps", "total_navigation_clicks", "updated_at"])
        updated += 1
    print(f"  [VendorStats] Updated {updated} vendors with realistic engagement counts")


# ── Run all seeders ───────────────────────────────────────────────────────────
with transaction.atomic():
    print("Step 1: Landmarks")
    seed_landmarks()

    print("\nStep 2: VoiceBotConfig")
    seed_voicebot()

    print("\nStep 3: Discounts")
    seed_discounts()

    print("\nStep 4: Analytics Events")
    seed_analytics()

    print("\nStep 5: Payments & Subscriptions")
    seed_payments()

    print("\nStep 6: Field Photos")
    seed_field_photos()

    print("\nStep 7: Notification Templates")
    seed_notification_templates()

    print("\nStep 8: Governance")
    seed_governance()

    print("\nStep 9: Reels top-up")
    seed_reels()

    print("\nStep 10: Vendor stats")
    seed_vendor_stats()

print(f"\n{'='*60}")
print("SEED COMPLETE — Final counts:")
print(f"  Vendors:               {Vendor.objects.count()}")
print(f"  Discounts:             {Discount.objects.count()}")
print(f"  VoiceBotConfigs:       {VoiceBotConfig.objects.count()}")
print(f"  Reels (pending):       {VendorReel.objects.filter(moderation_status=ModerationStatus.PENDING).count()}")
print(f"  Analytics Events:      {AnalyticsEvent.objects.count()}")
print(f"  StripeCustomers:       {StripeCustomer.objects.count()}")
print(f"  VendorSubscriptions:   {VendorSubscription.objects.count()}")
print(f"  FraudScores:           {FraudScore.objects.count()}")
print(f"  Blacklist Entries:     {Blacklist.objects.count()}")
print(f"  Suspensions:           {VendorSuspension.objects.count()}")
print(f"  NotifTemplates:        {NotificationTemplate.objects.count()}")
print(f"  FieldPhotos:           {FieldPhoto.objects.count()}")
print(f"  Landmarks:             {Landmark.objects.count()}")
print(f"{'='*60}\n")
