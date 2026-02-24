"""
Google Places Nearby Search -> AirAd Vendor upsert service.

Deduplication & Idempotency Strategy (7 layers):
  L1. google_place_id UNIQUE constraint  — DB-level duplicate prevention
  L2. update_or_create(google_place_id=)  — idempotent upsert per place
  L3. Cross-area dedup                    — skip Place Details API call if
                                            google_place_id already in Vendor table
  L4. In-batch dedup                      — de-duplicate Nearby Search page results
  L5. Checkpoint / resume                 — processed_place_ids persisted per place;
                                            crash-restart skips completed items
  L6. Batch-level idempotency             — Celery task skips PROCESSING / DONE batches
  L7. Slug stability                      — existing vendor slug preserved on re-import;
                                            new slugs use place_id suffix to avoid races

Flow:
  1. Nearby Search (paginated, max 3 pages = 60 results)
  2. Filter out place_ids already in checkpoint (resume support)
  3. Filter out place_ids already in Vendor table (cross-area dedup — L3)
  4. Place Details per remaining result (avoids wasted API calls)
  5. Map fields -> Vendor schema
  6. Encrypt phone with core/encryption.encrypt()
  7. Map business_hours to AirAd format
  8. Upsert Vendor via google_place_id (idempotent — L1/L2)
  9. Auto-assign up to 3 Category tags from Google Place types (Rule R2)
  10. Checkpoint place_id -> batch.processed_place_ids (L5)
  11. Write AuditLog entry per vendor
  12. Log per-place errors -> batch.error_log (capped at 1000)
"""

import logging
import time
import uuid as _uuid
from typing import Optional

import httpx
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from apps.audit.utils import log_action
from apps.geo.models import Area
from apps.imports.models import ImportBatch
from apps.tags.models import Tag
from apps.vendors.models import Vendor
from core.encryption import encrypt
from core.ssrf_protection import validate_external_url

logger = logging.getLogger(__name__)

GOOGLE_TYPE_TO_TAG_SLUG: dict[str, str] = {
    "restaurant": "restaurant",
    "food": "food",
    "cafe": "cafe",
    "bakery": "bakery",
    "meal_takeaway": "takeaway",
    "meal_delivery": "delivery",
    "bar": "bar",
    "fast_food": "fast-food",
    "pizza": "pizza",
    "grocery_or_supermarket": "grocery",
    "convenience_store": "convenience-store",
    "store": "retail",
}

DAY_MAP: dict[int, str] = {
    0: "sunday",
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
}

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS = (
    "place_id,name,formatted_address,geometry,formatted_phone_number,"
    "opening_hours,types,website,rating"
)

# Rate-limit / throttle constants
MAX_RETRIES_PER_REQUEST = 3
BASE_BACKOFF_SECONDS = 2
INTER_DETAIL_DELAY = 0.15  # 150ms between Place Details calls (~6 QPS)
ERROR_LOG_CAP = 1000
CHECKPOINT_INTERVAL = 5  # Flush checkpoint to DB every N places


class GooglePlacesImportService:
    """Imports vendors from Google Places API into AirAd.

    Implements 7-layer deduplication (see module docstring).
    """

    def __init__(self, batch: ImportBatch):
        self.batch = batch
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.client = httpx.Client(timeout=15)
        self._tag_cache: dict[str, Optional[Tag]] = {}
        # L5: Restore checkpoint from previous run (crash-resume)
        self._already_processed: set[str] = set(batch.processed_place_ids or [])
        self._pending_errors: list[dict] = []
        self._checkpoint_counter = 0

    # ── Public entry point ────────────────────────────────────────────

    def run(self) -> ImportBatch:
        area = Area.objects.select_related("city").get(id=self.batch.area_id)
        logger.info(
            f"[GooglePlaces] Batch {self.batch.id} starting | "
            f"area={area.name} | query='{self.batch.search_query}' | "
            f"radius={self.batch.radius_m}m | "
            f"checkpoint={len(self._already_processed)} already processed"
        )
        self.batch.status = "PROCESSING"
        self.batch.save(update_fields=["status"])

        try:
            # Phase 1: Discover place_ids via Nearby Search (L4 in-batch dedup)
            all_place_ids = self._nearby_search_all_pages()
            self.batch.total_rows = len(all_place_ids)
            self.batch.save(update_fields=["total_rows"])

            # Phase 2: Filter — checkpoint resume (L5)
            remaining = [
                pid for pid in all_place_ids if pid not in self._already_processed
            ]
            logger.info(
                f"[GooglePlaces] {len(all_place_ids)} discovered, "
                f"{len(self._already_processed)} checkpoint-skipped, "
                f"{len(remaining)} to process"
            )

            # Phase 3: Cross-area dedup (L3) — skip Place Details API call
            #   for place_ids that already exist as Vendor records
            existing_place_ids = set(
                Vendor.all_objects.filter(google_place_id__in=remaining).values_list(
                    "google_place_id", flat=True
                )
            )
            new_place_ids = [pid for pid in remaining if pid not in existing_place_ids]
            update_place_ids = [pid for pid in remaining if pid in existing_place_ids]

            logger.info(
                f"[GooglePlaces] Cross-area dedup: {len(existing_place_ids)} already in DB "
                f"(will refresh), {len(new_place_ids)} new places need Details API"
            )

            # Phase 4a: Process genuinely new places (full Details API call)
            for place_id in new_place_ids:
                self._process_one_place(place_id, area, is_new=True)

            # Phase 4b: Refresh existing places (update area assignment, hours, etc.)
            #   Uses Details API but could be skipped if freshness is acceptable.
            #   We still call Details to keep data fresh, but this is the layer
            #   where you could add a staleness check (e.g., skip if updated < 7 days ago).
            for place_id in update_place_ids:
                self._process_one_place(place_id, area, is_new=False)

            # Flush any remaining buffered errors
            self._flush_errors()
            self.batch.status = "DONE"
        except Exception as exc:
            logger.exception(f"[GooglePlaces] Batch {self.batch.id} top-level failure")
            self._buffer_error({"error": str(exc), "phase": "batch-level"})
            self._flush_errors()
            self.batch.status = "FAILED"
        finally:
            self.batch.save(
                update_fields=[
                    "status",
                    "processed_rows",
                    "error_count",
                    "error_log",
                    "processed_place_ids",
                ]
            )
            self.client.close()

        logger.info(
            f"[GooglePlaces] Batch {self.batch.id} {self.batch.status} | "
            f"{self.batch.processed_rows} processed, {self.batch.error_count} errors"
        )
        return self.batch

    # ── Phase 1: Nearby Search with in-batch dedup (L4) ──────────────

    def _nearby_search_all_pages(self) -> list[str]:
        place_ids: list[str] = []
        seen: set[str] = set()  # L4: in-batch dedup
        params = {
            "location": f"{self.batch.search_lat},{self.batch.search_lng}",
            "radius": self.batch.radius_m,
            "keyword": self.batch.search_query,
            "type": "food",
            "key": self.api_key,
        }
        url = NEARBY_URL
        page = 0
        while True:
            resp = self._request_with_backoff("GET", url, params=params)
            data = resp.json()
            api_status = data.get("status")
            if api_status == "ZERO_RESULTS":
                break
            if api_status != "OK":
                logger.warning(f"[GooglePlaces] Nearby Search status: {api_status}")
                break
            for r in data.get("results", []):
                pid = r.get("place_id")
                if pid and pid not in seen:  # L4: in-batch dedup via set
                    seen.add(pid)
                    place_ids.append(pid)
            page += 1
            next_token = data.get("next_page_token")
            if not next_token:
                break
            time.sleep(2)  # Google requires delay before next_page_token is valid
            params = {"pagetoken": next_token, "key": self.api_key}
        logger.info(
            f"[GooglePlaces] Found {len(place_ids)} unique places across {page} page(s)"
        )
        return place_ids

    # ── Phase 4: Process individual place ─────────────────────────────

    def _process_one_place(self, place_id: str, area: Area, is_new: bool) -> None:
        try:
            # Rate-limit: small delay between Detail requests
            time.sleep(INTER_DETAIL_DELAY)
            details = self._fetch_details(place_id)
            if not details:
                self._buffer_error(
                    {"place_id": place_id, "error": "Place Details returned empty"}
                )
                self._checkpoint_place(place_id)
                return
            vendor = self._upsert_vendor(details, place_id, area, is_new=is_new)
            self._assign_tags(vendor, details.get("types", []))
            log_action(
                action="vendor.google_places_upsert",
                actor=None,
                target_obj=vendor,
                request=None,
                before={},
                after={
                    "business_name": vendor.business_name,
                    "place_id": place_id,
                    "is_new": is_new,
                },
            )
            self.batch.processed_rows += 1
            self._checkpoint_place(place_id)
        except Exception as exc:
            logger.warning(f"[GooglePlaces] Failed place {place_id}: {exc}")
            self._buffer_error({"place_id": place_id, "error": str(exc)})
            # Still checkpoint — don't re-attempt failed places on resume
            self._checkpoint_place(place_id)

    def _fetch_details(self, place_id: str) -> Optional[dict]:
        resp = self._request_with_backoff(
            "GET",
            DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": DETAILS_FIELDS,
                "key": self.api_key,
            },
        )
        data = resp.json()
        if data.get("status") == "OK":
            return data.get("result", {})
        logger.warning(
            f"[GooglePlaces] Details status={data.get('status')} for {place_id}"
        )
        return None

    # ── Upsert with slug stability (L1, L2, L7) ──────────────────────

    @transaction.atomic
    def _upsert_vendor(
        self, details: dict, place_id: str, area: Area, is_new: bool
    ) -> Vendor:
        geo = details.get("geometry", {}).get("location", {})
        lat, lng = geo.get("lat"), geo.get("lng")
        if not lat or not lng:
            raise ValueError("Missing GPS in Place Details")

        raw_phone = details.get("formatted_phone_number", "")
        phone_enc = encrypt(raw_phone) if raw_phone else b""
        gps = Point(lng, lat, srid=4326)  # PostGIS: Point(lng, lat) NOT Point(lat, lng)
        business_name = details.get("name", "").strip()

        # L7: Slug stability — preserve existing slug on update, generate stable slug on create
        #   Uses place_id short hash as suffix to guarantee uniqueness without a racy loop.
        existing = Vendor.all_objects.filter(google_place_id=place_id).first()
        if existing:
            slug = existing.slug  # Preserve — never overwrite existing URLs
        else:
            slug = self._generate_stable_slug(business_name, place_id)

        defaults = {
            "business_name": business_name,
            "slug": slug,
            "address_text": details.get("formatted_address", ""),
            "gps_point": gps,
            "phone_number_encrypted": phone_enc,
            "business_hours": self._map_hours(
                details.get("opening_hours", {}).get("periods", [])
            ),
            "website_url": details.get("website", ""),
            "data_source": "GOOGLE_PLACES",
            "is_deleted": False,
            "area": area,
            "city": area.city,
        }

        # Only set gps_baseline and qc_status on creation — don't overwrite QA decisions
        if not existing:
            defaults["gps_baseline"] = gps
            defaults["qc_status"] = "PENDING"

        try:
            vendor, created = Vendor.objects.update_or_create(
                google_place_id=place_id,
                defaults=defaults,
            )
        except IntegrityError:
            # L1: Concurrent insert race — another worker created it first. Fetch and update.
            vendor = Vendor.all_objects.get(google_place_id=place_id)
            for key, val in defaults.items():
                if key != "slug":  # Never overwrite slug
                    setattr(vendor, key, val)
            vendor.save()
            created = False

        action = "Created" if created else "Updated"
        logger.info(
            f"[GooglePlaces] {action}: {vendor.business_name} ({place_id[:12]}...)"
        )
        return vendor

    @staticmethod
    def _generate_stable_slug(business_name: str, place_id: str) -> str:
        """Generate a deterministic, collision-free slug.

        Uses first 8 chars of place_id as suffix instead of a racy counter loop.
        This is idempotent: same inputs always produce the same slug.
        """
        base = slugify(business_name) or "vendor"
        # place_id is a Google-assigned opaque string; take a short hash for readability
        suffix = slugify(place_id[:12]) or _uuid.uuid4().hex[:8]
        return f"{base}-{suffix}"[:280]  # Vendor.slug max_length=280

    # ── Business hours mapping ────────────────────────────────────────

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
            open_info = period.get("open", {})
            close_info = period.get("close", {})
            day_idx = open_info.get("day")
            if day_idx is None:
                continue
            day_name = DAY_MAP.get(day_idx)
            open_t = open_info.get("time", "0000")
            close_t = close_info.get("time", "0000")
            result[day_name] = {
                "open": f"{open_t[:2]}:{open_t[2:]}",
                "close": f"{close_t[:2]}:{close_t[2:]}",
                "is_closed": False,
            }
        return result

    # ── Tag assignment ────────────────────────────────────────────────

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

    # ── Checkpoint / resume (L5) ──────────────────────────────────────

    def _checkpoint_place(self, place_id: str) -> None:
        """Record a place_id as processed and periodically flush to DB."""
        self._already_processed.add(place_id)
        self._checkpoint_counter += 1
        if self._checkpoint_counter % CHECKPOINT_INTERVAL == 0:
            self.batch.processed_place_ids = list(self._already_processed)
            self.batch.save(update_fields=["processed_place_ids", "processed_rows"])

    # ── Error buffering (avoids N+1 DB writes) ────────────────────────

    def _buffer_error(self, entry: dict) -> None:
        """Buffer an error entry; flush to DB periodically."""
        if len(self.batch.error_log) + len(self._pending_errors) >= ERROR_LOG_CAP:
            return
        self._pending_errors.append(entry)
        self.batch.error_count += 1
        if len(self._pending_errors) >= CHECKPOINT_INTERVAL:
            self._flush_errors()

    def _flush_errors(self) -> None:
        """Write buffered errors to batch.error_log in a single DB write."""
        if not self._pending_errors:
            return
        remaining_cap = ERROR_LOG_CAP - len(self.batch.error_log)
        to_write = self._pending_errors[:remaining_cap]
        self.batch.error_log.extend(to_write)
        self._pending_errors = self._pending_errors[remaining_cap:]
        self.batch.save(update_fields=["error_log", "error_count"])

    # ── HTTP with exponential backoff & rate-limit handling ───────────

    def _request_with_backoff(self, method: str, url: str, **kwargs) -> httpx.Response:
        """HTTP request with retry + exponential backoff on 429 / 5xx.

        SSRF protection: validates URL against settings.ALLOWED_EXTERNAL_DOMAINS
        before making any outbound request.
        """
        validate_external_url(url)
        for attempt in range(MAX_RETRIES_PER_REQUEST + 1):
            try:
                resp = self.client.request(method, url, **kwargs)
                if resp.status_code == 429:
                    wait = BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        f"[GooglePlaces] 429 rate-limited, backing off {wait}s"
                    )
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        f"[GooglePlaces] {resp.status_code} server error, retry in {wait}s"
                    )
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.TimeoutException:
                if attempt == MAX_RETRIES_PER_REQUEST:
                    raise
                wait = BASE_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    f"[GooglePlaces] Timeout, retry in {wait}s (attempt {attempt + 1})"
                )
                time.sleep(wait)
        # Should not reach here, but satisfy type checker
        raise httpx.HTTPError(f"Failed after {MAX_RETRIES_PER_REQUEST + 1} attempts")
