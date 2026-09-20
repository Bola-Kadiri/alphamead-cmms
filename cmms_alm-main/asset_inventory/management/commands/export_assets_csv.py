"""
Export a site's assets to CSV in the WBG template shape (the inverse of
import_assets_csv).

Usage:
    python manage.py export_assets_csv WBG-BEN-COT path/to/output.csv
"""
from django.core.management.base import BaseCommand, CommandError

from asset_inventory.models import Asset
from asset_inventory.services import export_assets_to_csv
from facility.models import Facility


class Command(BaseCommand):
    help = "Export a site's assets to CSV in the WBG template shape."

    def add_arguments(self, parser):
        parser.add_argument("site_code", help="Facility.code of the site to export")
        parser.add_argument("output_path", help="Path to write the CSV file to")

    def handle(self, *args, **options):
        site_code = options["site_code"]
        if not Facility.objects.filter(code=site_code).exists():
            raise CommandError(f"No site found with code '{site_code}'.")

        queryset = Asset.objects.filter(facility__code=site_code).order_by(
            'zone__name', 'subsystem__name', 'asset_tag'
        )
        with open(options["output_path"], "w", newline="", encoding="utf-8") as f:
            export_assets_to_csv(queryset, f)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {queryset.count()} assets for site '{site_code}' to {options['output_path']}"
        ))
