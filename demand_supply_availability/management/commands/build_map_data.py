# demand_supply_availability/management/commands/build_map_data.py
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from demand_supply_availability.est_availability import (
    MATERIALS,
    SCENARIOS,
    build_map_data,
    base_path,
)
class Command(BaseCommand):
    help = "Rebuild from the availability spreadsheet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--materials",
            nargs="+",
            choices=MATERIALS,
            default=MATERIALS,
            help="Subset of materials to process (default: all).",
        )
        parser.add_argument(
            "--scenarios",
            nargs="+",
            choices=SCENARIOS,
            default=SCENARIOS,
            help="Subset of scenarios to process (default: all).",
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
        scenarios = options["scenarios"]
        self.stdout.write(f"Processing {len(materials)} material(s)...")
        self.stdout.write(f"Processing {len(scenarios)} scenario(s)...")

        try:
            out_path = build_map_data(
                materials=materials,
                scenarios=scenarios,
                output_path=options["output"],
                log=self.stdout.write,
            )
        except Exception as exc:
            raise CommandError(f"Build failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Wrote {out_path}"))
