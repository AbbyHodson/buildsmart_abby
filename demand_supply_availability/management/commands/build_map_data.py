# demand_supply_availability/management/commands/build_map_data.py
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from demand_supply_availability.est_default_availability import (
    MATERIALS,
    build_map_data,
    base_path,
)


class Command(BaseCommand):
    help = "Rebuild map_data.json from the availability spreadsheet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--materials",
            nargs="+",
            choices=MATERIALS,
            default=MATERIALS,
            help="Subset of materials to process (default: all).",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Override the output path for map_data.json.",
        )

    def handle(self, *args, **options):
        if not os.path.exists(base_path):
            raise CommandError(f"Spreadsheet not found at {base_path}")

        materials = options["materials"]
        self.stdout.write(f"Processing {len(materials)} material(s)...")

        try:
            out_path = build_map_data(
                materials=materials,
                output_path=options["output"],
                log=self.stdout.write,
            )
        except Exception as exc:
            raise CommandError(f"Build failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Wrote {out_path}"))
