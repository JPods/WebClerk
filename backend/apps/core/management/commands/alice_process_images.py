"""Process catalog files (images and documents) for items.

Two file categories:
  Images    — product photos → resize to tn/md/hires .jpg
  Documents — QA, SDS, install videos, spec sheets → store original

Two modes:
  1. source  — Process raw files from a Connection's catalog_config source_path.
               Allie/Andi sets the path. Alice processes locally.
               First converter pays; result pushes up to DynamicCatalogs for all.
  2. library — Download pre-processed files from DynamicCatalogs/WC_HQ.
               Alice WC_HQ provides each local Alice with an alternative path.

The catalog library shares FILES, never pricing. Different retailers may
have different price points for the same product.

Usage:
    # Process raw images from a configured source
    ./bin/python manage.py alice_process_images source --connection "AdvChm-Images"
    ./bin/python manage.py alice_process_images source --connection "AdvChm-Images" --type document

    # Download from catalog library (DynamicCatalogs)
    ./bin/python manage.py alice_process_images library --connection "WC_HQ"
    ./bin/python manage.py alice_process_images library --connection "WC_HQ" --skus HW-DRL-001

    # Set up a new catalog source connection
    ./bin/python manage.py alice_process_images setup --name "AdvChm-Images" \\
        --source-path ".../jitWebAdChimney/images/Click2Order" \\
        --match-by sku --tn-subdir TN
"""
from django.core.management.base import BaseCommand

from apps.core.services.image_import import process_source_files, download_from_library


class Command(BaseCommand):
    help = "Process images for items — local source or remote library download."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="mode", help="Processing mode")

        # ── source mode ──
        source_parser = sub.add_parser("source", help="Process raw files from source path")
        source_parser.add_argument("--connection", type=str, help="Connection name")
        source_parser.add_argument("--connection-id", type=int, help="Connection PK")
        source_parser.add_argument("--type", type=str, default="image",
                                   choices=["image", "document"],
                                   help="File type to process (default: image)")
        source_parser.add_argument("--dry-run", action="store_true",
                                   help="Show what would be processed without writing")

        # ── library mode ──
        lib_parser = sub.add_parser("library", help="Download from catalog library")
        lib_parser.add_argument("--connection", type=str, help="Connection name")
        lib_parser.add_argument("--connection-id", type=int, help="Connection PK")
        lib_parser.add_argument("--type", type=str, default="image",
                                choices=["image", "document"],
                                help="File type to download (default: image)")
        lib_parser.add_argument("--skus", type=str, help="Comma-separated SKUs to limit scope")
        lib_parser.add_argument("--dry-run", action="store_true",
                                help="Check availability without downloading")

        # ── setup mode ──
        setup_parser = sub.add_parser("setup", help="Create an image source connection")
        setup_parser.add_argument("--name", type=str, required=True, help="Connection name")
        setup_parser.add_argument("--source-path", type=str, required=True,
                                  help="Path to raw images")
        setup_parser.add_argument("--match-by", type=str, default="sku",
                                  choices=["sku", "ida", "filename"],
                                  help="How to match filenames to items")
        setup_parser.add_argument("--filename-pattern", type=str, default="{sku}.jpg",
                                  help="Filename pattern with {sku}/{ida} placeholder")
        setup_parser.add_argument("--tn-subdir", type=str, default="",
                                  help="Subdirectory name for existing thumbnails (e.g. TN)")
        setup_parser.add_argument("--default-alt", type=str, default="{name}",
                                  help="Alt text template with {name}/{sku} placeholders")

    def handle(self, *args, **options):
        mode = options.get("mode")
        if not mode:
            self.stderr.write(self.style.ERROR("Specify mode: source, library, or setup"))
            return

        if mode == "source":
            self._handle_source(options)
        elif mode == "library":
            self._handle_library(options)
        elif mode == "setup":
            self._handle_setup(options)

    def _resolve_connection(self, options):
        """Find connection by name or ID."""
        from apps.sync.models import Connection

        conn_id = options.get("connection_id")
        conn_name = options.get("connection")

        if conn_id:
            return Connection.objects.get(pk=conn_id)
        elif conn_name:
            return Connection.objects.get(name=conn_name)
        else:
            self.stderr.write(self.style.ERROR("Provide --connection or --connection-id"))
            return None

    def _handle_source(self, options):
        conn = self._resolve_connection(options)
        if not conn:
            return

        file_type = options.get("type", "image")
        dry_run = options.get("dry_run", False)
        self.stdout.write(f"Processing {file_type}s from: {conn.name}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — no files will be written"))

        result = process_source_files(
            connection_id=conn.pk,
            file_type=file_type,
            dry_run=dry_run,
        )

        if result.get("error"):
            self.stderr.write(self.style.ERROR(f"  Error: {result['error']}"))
            return

        self.stdout.write(f"  Processed: {result['processed']}")
        self.stdout.write(f"  Skipped:   {result['skipped']}")
        self.stdout.write(f"  Errors:    {len(result['errors'])}")

        for item in result.get("items", []):
            self.stdout.write(f"    {item['sku']} ({item['ida']})")

        for err in result.get("errors", []):
            self.stderr.write(self.style.WARNING(f"    ! {err}"))

        self.stdout.write(self.style.SUCCESS("Done."))

    def _handle_library(self, options):
        conn = self._resolve_connection(options)
        if not conn:
            return

        file_type = options.get("type", "image")
        dry_run = options.get("dry_run", False)
        skus = options.get("skus")

        item_ids = None
        if skus:
            from apps.products.models import Item
            sku_list = [s.strip() for s in skus.split(",")]
            item_ids = list(
                Item.objects.filter(sku__in=sku_list, is_active=True)
                .values_list("pk", flat=True)
            )
            if not item_ids:
                self.stderr.write(self.style.ERROR(f"No items found for SKUs: {skus}"))
                return

        self.stdout.write(f"Downloading {file_type}s from library: {conn.name}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — checking availability only"))

        result = download_from_library(
            connection_id=conn.pk,
            item_ids=item_ids,
            file_type=file_type,
            dry_run=dry_run,
        )

        if result.get("error"):
            self.stderr.write(self.style.ERROR(f"  Error: {result['error']}"))
            return

        self.stdout.write(f"  Downloaded:     {result['downloaded']}")
        self.stdout.write(f"  Already local:  {result['already_local']}")
        self.stdout.write(f"  Not available:  {result['not_available']}")
        self.stdout.write(f"  Errors:         {len(result['errors'])}")

        for err in result.get("errors", []):
            self.stderr.write(self.style.WARNING(f"    ! {err}"))

        self.stdout.write(self.style.SUCCESS("Done."))

    def _handle_setup(self, options):
        """Create a Connection for catalog file importing."""
        from apps.sync.models import Connection

        name = options["name"]
        source_path = options["source_path"]

        catalog_config = {
            "source_path": source_path,
            "match_by": options["match_by"],
            "filename_pattern": options["filename_pattern"],
            "subdirs": {},
            "default_alt": options["default_alt"],
            "file_types": ["image", "document"],
        }

        tn_subdir = options.get("tn_subdir")
        if tn_subdir:
            catalog_config["subdirs"]["tn"] = tn_subdir

        conn, created = Connection.objects.get_or_create(
            name=name,
            defaults={
                "type": "internal",
                "purpose": "catalog_source",
                "config": {"catalog_config": catalog_config},
                "is_active": True,
            },
        )

        if not created:
            # Update existing
            config = conn.config or {}
            config["catalog_config"] = catalog_config
            conn.config = config
            conn.save()
            self.stdout.write(f"  Updated connection: {name}")
        else:
            self.stdout.write(f"  Created connection: {name}")

        self.stdout.write(f"  Source path:  {source_path}")
        self.stdout.write(f"  Match by:     {image_config['match_by']}")
        self.stdout.write(f"  Pattern:      {image_config['filename_pattern']}")
        if tn_subdir:
            self.stdout.write(f"  TN subdir:    {tn_subdir}")

        self.stdout.write(self.style.SUCCESS(
            f"\nReady. Run: manage.py alice_process_images source --connection \"{name}\" --dry-run"
        ))
