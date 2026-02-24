"""
Usage examples:
  python manage.py seed_google_places --city islamabad --area f-10
  python manage.py seed_google_places --city islamabad --area f-10 --query "cafe coffee" --radius 1200
  python manage.py seed_google_places --city lahore --area gulberg
"""

from apps.geo.models import Area, City
from apps.imports.google_places_service import GooglePlacesImportService
from apps.imports.models import ImportBatch
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed vendors from Google Places API for a given city + area"

    def add_arguments(self, parser):
        parser.add_argument("--city", required=True, help="City slug  (e.g. islamabad)")
        parser.add_argument("--area", required=True, help="Area slug  (e.g. f-10)")
        parser.add_argument(
            "--query",
            default="restaurants food breakfast chai",
            help="Search keyword sent to Google Places",
        )
        parser.add_argument(
            "--radius",
            type=int,
            default=1500,
            help="Search radius in metres (default: 1500)",
        )

    def handle(self, *args, **options):
        # ── Validate geo ───────────────────────────────────────────────────────
        try:
            city = City.objects.get(slug=options["city"])
        except City.DoesNotExist:
            raise CommandError(
                f"City '{options['city']}' not found. Run: python manage.py seed_data"
            )

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

        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n Searching Google Places...\n"
                f"   City:   {city.name}\n"
                f"   Area:   {area.name}\n"
                f"   Query:  '{options['query']}'\n"
                f"   Radius: {options['radius']}m\n"
                f"   Center: lat={centroid.y:.4f}, lng={centroid.x:.4f}\n"
            )
        )

        # ── Create batch ───────────────────────────────────────────────────────
        batch = ImportBatch.objects.create(
            import_type="GOOGLE_PLACES",
            area=area,
            search_query=options["query"],
            radius_m=options["radius"],
            search_lat=centroid.y,
            search_lng=centroid.x,
            status="QUEUED",
            created_by=None,  # management command = system actor
        )
        self.stdout.write(f"   Batch ID: {batch.id}\n")

        # ── Run synchronously (no Celery needed) ───────────────────────────────
        service = GooglePlacesImportService(batch=batch)
        completed = service.run()

        # ── Report ─────────────────────────────────────────────────────────────
        self.stdout.write("\n" + "-" * 50)
        if completed.status == "DONE":
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import complete!\n"
                    f"   Total found:   {completed.total_rows}\n"
                    f"   Vendors saved: {completed.processed_rows}\n"
                    f"   Errors:        {completed.error_count}\n\n"
                    f"   All vendors -> qc_status=PENDING\n"
                    f"   Admin Portal -> QC Queue -> filter area='{area.name}' -> review & approve\n"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Import {completed.status}\n"
                    f"   Processed: {completed.processed_rows}/{completed.total_rows}\n"
                    f"   Errors:    {completed.error_count}\n"
                )
            )
            if completed.error_log:
                self.stdout.write("First 5 errors:")
                for err in completed.error_log[:5]:
                    self.stdout.write(f"  - {err}")
