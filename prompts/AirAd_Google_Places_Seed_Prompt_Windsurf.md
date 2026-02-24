# AirAd — Google Places Import & Database Seeding
### Windsurf Prompt — Copy this entire block into Windsurf

---

## CONTEXT

You are working on the AirAd Django backend. The existing codebase has:
- `apps/vendors/models.py` — `Vendor` model with PostGIS `PointField`, `phone_number_encrypted` (BinaryField), `qc_status`, `data_source`, `is_deleted`
- `apps/geo/models.py` — `Country`, `City`, `Area`, `Landmark` models (Area has `centroid` PointField and `slug`)
- `apps/tags/models.py` — `Tag` model with `tag_type` (CATEGORY, INTENT, SYSTEM, etc.) and `slug`
- `apps/imports/models.py` — `ImportBatch` model with `status`, `error_log`, `processed_rows`, `total_rows`, `error_count`
- `apps/audit/utils.py` — `log_action(action, actor, target_obj, request, before, after, actor_label, request_id)` function
- `core/encryption.py` — `encrypt(value: str) -> bytes` and `decrypt(value: bytes) -> str`
- `celery_app.py` — Celery app already configured

**DO NOT** modify any existing model fields. Only ADD what is specified below.

---

## YOUR TASK — Build these 7 deliverables in order

---

## DELIVERABLE 1 — Model Additions + Migration

### 1A. `apps/vendors/models.py` — Add to existing `Vendor` class:

```python
google_place_id = models.CharField(
    max_length=300,
    blank=True,
    null=True,
    unique=True,
    db_index=True,
    help_text="Google Places place_id — used for upsert deduplication on re-import"
)
website_url = models.URLField(
    blank=True,
    default="",
    help_text="Business website from Google Places"
)
```

### 1B. `apps/imports/models.py` — Add to existing `ImportBatch` class:

```python
import_type = models.CharField(
    max_length=20,
    choices=[("CSV", "CSV Upload"), ("GOOGLE_PLACES", "Google Places API")],
    default="CSV",
    db_index=True,
)
area = models.ForeignKey(
    "geo.Area",
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="google_places_batches",
)
search_query = models.CharField(max_length=255, blank=True, default="")
radius_m     = models.PositiveIntegerField(null=True, blank=True)
search_lat   = models.FloatField(null=True, blank=True)
search_lng   = models.FloatField(null=True, blank=True)
```

### 1C. Generate and apply migrations:

```bash
python manage.py makemigrations vendors imports --name google_places_fields
python manage.py migrate
```

---

## DELIVERABLE 2 — Google Places Service

Create: `apps/imports/google_places_service.py`

```python
"""
Google Places Nearby Search -> AirAd Vendor upsert service.

Flow:
  1. Nearby Search (paginated, max 3 pages = 60 results)
  2. Place Details per result (name, phone, hours, GPS, website)
  3. Map fields -> Vendor schema
  4. Encrypt phone with core/encryption.encrypt()
  5. Map business_hours to AirAd format
  6. Upsert Vendor via google_place_id (idempotent)
  7. Auto-assign up to 3 Category tags from Google Place types (Rule R2)
  8. Write AuditLog entry per vendor
  9. Log per-place errors -> batch.error_log (capped at 1000)
"""

import logging
import time
from typing import Optional

import httpx
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction

from apps.audit.utils import log_action
from apps.geo.models import Area
from apps.imports.models import ImportBatch
from apps.tags.models import Tag
from apps.vendors.models import Vendor
from core.encryption import encrypt

logger = logging.getLogger(__name__)

GOOGLE_TYPE_TO_TAG_SLUG: dict[str, str] = {
    "restaurant":             "restaurant",
    "food":                   "food",
    "cafe":                   "cafe",
    "bakery":                 "bakery",
    "meal_takeaway":          "takeaway",
    "meal_delivery":          "delivery",
    "bar":                    "bar",
    "fast_food":              "fast-food",
    "pizza":                  "pizza",
    "grocery_or_supermarket": "grocery",
    "convenience_store":      "convenience-store",
    "store":                  "retail",
}

DAY_MAP: dict[int, str] = {
    0: "sunday", 1: "monday", 2: "tuesday", 3: "wednesday",
    4: "thursday", 5: "friday", 6: "saturday",
}

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS = (
    "place_id,name,formatted_address,geometry,formatted_phone_number,"
    "opening_hours,types,website,rating"
)


class GooglePlacesImportService:

    def __init__(self, batch: ImportBatch):
        self.batch = batch
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.client = httpx.Client(timeout=15)
        self._tag_cache: dict[str, Optional[Tag]] = {}

    def run(self) -> ImportBatch:
        area = Area.objects.select_related("city").get(id=self.batch.area_id)
        logger.info(
            f"[GooglePlaces] Batch {self.batch.id} starting | "
            f"area={area.name} | query='{self.batch.search_query}' | "
            f"radius={self.batch.radius_m}m"
        )
        self.batch.status = "PROCESSING"
        self.batch.save(update_fields=["status"])

        try:
            place_ids = self._nearby_search_all_pages()
            self.batch.total_rows = len(place_ids)
            self.batch.save(update_fields=["total_rows"])

            for place_id in place_ids:
                self._process_one_place(place_id, area)

            self.batch.status = "DONE"
        except Exception as exc:
            logger.exception(f"[GooglePlaces] Batch {self.batch.id} top-level failure")
            self._log_error({"error": str(exc), "phase": "batch-level"})
            self.batch.status = "FAILED"
        finally:
            self.batch.save(update_fields=["status", "processed_rows", "error_count"])
            self.client.close()

        logger.info(
            f"[GooglePlaces] Batch {self.batch.id} {self.batch.status} | "
            f"{self.batch.processed_rows} processed, {self.batch.error_count} errors"
        )
        return self.batch

    def _nearby_search_all_pages(self) -> list[str]:
        place_ids: list[str] = []
        params = {
            "location": f"{self.batch.search_lat},{self.batch.search_lng}",
            "radius":   self.batch.radius_m,
            "keyword":  self.batch.search_query,
            "type":     "food",
            "key":      self.api_key,
        }
        url = NEARBY_URL
        while True:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            api_status = data.get("status")
            if api_status == "ZERO_RESULTS":
                break
            if api_status != "OK":
                logger.warning(f"[GooglePlaces] Nearby Search status: {api_status}")
                break
            for r in data.get("results", []):
                pid = r.get("place_id")
                if pid and pid not in place_ids:
                    place_ids.append(pid)
            next_token = data.get("next_page_token")
            if not next_token:
                break
            time.sleep(2)  # Google requires delay before next_page_token is valid
            params = {"pagetoken": next_token, "key": self.api_key}
        logger.info(f"[GooglePlaces] Found {len(place_ids)} places")
        return place_ids

    def _fetch_details(self, place_id: str) -> Optional[dict]:
        resp = self.client.get(DETAILS_URL, params={
            "place_id": place_id,
            "fields":   DETAILS_FIELDS,
            "key":      self.api_key,
        })
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK":
            return data.get("result", {})
        return None

    def _process_one_place(self, place_id: str, area: Area) -> None:
        try:
            details = self._fetch_details(place_id)
            if not details:
                self._log_error({"place_id": place_id, "error": "Place Details returned empty"})
                return
            vendor = self._upsert_vendor(details, place_id, area)
            self._assign_tags(vendor, details.get("types", []))
            log_action(
                action="vendor.google_places_upsert",
                actor=None,
                target_obj=vendor,
                request=None,
                before=None,
                after={"business_name": vendor.business_name, "place_id": place_id},
                actor_label="SYSTEM_GOOGLE_PLACES",
                request_id=str(self.batch.id),
            )
            self.batch.processed_rows += 1
        except Exception as exc:
            logger.warning(f"[GooglePlaces] Failed place {place_id}: {exc}")
            self._log_error({"place_id": place_id, "error": str(exc)})

    @transaction.atomic
    def _upsert_vendor(self, details: dict, place_id: str, area: Area) -> Vendor:
        geo = details.get("geometry", {}).get("location", {})
        lat, lng = geo.get("lat"), geo.get("lng")
        if not lat or not lng:
            raise ValueError("Missing GPS in Place Details")

        raw_phone = details.get("formatted_phone_number", "")
        phone_enc = encrypt(raw_phone) if raw_phone else b""
        gps = Point(lng, lat, srid=4326)  # PostGIS: Point(lng, lat) NOT Point(lat, lng)

        vendor, created = Vendor.objects.update_or_create(
            google_place_id=place_id,
            defaults={
                "business_name":          details.get("name", "").strip(),
                "address_text":           details.get("formatted_address", ""),
                "gps_point":              gps,
                "gps_baseline":           gps,
                "phone_number_encrypted": phone_enc,
                "business_hours":         self._map_hours(
                    details.get("opening_hours", {}).get("periods", [])
                ),
                "website_url":            details.get("website", ""),
                "data_source":            "GOOGLE_PLACES",
                "qc_status":              "PENDING",
                "is_deleted":             False,
                "area":                   area,
            }
        )
        action = "Created" if created else "Updated"
        logger.info(f"[GooglePlaces] {action}: {vendor.business_name}")
        return vendor

    def _map_hours(self, periods: list) -> dict:
        """
        Google Places periods -> AirAd BusinessHoursSchema.

        Google:  {"open": {"day": 1, "time": "0800"}, "close": {"day": 1, "time": "2200"}}
        AirAd:   {"monday": {"open": "08:00", "close": "22:00", "is_closed": false}}
        """
        result = {
            day: {"open": "00:00", "close": "00:00", "is_closed": True}
            for day in DAY_MAP.values()
        }
        for period in periods:
            open_info  = period.get("open", {})
            close_info = period.get("close", {})
            day_idx    = open_info.get("day")
            if day_idx is None:
                continue
            day_name   = DAY_MAP.get(day_idx)
            open_t     = open_info.get("time", "0000")
            close_t    = close_info.get("time", "0000")
            result[day_name] = {
                "open":      f"{open_t[:2]}:{open_t[2:]}",
                "close":     f"{close_t[:2]}:{close_t[2:]}",
                "is_closed": False,
            }
        return result

    def _assign_tags(self, vendor: Vendor, google_types: list[str]) -> None:
        """Assign up to 3 Category tags from Google Place types. Enforces Rule R2."""
        assigned = 0
        for gtype in google_types:
            if assigned >= 3:
                break
            slug = GOOGLE_TYPE_TO_TAG_SLUG.get(gtype)
            if not slug:
                continue
            if slug not in self._tag_cache:
                self._tag_cache[slug] = Tag.objects.filter(
                    slug=slug, tag_type="CATEGORY", is_active=True
                ).first()
            tag = self._tag_cache[slug]
            if tag and not vendor.tags.filter(id=tag.id).exists():
                vendor.tags.add(tag)
                assigned += 1

    def _log_error(self, entry: dict) -> None:
        if len(self.batch.error_log) >= 1000:  # cap at 1000 per spec
            return
        self.batch.error_log.append(entry)
        self.batch.error_count += 1
        self.batch.save(update_fields=["error_log", "error_count"])
```

---

## DELIVERABLE 3 — Celery Task

Create: `apps/imports/tasks_google_places.py`

```python
"""
Celery task for Google Places import.
Receives ONLY batch_id — all params live on ImportBatch record.
"""
import logging
from celery import shared_task
from apps.imports.models import ImportBatch

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="imports.process_google_places_import",
)
def process_google_places_import(self, batch_id: str) -> dict:
    """
    Idempotency: skips if batch already PROCESSING or DONE.
    Retries up to 3 times on failure with exponential backoff.
    """
    try:
        batch = ImportBatch.objects.get(id=batch_id)
    except ImportBatch.DoesNotExist:
        logger.error(f"ImportBatch {batch_id} not found")
        return {"error": "not_found"}

    if batch.status in ("PROCESSING", "DONE"):
        logger.warning(f"Batch {batch_id} already {batch.status} — skipping")
        return {"status": batch.status, "skipped": True}

    from apps.imports.google_places_service import GooglePlacesImportService
    try:
        service = GooglePlacesImportService(batch=batch)
        completed = service.run()
        return {
            "status":         completed.status,
            "processed_rows": completed.processed_rows,
            "error_count":    completed.error_count,
        }
    except Exception as exc:
        logger.exception(f"Google Places task failed for batch {batch_id}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

---

## DELIVERABLE 4 — API Endpoint

Create: `apps/imports/views_google_places.py`

```python
"""
POST /api/v1/imports/google-places/

Request body:
  { "area_id": "<uuid>", "search_query": "restaurants food", "radius_m": 1500 }

Response 202:
  { "success": true, "data": { "batch_id": "...", "status": "QUEUED", "poll_url": "..." } }
"""
import logging
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import RolePermission
from apps.geo.models import Area
from apps.imports.models import ImportBatch
from apps.imports.tasks_google_places import process_google_places_import

logger = logging.getLogger(__name__)


class GooglePlacesImportRequestSerializer(serializers.Serializer):
    area_id      = serializers.UUIDField()
    search_query = serializers.CharField(max_length=255, default="restaurants food")
    radius_m     = serializers.IntegerField(min_value=100, max_value=5000, default=1500)

    def validate_area_id(self, value):
        try:
            return Area.objects.get(id=value)
        except Area.DoesNotExist:
            raise serializers.ValidationError(f"Area {value} does not exist.")


class GooglePlacesImportView(APIView):
    """POST /api/v1/imports/google-places/"""
    permission_classes = [
        RolePermission.for_roles("IMPORT_OPERATOR", "DATA_MANAGER", "SUPER_ADMIN")
    ]

    def post(self, request):
        ser = GooglePlacesImportRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "data": None, "message": "Validation failed",
                 "errors": ser.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        vd   = ser.validated_data
        area: Area = vd["area_id"]  # validate_area_id returns Area object

        centroid = getattr(area, "centroid", None)
        if not centroid:
            return Response(
                {"success": False,
                 "message": f"Area '{area.name}' has no centroid. Set area.centroid first.",
                 "errors": {"area_id": ["Area centroid required."]}},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch = ImportBatch.objects.create(
            import_type  ="GOOGLE_PLACES",
            area         = area,
            search_query = vd["search_query"],
            radius_m     = vd["radius_m"],
            search_lat   = centroid.y,  # PostGIS Point(lng,lat) -> .y = lat
            search_lng   = centroid.x,
            status       = "QUEUED",
            created_by   = request.user,
        )

        # Pass ONLY batch_id to Celery — never raw data
        process_google_places_import.delay(str(batch.id))
        logger.info(f"Google Places import queued | batch={batch.id} | area={area.name}")

        return Response({
            "success": True,
            "data": {
                "batch_id":     str(batch.id),
                "status":       "QUEUED",
                "area":         area.name,
                "search_query": vd["search_query"],
                "radius_m":     vd["radius_m"],
                "poll_url":     f"/api/v1/imports/{batch.id}/",
            },
            "message": "Import queued. Poll poll_url for progress.",
            "errors":  None,
        }, status=status.HTTP_202_ACCEPTED)
```

---

## DELIVERABLE 5 — URL Registration

In `apps/imports/urls.py`, add to existing `urlpatterns`:

```python
from apps.imports.views_google_places import GooglePlacesImportView

path("imports/google-places/", GooglePlacesImportView.as_view(), name="google-places-import"),
```

---

## DELIVERABLE 6 — Settings

In `config/settings/base.py`, add:

```python
GOOGLE_PLACES_API_KEY = env("GOOGLE_PLACES_API_KEY", default="")
```

In `.env`:
```
GOOGLE_PLACES_API_KEY=AIzaSy_YOUR_KEY_HERE
```

In `.env.example`:
```
# Get from: https://console.cloud.google.com -> APIs & Services -> Credentials
# Enable "Places API" on your GCP project first
GOOGLE_PLACES_API_KEY=GET_FROM_GOOGLE_CLOUD_CONSOLE
```

In `requirements/base.txt` (if not already present):
```
httpx==0.27.*
```

---

## DELIVERABLE 7 — Management Command (Seed Without Celery)

Create: `apps/imports/management/commands/seed_google_places.py`

This command seeds any area directly from the terminal — no Celery worker needed. Best for local dev and initial data loading.

```python
"""
Usage examples:
  python manage.py seed_google_places --city islamabad --area f-10
  python manage.py seed_google_places --city islamabad --area f-10 --query "cafe coffee" --radius 1200
  python manage.py seed_google_places --city lahore --area gulberg
"""
from django.core.management.base import BaseCommand, CommandError
from apps.geo.models import City, Area
from apps.imports.models import ImportBatch
from apps.imports.google_places_service import GooglePlacesImportService


class Command(BaseCommand):
    help = "Seed vendors from Google Places API for a given city + area"

    def add_arguments(self, parser):
        parser.add_argument("--city",   required=True,  help="City slug  (e.g. islamabad)")
        parser.add_argument("--area",   required=True,  help="Area slug  (e.g. f-10)")
        parser.add_argument("--query",  default="restaurants food breakfast chai",
                            help="Search keyword sent to Google Places")
        parser.add_argument("--radius", type=int, default=1500,
                            help="Search radius in metres (default: 1500)")

    def handle(self, *args, **options):
        # ── Validate geo ───────────────────────────────────────────────────────
        try:
            city = City.objects.get(slug=options["city"])
        except City.DoesNotExist:
            raise CommandError(f"City '{options['city']}' not found. Run: python manage.py seed_data")

        try:
            area = Area.objects.get(slug=options["area"], city=city)
        except Area.DoesNotExist:
            raise CommandError(
                f"Area '{options['area']}' not found under city '{options['city']}'.\n"
                f"Run: python manage.py seed_data"
            )

        centroid = getattr(area, "centroid", None)
        if not centroid:
            raise CommandError(
                f"Area '{area.name}' has no centroid PointField set.\n"
                f"Fix: area.centroid = Point(lng, lat, srid=4326); area.save()"
            )

        self.stdout.write(self.style.HTTP_INFO(
            f"\n Searching Google Places...\n"
            f"   City:   {city.name}\n"
            f"   Area:   {area.name}\n"
            f"   Query:  '{options['query']}'\n"
            f"   Radius: {options['radius']}m\n"
            f"   Center: lat={centroid.y:.4f}, lng={centroid.x:.4f}\n"
        ))

        # ── Create batch ───────────────────────────────────────────────────────
        batch = ImportBatch.objects.create(
            import_type  ="GOOGLE_PLACES",
            area         = area,
            search_query = options["query"],
            radius_m     = options["radius"],
            search_lat   = centroid.y,
            search_lng   = centroid.x,
            status       = "QUEUED",
            created_by   = None,  # management command = system actor
        )
        self.stdout.write(f"   Batch ID: {batch.id}\n")

        # ── Run synchronously (no Celery needed) ───────────────────────────────
        service = GooglePlacesImportService(batch=batch)
        completed = service.run()

        # ── Report ─────────────────────────────────────────────────────────────
        self.stdout.write("\n" + "-" * 50)
        if completed.status == "DONE":
            self.stdout.write(self.style.SUCCESS(
                f"Import complete!\n"
                f"   Total found:   {completed.total_rows}\n"
                f"   Vendors saved: {completed.processed_rows}\n"
                f"   Errors:        {completed.error_count}\n\n"
                f"   All vendors -> qc_status=PENDING\n"
                f"   Admin Portal -> QC Queue -> filter area='{area.name}' -> review & approve\n"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Import {completed.status}\n"
                f"   Processed: {completed.processed_rows}/{completed.total_rows}\n"
                f"   Errors:    {completed.error_count}\n"
            ))
            if completed.error_log:
                self.stdout.write("First 5 errors:")
                for err in completed.error_log[:5]:
                    self.stdout.write(f"  - {err}")
```

---

## AFTER WRITING ALL FILES — Run in this exact order:

```bash
# Step 1 — Migrations
python manage.py makemigrations vendors imports --name google_places_fields
python manage.py migrate

# Step 2 — Make sure seed_data ran first (geo + tags must exist)
python manage.py seed_data

# Step 3 — Verify F-10 area centroid (run in Django shell)
python manage.py shell -c "
from apps.geo.models import Area
from django.contrib.gis.geos import Point
try:
    area = Area.objects.get(slug='f-10')
    if not area.centroid:
        area.centroid = Point(73.0229, 33.7001, srid=4326)
        area.save()
        print('Centroid set for F-10')
    else:
        print(f'F-10 centroid OK: {area.centroid}')
except Area.DoesNotExist:
    print('ERROR: F-10 area not found. Run seed_data first.')
"

# Step 4 — Seed F-10 food points (Round 1: restaurants)
python manage.py seed_google_places \
  --city islamabad \
  --area f-10 \
  --query "restaurants food breakfast chai paratha" \
  --radius 1500

# Step 5 — Seed F-10 (Round 2: cafes and sweets, safe to re-run)
python manage.py seed_google_places \
  --city islamabad \
  --area f-10 \
  --query "cafe coffee bakery sweets mithai" \
  --radius 1200

# Step 6 — Verify results
python manage.py shell -c "
from apps.vendors.models import Vendor
qs = Vendor.objects.filter(area__slug='f-10', data_source='GOOGLE_PLACES', is_deleted=False)
print(f'F-10 vendors from Google Places: {qs.count()}')
for v in qs[:10]:
    print(f'  {v.business_name} | qc={v.qc_status}')
"
```

---

## RULES — DO NOT VIOLATE ANY OF THESE

```
RULE 1 — GPS storage
  ALWAYS: Point(lng, lat, srid=4326)   <- lng first, then lat
  NEVER:  Point(lat, lng)  or separate FloatFields

RULE 2 — Phone encryption
  ALWAYS: phone_number_encrypted = encrypt(raw_phone)
  NEVER:  store phone as plaintext, even temporarily

RULE 3 — Celery task payload
  ALWAYS: pass batch_id (str) only
  NEVER:  pass API keys, coordinates, or CSV content through Celery broker

RULE 4 — Deduplication
  ALWAYS: Vendor.objects.update_or_create(google_place_id=place_id, defaults={...})
  This makes every re-run fully safe — no duplicate vendors ever created

RULE 5 — Error handling
  ALWAYS: log error to batch.error_log, continue processing next place
  NEVER:  abort entire batch on single-place failure
  CAP:    error_log max 1000 entries (enforced in _log_error)

RULE 6 — Category tags
  Max 3 per vendor (Rule R2). Stop at assigned >= 3.

RULE 7 — QC status
  All Google Places vendors -> qc_status='PENDING'
  Human QC review required before any vendor goes live

RULE 8 — AuditLog
  Every vendor upsert -> log_action(actor=None, actor_label='SYSTEM_GOOGLE_PLACES')
  request_id = str(batch.id)
```

---

*AirAd — Google Places Seed Prompt for Windsurf v1.0*
*Stack: Django 5.x + PostGIS + Celery + httpx + AES-256-GCM*
*Idempotent: YES — safe to re-run (deduplication via google_place_id)*
*Celery optional: Management command runs synchronously without Celery*
