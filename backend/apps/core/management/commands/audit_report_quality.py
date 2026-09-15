"""Audit report definitions for quality — Alice's enforcement tool.

Alice is not passive. When report records lack distinguishing information,
she creates Action records to force the user to review and improve them.

Checks:
  1. Missing or vague descriptions (< 30 chars)
  2. Duplicate names within the same model_name
  3. Generic numbered names ("Proposal 1", "Invoice 2") with no distinction
  4. Missing model_name (orphan reports)
  5. Duplicate entries (same name + same model_name)

Usage:
    python manage.py audit_report_quality              # audit and report
    python manage.py audit_report_quality --fix         # auto-fix what can be fixed
    python manage.py audit_report_quality --actions     # create Alice Actions for issues
"""
from collections import Counter
from django.core.management.base import BaseCommand
from apps.core.models import Report


# Descriptions that don't distinguish a report from its siblings
VAGUE_PATTERNS = [
    'format 1', 'format 2', 'format 3', 'format 4', 'format 5',
    'standard invoice', 'standard proposal', 'standard order',
    'print proposal', 'print invoice', 'print order',
]

MIN_USEFUL_DESC_LEN = 30


class Command(BaseCommand):
    help = "Audit report definitions for quality and completeness"

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true',
                            help='Auto-fix what can be fixed (deactivate exact duplicates)')
        parser.add_argument('--actions', action='store_true',
                            help='Create Alice Action records for issues requiring human review')
        parser.add_argument('--coach', action='store_true',
                            help='Alice compares forms, finds duplicates, generates descriptions')
        parser.add_argument('--model', type=str, default=None,
                            help='Audit only this model_name (e.g. proposal)')

    def handle(self, *args, **options):
        do_fix = options['fix']
        do_actions = options['actions']
        model_filter = options.get('model')

        reports = Report.objects.filter(is_active=True, is_deleted=False)
        if model_filter:
            reports = reports.filter(model_name=model_filter)
        reports = reports.order_by('model_name', 'name')

        issues = []

        # ── Check 1: Missing or vague descriptions ──────────────────────
        for r in reports:
            desc = (r.description or r.purpose or '').strip()
            if not desc:
                issues.append({
                    'report_id': r.id,
                    'name': r.name,
                    'model_name': r.model_name,
                    'issue': 'NO_DESCRIPTION',
                    'detail': 'Report has no description — user cannot distinguish it from others',
                    'severity': 'high',
                })
            elif len(desc) < MIN_USEFUL_DESC_LEN:
                is_vague = any(p in desc.lower() for p in VAGUE_PATTERNS)
                if is_vague:
                    issues.append({
                        'report_id': r.id,
                        'name': r.name,
                        'model_name': r.model_name,
                        'issue': 'VAGUE_DESCRIPTION',
                        'detail': f'Description "{desc}" does not distinguish this report from its siblings',
                        'severity': 'medium',
                    })

        # ── Check 2: Duplicate names within same model ──────────────────
        name_groups = {}
        for r in reports:
            key = (r.model_name or '', r.name or '')
            if key not in name_groups:
                name_groups[key] = []
            name_groups[key].append(r)

        for (model, name), group in name_groups.items():
            if len(group) > 1:
                ids = [r.id for r in group]
                issues.append({
                    'report_id': ids[0],
                    'name': name,
                    'model_name': model,
                    'issue': 'DUPLICATE_NAME',
                    'detail': f'"{name}" appears {len(group)} times for model "{model}" (ids: {ids})',
                    'severity': 'high',
                    'duplicate_ids': ids,
                })

        # ── Check 3: Generic numbered names ─────────────────────────────
        for r in reports:
            name = (r.name or '').strip()
            # Pattern: "Word N" where N is a single digit
            parts = name.rsplit(' ', 1)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 1:
                desc = (r.description or r.purpose or '').strip()
                if not desc or len(desc) < MIN_USEFUL_DESC_LEN:
                    issues.append({
                        'report_id': r.id,
                        'name': r.name,
                        'model_name': r.model_name,
                        'issue': 'GENERIC_NUMBERED_NAME',
                        'detail': f'"{name}" is a WC2 legacy name — rename to describe what makes this format different',
                        'severity': 'medium',
                    })

        # ── Check 4: Missing model_name ─────────────────────────────────
        for r in reports:
            if not r.model_name:
                issues.append({
                    'report_id': r.id,
                    'name': r.name,
                    'model_name': None,
                    'issue': 'NO_MODEL_NAME',
                    'detail': f'Report "{r.name}" has no model_name — will not appear in any model\'s report list',
                    'severity': 'high',
                })

        # ── Coach: Alice compares forms and generates descriptions ──────
        do_coach = options['coach']
        if do_coach:
            from apps.ai_assistant.services.report_coach import ReportCoach
            coach = ReportCoach()

            # Get unique model_names
            model_names = set(r.model_name for r in reports if r.model_name)
            all_findings = []

            for mn in sorted(model_names):
                findings = coach.analyze_model(mn)
                all_findings.extend(findings)

            if all_findings:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Alice Coach — {len(all_findings)} findings\n")

                for f in all_findings:
                    ftype = f['type']
                    if ftype == 'IDENTICAL':
                        self.stdout.write(self.style.ERROR(
                            f"  🔴 IDENTICAL: {f['report_names']} (#{f['report_ids']}) — {f['reason']}"
                        ))
                    elif ftype == 'LIKELY_DUPLICATE':
                        self.stdout.write(self.style.WARNING(
                            f"  🟠 LIKELY DUPLICATE: {f['report_names']} — {f['reason']}"
                        ))
                    elif ftype == 'SIMILAR':
                        self.stdout.write(self.style.WARNING(
                            f"  🟠 SIMILAR: {f['report_names']} — {f['reason']}"
                        ))
                    elif ftype == 'DISTINCT_BUT_UNDESCRIBED':
                        self.stdout.write(
                            f"  🟡 UNDESCRIBED: {f['report_names']} — {f['reason']}"
                        )
                    elif ftype == 'NEEDS_DESCRIPTION':
                        conf = f.get('confidence', '?')
                        self.stdout.write(
                            f"  📝 SUGGEST [{conf}] #{f['report_id']} \"{f['report_name']}\":"
                        )
                        self.stdout.write(
                            f"     current:   \"{f['current_desc']}\""
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"     suggested: \"{f['suggested_desc']}\""
                        ))
                    elif ftype == 'NEVER_USED':
                        self.stdout.write(self.style.WARNING(
                            f"  ⚪ NEVER USED: #{f['report_id']} \"{f['report_name']}\" — {f['detail']}"
                        ))
                    elif ftype == 'SINGLE_USER_REPORT':
                        self.stdout.write(
                            f"  👤 SINGLE USER: #{f['report_id']} \"{f['report_name']}\" "
                            f"({f['use_count']}x by 1 user) — {f['detail']}"
                        )
                    elif ftype == 'SAME_USERS_BOTH_REPORTS':
                        self.stdout.write(self.style.WARNING(
                            f"  🔄 SAME USERS: {f['report_names']} (used {f['use_counts']}x) — {f['detail']}"
                        ))

                # Apply coaching (update descriptions, deactivate identical)
                if do_fix:
                    results = coach.apply_coaching(all_findings)
                    self.stdout.write(self.style.SUCCESS(
                        f"\nCoaching applied:"
                        f"\n  Descriptions updated: {results['descriptions_updated']}"
                        f"\n  Duplicates deactivated: {results['duplicates_deactivated']}"
                        f"\n  Skipped (needs human): {results['skipped']}"
                    ))
                else:
                    self.stdout.write(
                        f"\nRun with --fix to apply coaching (update descriptions, deactivate identical)"
                    )
            else:
                self.stdout.write(self.style.SUCCESS("\nAlice Coach: All reports are well-described."))

        # ── Report results ──────────────────────────────────────────────
        self.stdout.write(f"\nAudited {reports.count()} report records")
        self.stdout.write(f"Found {len(issues)} issues\n")

        # Group by severity
        by_severity = Counter(i['severity'] for i in issues)
        for sev in ['high', 'medium', 'low']:
            count = by_severity.get(sev, 0)
            if count:
                self.stdout.write(f"  {sev}: {count}")

        # Group by issue type
        by_type = Counter(i['issue'] for i in issues)
        self.stdout.write("")
        for issue_type, count in by_type.most_common():
            self.stdout.write(f"  {issue_type}: {count}")

        self.stdout.write("")
        for issue in issues:
            severity_icon = {'high': '🔴', 'medium': '🟠', 'low': '🟡'}.get(issue['severity'], '⚪')
            self.stdout.write(
                f"  {severity_icon} [{issue['issue']}] {issue['model_name']}/{issue['name']} "
                f"(#{issue['report_id']}): {issue['detail']}"
            )

        # ── Auto-fix duplicates ─────────────────────────────────────────
        if do_fix:
            fixed = 0
            for issue in issues:
                if issue['issue'] == 'DUPLICATE_NAME' and 'duplicate_ids' in issue:
                    # Keep the first, deactivate the rest
                    dup_ids = issue['duplicate_ids'][1:]  # skip first
                    Report.objects.filter(id__in=dup_ids).update(is_active=False)
                    fixed += len(dup_ids)
                    self.stdout.write(self.style.SUCCESS(
                        f"  Deactivated duplicates: {dup_ids} (kept #{issue['duplicate_ids'][0]})"
                    ))
            if fixed:
                self.stdout.write(self.style.SUCCESS(f"\nFixed {fixed} duplicate(s)"))

        # ── Create Alice Actions ────────────────────────────────────────
        if do_actions and issues:
            try:
                from apps.core.models import Action
            except ImportError:
                self.stdout.write(self.style.WARNING("Action model not available — skipping"))
                return

            # Group issues by model_name for one Action per model
            by_model = {}
            for issue in issues:
                model = issue['model_name'] or 'system'
                if model not in by_model:
                    by_model[model] = []
                by_model[model].append(issue)

            created = 0
            for model, model_issues in by_model.items():
                # Check if an open Action already exists
                existing = Action.objects.filter(
                    ida__startswith=f'ALICE-REPORT-AUDIT-{model}',
                    status__in=['planned', 'in_progress'],
                    is_active=True,
                    is_deleted=False,
                ).first()

                if existing:
                    self.stdout.write(f"  Action already exists for {model}: #{existing.id}")
                    continue

                issue_lines = []
                for issue in model_issues:
                    icon = {'high': '🔴', 'medium': '🟠', 'low': '🟡'}.get(issue['severity'], '⚪')
                    issue_lines.append(
                        f"{icon} [{issue['issue']}] \"{issue['name']}\" (#{issue['report_id']}): {issue['detail']}"
                    )

                desc = (
                    f"Alice report audit found {len(model_issues)} issue(s) in {model} reports.\n\n"
                    f"Each report must have a description that helps the user choose between them. "
                    f"Vague names like 'Proposal 2' or duplicate entries waste the user's time.\n\n"
                    f"Issues:\n" + "\n".join(issue_lines) + "\n\n"
                    f"For each issue:\n"
                    f"- VAGUE: Open the report record and write a description that explains "
                    f"WHAT MAKES THIS FORMAT DIFFERENT from the others.\n"
                    f"- DUPLICATE: Decide which to keep, deactivate the other.\n"
                    f"- NO_MODEL_NAME: Assign the correct model_name so it appears in the right list.\n"
                    f"- GENERIC_NUMBERED: Rename from 'Proposal 2' to something like "
                    f"'Proposal - Wholesale with Discount Grid'."
                )

                action = Action(
                    ida=f'ALICE-REPORT-AUDIT-{model.upper()}-{len(model_issues)}',
                    task={'en': f'Fix {len(model_issues)} report description(s) for {model}'},
                    description={'en': desc},
                    status='planned',
                    priority=2,  # 1=low, 2=medium, 3=high, 4=urgent
                    kanban_column='todo',
                    refs={
                        'keywords': {
                            'type': 'alice_audit',
                            'audit': 'report_quality',
                            'model_name': model,
                        },
                        'alice': {
                            'source': 'alice_audit',
                            'audit_type': 'report_quality',
                            'issue_count': len(model_issues),
                        }
                    },
                )
                action.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  Created Action #{action.id}: {action.ida}"
                ))

            self.stdout.write(self.style.SUCCESS(f"\nCreated {created} Alice Action(s)"))
