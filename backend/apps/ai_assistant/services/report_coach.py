"""
Alice Report Coach — compares report definitions within each model to find
duplicates, articulate differences, and generate coaching descriptions.

Alice is not passive. When she finds reports that are indistinguishable,
she either:
  1. Identifies them as duplicates (deactivate one)
  2. Generates a distinguishing description based on their actual config
  3. Creates an Action forcing the user to review and clarify

This service is called by:
  - audit_report_quality management command (--coach flag)
  - Alice's nightly review (Celery beat)
  - On-demand via manage endpoint

Usage:
    from apps.ai_assistant.services.report_coach import ReportCoach
    coach = ReportCoach()
    findings = coach.analyze_model('proposal')
    coach.apply_coaching(findings)
"""
import json
import logging
from collections import defaultdict
from typing import Any

from apps.core.models import Report

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template key → human-readable description of what that template does
# ---------------------------------------------------------------------------

KNOWN_TEMPLATE_DESCRIPTIONS = {
    # Invoices
    'invoice': 'Standard invoice — Bill To, Ship To, line items with Qty/Unit/Extended, totals, comments',
    'invoice_standard': 'Standard invoice — single address, no shipping detail',
    'invoice_shipping': 'Shipping invoice — includes Ship From, Ship Via, tracking, packed by',
    'invoice_pp_ship': 'Prepaid shipping invoice — prepaid terms with shipping detail',
    'invoice_pp_standard': 'Prepaid standard invoice — prepaid terms, no shipping',
    'invoice_foreign': 'Foreign/international invoice — includes currency, customs info',
    'credit_memo': 'Credit memo — negative invoice for returns/adjustments',
    'net_invoice': 'Net invoice — shows net amounts after discounts applied',
    # Proposals
    'proposal': 'Basic proposal — customer info, line items, totals',
    'proposal_1': 'WC2 Proposal 1 — Accept/Use columns, Base/Disc%/Unit pricing, dual signature',
    'proposal_2': 'WC2 Proposal 2 — (description needed from WC2 form review)',
    'proposal_3': 'WC2 Proposal 3 — (description needed from WC2 form review)',
    'proposal_4': 'WC2 Proposal 4 — (description needed from WC2 form review)',
    'customer_quote': 'Customer-facing quote without internal pricing columns',
    'bid_document': 'Formal bid response — specifications, pricing, terms, acceptance block',
    'estimate': 'Estimate — budgetary only, not binding, no acceptance signature',
    'proposal_email': 'Email-formatted proposal — HTML body for sending to customer',
    # Orders
    'order': 'Standard order confirmation — Bill To, Ship To, line items, totals',
    'pick_list': 'Warehouse pick list — Bin location, Qty, Picked checkbox',
    'packing_slip': 'Packing slip — Ship To, Ordered/Shipped quantities, no prices',
    'bill_of_lading': 'Bill of Lading — carrier, weight, freight charges, legal terms',
    # Purchases
    'purchase_order': 'Purchase order to vendor — Ship To (our warehouse), cost pricing',
    # Statements
    'statement': 'Customer statement — aging buckets, open invoices, payment history',
    'past_due_notice': 'Past-due notice — overdue invoices with urgency message',
    # Other
    'commission_report': 'Commission report by rep — invoices, sales totals, effective rate',
    'customs_proforma': 'Customs proforma — HS codes, country of origin, declared values, weights',
}


class ReportCoach:
    """Analyze and coach on report definitions."""

    def analyze_model(self, model_name: str) -> list[dict]:
        """Analyze all reports for a model. Returns findings."""
        reports = list(
            Report.objects.filter(
                model_name=model_name,
                is_active=True,
                is_deleted=False,
            ).order_by('sort_order', 'name')
        )

        if not reports:
            return []

        findings = []

        # Group by output_type for comparison within each group
        by_output = defaultdict(list)
        for r in reports:
            by_output[r.output_type or 'print'].append(r)

        for output_type, group in by_output.items():
            if len(group) < 2:
                continue

            # Compare each pair
            for i, r1 in enumerate(group):
                for r2 in group[i + 1:]:
                    comparison = self._compare_reports(r1, r2)
                    if comparison:
                        findings.append(comparison)

        # Check for reports that need descriptions
        for r in reports:
            desc = (r.description or r.purpose or '').strip()
            suggestion = self._suggest_description(r)
            if suggestion and (not desc or len(desc) < 30):
                findings.append({
                    'type': 'NEEDS_DESCRIPTION',
                    'report_id': r.id,
                    'report_name': r.name,
                    'model_name': model_name,
                    'current_desc': desc,
                    'suggested_desc': suggestion,
                    'confidence': 'high' if r.config and r.config.get('template') else 'medium',
                })

        # ── Usage-based coaching ─────────────────────────────────────
        for r in reports:
            usage = self._get_usage(r)
            use_count = usage.get('use_count', 0)
            used_by = usage.get('used_by', [])
            last_used = usage.get('last_used_utc', '')

            # Never used — candidate for deactivation
            if use_count == 0 and r.output_type == 'print':
                findings.append({
                    'type': 'NEVER_USED',
                    'report_id': r.id,
                    'report_name': r.name,
                    'model_name': model_name,
                    'use_count': 0,
                    'detail': f'"{r.name}" has never been used. Review whether it should be deactivated or is a new template not yet adopted.',
                })

            # Used by only one person — may be too specialized
            elif len(used_by) == 1 and use_count >= 5:
                findings.append({
                    'type': 'SINGLE_USER_REPORT',
                    'report_id': r.id,
                    'report_name': r.name,
                    'model_name': model_name,
                    'use_count': use_count,
                    'user_count': 1,
                    'detail': f'"{r.name}" used {use_count} times but only by one user. May be a personal preference — consider if it should be the default or removed.',
                })

        # Check for usage-based duplicates: two reports with nearly identical use patterns
        print_reports = [r for r in reports if (r.output_type or 'print') == 'print']
        for i, r1 in enumerate(print_reports):
            u1 = self._get_usage(r1)
            for r2 in print_reports[i + 1:]:
                u2 = self._get_usage(r2)
                # If both have usage and the same users use both, they may be confused
                users1 = set(u1.get('used_by', []))
                users2 = set(u2.get('used_by', []))
                if users1 and users2 and users1 == users2:
                    c1 = u1.get('use_count', 0)
                    c2 = u2.get('use_count', 0)
                    if c1 > 0 and c2 > 0:
                        findings.append({
                            'type': 'SAME_USERS_BOTH_REPORTS',
                            'report_ids': [r1.id, r2.id],
                            'report_names': [r1.name, r2.name],
                            'model_name': model_name,
                            'use_counts': [c1, c2],
                            'detail': f'Same users run both "{r1.name}" ({c1}x) and "{r2.name}" ({c2}x) — they may not know the difference. Coach them or consolidate.',
                        })

        return findings

    @staticmethod
    def _get_usage(r: Report) -> dict:
        """Extract usage data from report metadata.flow."""
        meta = r.metadata or {}
        return meta.get('flow', {}) or {}

    def _compare_reports(self, r1: Report, r2: Report) -> dict | None:
        """Compare two reports and determine if identical, similar, or distinct."""
        cfg1 = r1.config or {}
        cfg2 = r2.config or {}

        # Same template key = likely identical
        tmpl1 = cfg1.get('template', '')
        tmpl2 = cfg2.get('template', '')

        # Same pdfme template JSON = definitely identical
        pdfme1 = cfg1.get('pdfme_template')
        pdfme2 = cfg2.get('pdfme_template')

        if pdfme1 and pdfme2 and json.dumps(pdfme1, sort_keys=True) == json.dumps(pdfme2, sort_keys=True):
            return {
                'type': 'IDENTICAL',
                'report_ids': [r1.id, r2.id],
                'report_names': [r1.name, r2.name],
                'model_name': r1.model_name,
                'reason': 'Same pdfme template JSON — these produce the same PDF',
                'recommendation': f'Deactivate one. Keep "{r1.name}" (#{r1.id}) or "{r2.name}" (#{r2.id})',
            }

        if tmpl1 and tmpl2 and tmpl1 == tmpl2:
            # Same template key — check if fields differ
            fields1 = set(str(f) for f in (cfg1.get('fields') or []))
            fields2 = set(str(f) for f in (cfg2.get('fields') or []))
            if fields1 == fields2:
                return {
                    'type': 'IDENTICAL',
                    'report_ids': [r1.id, r2.id],
                    'report_names': [r1.name, r2.name],
                    'model_name': r1.model_name,
                    'reason': f'Same template key "{tmpl1}" and same fields',
                    'recommendation': f'Deactivate one',
                }
            else:
                diff = fields1.symmetric_difference(fields2)
                return {
                    'type': 'SIMILAR',
                    'report_ids': [r1.id, r2.id],
                    'report_names': [r1.name, r2.name],
                    'model_name': r1.model_name,
                    'reason': f'Same template key "{tmpl1}" but different fields: {diff}',
                    'recommendation': f'Update descriptions to explain the field difference',
                }

        # Both have no config — check if names/descriptions are effectively the same
        if not cfg1 and not cfg2:
            desc1 = (r1.description or r1.purpose or '').strip().lower()
            desc2 = (r2.description or r2.purpose or '').strip().lower()
            name1 = (r1.name or '').strip().lower()
            name2 = (r2.name or '').strip().lower()

            # Very similar names with no config = probably duplicates
            if name1 == name2 or (desc1 and desc1 == desc2):
                return {
                    'type': 'LIKELY_DUPLICATE',
                    'report_ids': [r1.id, r2.id],
                    'report_names': [r1.name, r2.name],
                    'model_name': r1.model_name,
                    'reason': 'Same name or description, no config on either — likely duplicates from WC2 migration',
                    'recommendation': 'Review both. If identical, deactivate one. If different, add config and distinct descriptions.',
                }

        # Different templates = distinct — but do descriptions explain the difference?
        if tmpl1 != tmpl2 and tmpl1 and tmpl2:
            desc1 = (r1.description or r1.purpose or '').strip()
            desc2 = (r2.description or r2.purpose or '').strip()
            if not desc1 or not desc2 or len(desc1) < 30 or len(desc2) < 30:
                known1 = KNOWN_TEMPLATE_DESCRIPTIONS.get(tmpl1, '')
                known2 = KNOWN_TEMPLATE_DESCRIPTIONS.get(tmpl2, '')
                return {
                    'type': 'DISTINCT_BUT_UNDESCRIBED',
                    'report_ids': [r1.id, r2.id],
                    'report_names': [r1.name, r2.name],
                    'model_name': r1.model_name,
                    'reason': f'Different templates ("{tmpl1}" vs "{tmpl2}") but descriptions don\'t explain the difference',
                    'recommendation': f'Add descriptions. Suggested: "{r1.name}": "{known1}". "{r2.name}": "{known2}".',
                }

        return None

    def _suggest_description(self, r: Report) -> str | None:
        """Suggest a description based on the report's config."""
        cfg = r.config or {}
        tmpl_key = cfg.get('template', '')

        # Known template → known description
        if tmpl_key and tmpl_key in KNOWN_TEMPLATE_DESCRIPTIONS:
            return KNOWN_TEMPLATE_DESCRIPTIONS[tmpl_key]

        # Output type hints
        output = r.output_type or 'print'
        name = (r.name or '').lower()
        cat = (r.category or '').lower()

        if output == 'email':
            return f'Email {r.model_name or "document"} to recipient — sends formatted HTML email'
        if output == 'export':
            return f'Export {r.model_name or "records"} to CSV/spreadsheet for external analysis'
        if output == 'json':
            return f'Return {r.model_name or "record"} data as structured JSON for API integration'
        if output == 'api':
            return f'POST {r.model_name or "record"} data to external system endpoint'
        if output == 'merge':
            return f'Merge {r.model_name or "record"} data into Word/document template'
        if cat == 'label':
            return f'Print labels for {r.model_name or "records"} — shipping or identification labels'
        if cat == 'summary':
            return f'Summary view of {r.model_name or "records"} — aggregated totals and counts'
        if 'checklist' in name:
            return f'Preparation checklist for {r.model_name or "record"} — steps to verify before finalizing'

        # Has pdfme template → describe from schema
        if cfg.get('pdfme_template'):
            schemas = cfg['pdfme_template'].get('schemas', [[]])
            field_names = [s.get('name', '') for s in (schemas[0] if schemas else []) if s.get('name')]
            if field_names:
                return f'Custom PDF template with fields: {", ".join(field_names[:8])}'

        # Has fields list → describe from fields
        if cfg.get('fields'):
            fields = cfg['fields']
            return f'Print form showing: {", ".join(str(f) for f in fields[:6])}'

        return None

    def apply_coaching(self, findings: list[dict], dry_run: bool = False) -> dict:
        """Apply coaching — update descriptions, deactivate duplicates.

        Returns summary of actions taken.
        """
        applied = {'descriptions_updated': 0, 'duplicates_deactivated': 0, 'skipped': 0}

        for finding in findings:
            ftype = finding['type']

            if ftype == 'NEEDS_DESCRIPTION' and finding.get('suggested_desc'):
                if not dry_run:
                    report = Report.objects.filter(id=finding['report_id']).first()
                    if report:
                        report.description = finding['suggested_desc']
                        report.save(update_fields=['description', 'dt_modified', 'version'])
                        logger.info(
                            "Alice coached report #%d (%s): set description to '%s'",
                            report.id, report.name, finding['suggested_desc'][:60]
                        )
                applied['descriptions_updated'] += 1

            elif ftype == 'IDENTICAL' and finding.get('report_ids'):
                # Deactivate the second one
                keep_id = finding['report_ids'][0]
                deactivate_id = finding['report_ids'][1]
                if not dry_run:
                    Report.objects.filter(id=deactivate_id).update(is_active=False)
                    logger.info(
                        "Alice deactivated duplicate report #%d (kept #%d)",
                        deactivate_id, keep_id
                    )
                applied['duplicates_deactivated'] += 1

            else:
                applied['skipped'] += 1

        return applied
