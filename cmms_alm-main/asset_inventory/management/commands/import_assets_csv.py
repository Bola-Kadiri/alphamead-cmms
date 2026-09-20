"""
Bulk-import sites, zones, spaces and assets from a CSV file.

Usage:
    python manage.py import_assets_csv path/to/WBG_Assets_Benin_Cotonou.csv
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from asset_inventory.services import import_assets_from_csv, format_import_summary

User = get_user_model()


class Command(BaseCommand):
    help = "Bulk-import sites/zones/spaces/assets from a CSV export (see asset_inventory/services.py for the expected columns)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file to import")

    def handle(self, *args, **options):
        owner = User.objects.filter(is_superuser=True).first()

        try:
            with open(options["csv_path"], "rb") as f:
                summary = import_assets_from_csv(f, owner=owner)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['csv_path']}")
        except ValueError as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.SUCCESS(f"Import complete: {format_import_summary(summary)}"))
