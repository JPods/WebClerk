"""
seed_dbsr_document — Generate a consolidated Document from all DBSR explanations.

Queries every Setting and Report that has metadata.explanation populated,
groups by purpose/category, and writes a single Document record as a
readable index of all database supporting records.

Also creates/updates a database_health Setting that lists all required DBSRs.
Any missing or expired records are flagged.

Usage:
    python manage.py seed_dbsr_document
    python manage.py seed_dbsr_document --force   # overwrite existing
"""
import json
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models.setting import Setting
from apps.core.models.report import Report
from apps.docs.models.document import Document


DOCUMENT_IDA = 'WC3-DBSR-INDEX'
HEALTH_IDA = 'database-health'
HEALTH_LOCAL_IDA = 'database-health-local'

# Every WC3 installation requires these purpose categories to be populated.
# Each entry: (purpose, min_count, description)
REQUIRED_PURPOSES = [
    ('wc:field_access', 30, 'RBAC field filters per model'),
    ('wc:workbench_fields', 30, 'DataBrowser layouts per model'),
    ('wc:schema_map', 30, 'Pydantic schema definitions per model'),
    ('wc:search', 5, 'Saved search presets'),
    ('wc:detail_layout', 10, 'App-level detail view layouts'),
    ('wc:db_defaults', 5, 'Default values for new records'),
    ('wc:selectlist', 5, 'Dropdown/select list definitions'),
    ('wc:coaching', 5, 'AI assistant coaching rules'),
    ('wc:print_layout', 3, 'Print template layouts'),
    ('wc:company_profile', 1, 'Company identity and settings'),
    ('wc:feature', 1, 'Feature flags'),
]


def build_markdown_body():
    """Query all explained DBSRs and build a markdown document."""
    lines = [
        '# WebClerk Database Supporting Records (DBSR) Index',
        '',
        'This document is auto-generated from `metadata.explanation` on each record.',
        'Edit explanations on the source record; re-run `seed_dbsr_document` to refresh.',
        '',
        f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M UTC")}',
        '',
    ]

    # ── Settings by purpose ──
    lines.append('## Settings')
    lines.append('')

    settings = (Setting.objects
                .exclude(metadata={})
                .order_by('purpose', 'parent_model', 'name'))

    current_purpose = None
    for s in settings:
        meta = s.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta.replace("'", '"'))
            except (json.JSONDecodeError, ValueError):
                continue
        explanation = meta.get('explanation', '')
        if not explanation:
            continue

        if s.purpose != current_purpose:
            current_purpose = s.purpose
            lines.append(f'### {current_purpose}')
            lines.append('')

        model_label = s.parent_model or 'system'
        name_label = s.name or s.ida
        lines.append(f'**{name_label}** ({model_label})')
        lines.append(f': {explanation}')
        lines.append('')

    # ── Reports by category ──
    lines.append('## Reports')
    lines.append('')

    reports = Report.objects.all().order_by('category', 'name')

    current_category = None
    for r in reports:
        meta = r.metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta.replace("'", '"'))
            except (json.JSONDecodeError, ValueError):
                continue
        explanation = meta.get('explanation', '')
        if not explanation:
            continue

        if r.category != current_category:
            current_category = r.category
            lines.append(f'### {current_category}')
            lines.append('')

        lines.append(f'**{r.name}**')
        lines.append(f': {explanation}')
        lines.append('')

    return '\n'.join(lines)


def build_health_manifest():
    """Check required DBSRs and build health data."""
    # dt_modified is epoch ms (BigIntegerField), not datetime
    stale_threshold_ms = int((time.time() - 90 * 86400) * 1000)
    issues = []
    manifest = []

    for purpose, min_count, description in REQUIRED_PURPOSES:
        qs = Setting.objects.filter(purpose=purpose)
        count = qs.count()
        explained = qs.exclude(metadata={}).count()

        entry = {
            'purpose': purpose,
            'description': description,
            'required_min': min_count,
            'actual_count': count,
            'explained_count': explained,
            'status': 'ok',
        }

        if count < min_count:
            entry['status'] = 'missing'
            issues.append(f'{purpose}: {count}/{min_count} records (need {min_count - count} more)')
        elif explained < count:
            entry['status'] = 'incomplete'
            issues.append(f'{purpose}: {count - explained}/{count} records lack explanations')

        # Check for stale records (not modified in 90 days)
        stale = qs.filter(dt_modified__lt=stale_threshold_ms).count()
        if stale > 0:
            entry['stale_count'] = stale
            if entry['status'] == 'ok':
                entry['status'] = 'stale'
            issues.append(f'{purpose}: {stale} records not updated in 90+ days')

        manifest.append(entry)

    # Check reports too
    report_count = Report.objects.count()
    report_entry = {
        'purpose': 'reports',
        'description': 'Report templates',
        'required_min': 10,
        'actual_count': report_count,
        'status': 'ok' if report_count >= 10 else 'missing',
    }
    manifest.append(report_entry)

    return manifest, issues


class Command(BaseCommand):
    help = 'Generate consolidated DBSR index document and health manifest'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing document and health setting')

    def handle(self, *args, **options):
        force = options['force']

        self.stdout.write(self.style.MIGRATE_HEADING(
            'seed_dbsr_document — generating consolidated index'))

        # ── Build and save the Document ──
        body = build_markdown_body()
        doc, created = Document.objects.update_or_create(
            ida=DOCUMENT_IDA,
            defaults={
                'name': 'DBSR Index — Database Supporting Records',
                'description': 'Auto-generated index of all Settings and Reports with explanations',
                'status': 'published',
                'mime_type': 'text/markdown',
                'body': body,
                'size_bytes': len(body.encode('utf-8')),
                'config': {
                    'doc_system': 'dbsr',
                    'auto_generated': True,
                    'source_command': 'seed_dbsr_document',
                },
            },
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'  {action} Document: {DOCUMENT_IDA} ({len(body)} chars)')

        # ── Build and save the health manifest ──
        manifest, issues = build_health_manifest()

        health_setting, h_created = Setting.objects.update_or_create(
            ida=HEALTH_IDA,
            defaults={
                'name': 'Database Health Manifest',
                'purpose': 'wc:database_health',
                'config': {
                    'manifest': manifest,
                    'issues': issues,
                    'last_check': timezone.now().isoformat(),
                },
                'metadata': {
                    'explanation': (
                        'Health manifest listing all required database supporting records. '
                        'Each entry specifies the minimum count of records needed for that '
                        'purpose category. Issues list missing, incomplete, or stale records. '
                        'Alice checks this periodically and flags gaps.'
                    ),
                },
            },
        )
        h_action = 'Created' if h_created else 'Updated'
        self.stdout.write(f'  {h_action} Setting: {HEALTH_IDA}')

        if issues:
            self.stdout.write(self.style.WARNING(f'\n  {len(issues)} health issues found:'))
            for issue in issues:
                self.stdout.write(f'    - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('  No health issues — all DBSRs present'))

        # ── Create local health manifest (user-managed) ──
        _, l_created = Setting.objects.get_or_create(
            ida=HEALTH_LOCAL_IDA,
            defaults={
                'name': 'Database Health Manifest (Local)',
                'purpose': 'wc:database_health',
                'config': {
                    'manifest': [],
                    'issues': [],
                    'last_check': timezone.now().isoformat(),
                },
                'metadata': {
                    'explanation': (
                        'Local health manifest for installation-specific DBSRs. '
                        'Users add custom required records here — industry-specific '
                        'reports, custom select lists, extra coaching rules. '
                        'Never synced to WC_HQ. The primary database-health record '
                        'is WC_HQ-managed and synced by uuid; this one is yours.'
                    ),
                },
            },
        )
        if l_created:
            self.stdout.write(f'  Created Setting: {HEALTH_LOCAL_IDA}')
        else:
            self.stdout.write(f'  Setting {HEALTH_LOCAL_IDA} already exists (user-managed, not overwritten)')

        self.stdout.write(self.style.SUCCESS('\nseed_dbsr_document complete'))
