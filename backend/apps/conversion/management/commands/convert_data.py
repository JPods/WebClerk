"""
Management command — Alice's data conversion pipeline.

Usage:
  # Start a new conversion (Pass 1: Claude maps columns)
  python manage.py convert_data start "Acme Items" /path/to/items.csv --supplier "Acme Corp"

  # Review proposed mappings
  python manage.py convert_data review <project_id>

  # Confirm all high-confidence mappings (>= 0.8)
  python manage.py convert_data confirm <project_id> --auto

  # Run conversion pass (apply confirmed maps, convert rows, find oddities)
  python manage.py convert_data run <project_id>

  # Show oddities
  python manage.py convert_data oddities <project_id>

  # Assemble bundle JSON
  python manage.py convert_data bundle <project_id> --output /path/to/bundle.json

  # List projects
  python manage.py convert_data list
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.conversion.models import (
    ConversionProject,
    ColumnMap,
    Oddity,
    StagingRow,
)
from apps.conversion.services.converter import (
    start_conversion,
    run_conversion_pass,
    assemble_bundle,
)


class Command(BaseCommand):
    help = "Alice's data conversion pipeline — convert supplier files to WC3 bundles"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action')

        start = sub.add_parser('start', help='Start a new conversion project')
        start.add_argument('name', help='Project name')
        start.add_argument('file', help='Path to source file')
        start.add_argument('--supplier', default='', help='Supplier name')

        review = sub.add_parser('review', help='Review column mappings')
        review.add_argument('project_id', type=int)

        confirm = sub.add_parser('confirm', help='Confirm column mappings')
        confirm.add_argument('project_id', type=int)
        confirm.add_argument('--auto', action='store_true', help='Auto-confirm high confidence (>= 0.8)')
        confirm.add_argument('--all', action='store_true', help='Confirm all proposed mappings')

        run = sub.add_parser('run', help='Run conversion pass')
        run.add_argument('project_id', type=int)

        oddities = sub.add_parser('oddities', help='Show oddities')
        oddities.add_argument('project_id', type=int)
        oddities.add_argument('--severity', default='', help='Filter by severity')

        bundle = sub.add_parser('bundle', help='Assemble bundle JSON')
        bundle.add_argument('project_id', type=int)
        bundle.add_argument('--output', default='', help='Output file path')

        sub.add_parser('list', help='List conversion projects')

    def handle(self, *args, **options):
        action = options.get('action')
        if not action:
            self.stderr.write("Usage: convert_data {start|review|confirm|run|oddities|bundle|list}")
            return

        handler = getattr(self, f'_handle_{action}', None)
        if handler:
            handler(options)
        else:
            self.stderr.write(f"Unknown action: {action}")

    def _handle_start(self, options):
        project = start_conversion(
            project_name=options['name'],
            file_path=options['file'],
            supplier_name=options.get('supplier', ''),
        )
        self.stdout.write(self.style.SUCCESS(
            f"Project {project.id}: '{project.name}' created. "
            f"{project.stats.get('columns_mapped', 0)} columns mapped, "
            f"{project.stats.get('columns_unmapped', 0)} unmapped. "
            f"Run 'convert_data review {project.id}' to see mappings."
        ))

    def _handle_review(self, options):
        project = ConversionProject.objects.get(id=options['project_id'])
        maps = ColumnMap.objects.filter(source_file__project=project).order_by('-confidence')

        self.stdout.write(f"\n  Project: {project.name}")
        self.stdout.write(f"  Status:  {project.status}")
        self.stdout.write(f"  Passes:  {project.pass_count}\n")

        for cm in maps:
            conf_bar = '*' * int(cm.confidence * 10)
            status_color = {
                'proposed': self.style.WARNING,
                'confirmed': self.style.SUCCESS,
                'rejected': self.style.ERROR,
                'unmapped': self.style.NOTICE,
            }.get(cm.status, str)

            self.stdout.write(
                f"  [{status_color(cm.status):>10}] "
                f"{cm.source_column:<30} -> {cm.target_model}.{cm.target_field:<25} "
                f"[{conf_bar:<10}] {cm.confidence:.1f}"
            )
            if cm.reasoning:
                self.stdout.write(f"             {cm.reasoning}")
            if cm.sample_values:
                self.stdout.write(f"             samples: {cm.sample_values[:3]}")
            self.stdout.write("")

    def _handle_confirm(self, options):
        project = ConversionProject.objects.get(id=options['project_id'])
        maps = ColumnMap.objects.filter(source_file__project=project, status='proposed')

        if options.get('all'):
            count = maps.update(status='confirmed')
        elif options.get('auto'):
            count = maps.filter(confidence__gte=0.8).update(status='confirmed')
        else:
            self.stderr.write("Specify --auto (>= 0.8 confidence) or --all")
            return

        self.stdout.write(self.style.SUCCESS(f"Confirmed {count} column mappings."))

    def _handle_run(self, options):
        project = ConversionProject.objects.get(id=options['project_id'])
        pass_log = run_conversion_pass(project)

        self.stdout.write(self.style.SUCCESS(
            f"Pass {pass_log.pass_number} complete. "
            f"Staged: {pass_log.rows_staged}, Rejected: {pass_log.rows_rejected}, "
            f"Oddities: {pass_log.oddities_found}. "
            f"Claude calls: {pass_log.llm_calls}, tokens: {pass_log.llm_input_tokens + pass_log.llm_output_tokens}"
        ))

    def _handle_oddities(self, options):
        project = ConversionProject.objects.get(id=options['project_id'])
        qs = Oddity.objects.filter(project=project).order_by('-severity', 'category')

        severity_filter = options.get('severity', '')
        if severity_filter:
            qs = qs.filter(severity=severity_filter)

        self.stdout.write(f"\n  Oddities for: {project.name}\n")

        # Summary by category
        categories = {}
        for o in qs:
            key = f"{o.severity}:{o.category}"
            categories[key] = categories.get(key, 0) + 1

        for key, count in sorted(categories.items()):
            self.stdout.write(f"  {key}: {count}")

        self.stdout.write(f"\n  Total: {qs.count()}\n")

        # Show first 20 detail
        for o in qs[:20]:
            self.stdout.write(
                f"  [{o.severity}] {o.category}: {o.description[:100]}"
            )
            if o.source_value:
                self.stdout.write(f"           value: {o.source_value[:60]}")
            if o.source_row:
                self.stdout.write(f"           row: {o.source_row}, column: {o.source_column}")
            self.stdout.write("")

    def _handle_bundle(self, options):
        project = ConversionProject.objects.get(id=options['project_id'])
        payload = assemble_bundle(project)

        staged_count = StagingRow.objects.filter(
            source_file__project=project, status='staged').count()
        review_count = StagingRow.objects.filter(
            source_file__project=project, status='needs_review').count()

        if review_count > 0:
            self.stdout.write(self.style.WARNING(
                f"{review_count} rows still need review. Bundle contains only staged rows."
            ))

        output_path = options.get('output', '')
        if output_path:
            path = Path(output_path)
            path.write_text(json.dumps(payload, indent=2, default=str))
            self.stdout.write(self.style.SUCCESS(
                f"Bundle written to {path} ({staged_count} records)"
            ))
        else:
            self.stdout.write(json.dumps(payload, indent=2, default=str))

    def _handle_list(self, options):
        projects = ConversionProject.objects.all().order_by('-dt_created')
        if not projects:
            self.stdout.write("No conversion projects.")
            return

        self.stdout.write(f"\n{'ID':>5}  {'Status':<10}  {'Passes':>6}  {'Supplier':<20}  {'Name'}")
        self.stdout.write(f"{'--':>5}  {'------':<10}  {'------':>6}  {'--------':<20}  {'----'}")
        for p in projects:
            self.stdout.write(
                f"{p.id:>5}  {p.status:<10}  {p.pass_count:>6}  {p.supplier_name:<20}  {p.name}"
            )
