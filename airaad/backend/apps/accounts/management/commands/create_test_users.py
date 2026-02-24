from apps.accounts.services import create_admin_user
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Create test users for all 11 admin roles"

    def handle(self, *args, **options):
        test_users = [
            # Phase-A data-collection roles
            ("admin@airads.test", "Super Admin", "SUPER_ADMIN"),
            ("citymanager@airads.test", "City Manager", "CITY_MANAGER"),
            ("dataentry@airads.test", "Data Entry", "DATA_ENTRY"),
            ("qareviewer@airads.test", "QA Reviewer", "QA_REVIEWER"),
            ("fieldagent@airads.test", "Field Agent", "FIELD_AGENT"),
            ("analyst@airads.test", "Analyst", "ANALYST"),
            ("support@airads.test", "Support", "SUPPORT"),
            # Governance roles (spec §2.1)
            ("opsmanager@airads.test", "Operations Manager", "OPERATIONS_MANAGER"),
            ("moderator@airads.test", "Content Moderator", "CONTENT_MODERATOR"),
            (
                "dataqualityanalyst@airads.test",
                "Data Quality Analyst",
                "DATA_QUALITY_ANALYST",
            ),
            (
                "analyticsobserver@airads.test",
                "Analytics Observer",
                "ANALYTICS_OBSERVER",
            ),
        ]

        with transaction.atomic():
            for email, full_name, role in test_users:
                try:
                    from apps.accounts.models import AdminUser

                    if AdminUser.objects.filter(email=email).exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f"User {email} already exists - skipping"
                            )
                        )
                        continue

                    user, temp_password = create_admin_user(
                        email=email,
                        full_name=full_name,
                        role=role,
                        actor=None,  # System creation
                        request=None,
                        password="admin@123",
                        must_change_password=False,
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created {role}: {email} | Password: {temp_password}"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to create {email}: {str(e)}")
                    )

        self.stdout.write(self.style.SUCCESS("Test user creation complete!"))
