"""
Management command: ai_intelligence — Run Phase 5 Autonomous Data Intelligence tasks.

Usage:
    python manage.py ai_intelligence                     # Run all tasks (dry run)
    python manage.py ai_intelligence --task health       # Just health scoring
    python manage.py ai_intelligence --task drift        # Just schema drift
    python manage.py ai_intelligence --task cleanup      # Just data cleanup
    python manage.py ai_intelligence --task optimize     # Just JSON optimization
    python manage.py ai_intelligence --task margins      # Just margin tracking
    python manage.py ai_intelligence --task velocity     # Just inventory velocity
    python manage.py ai_intelligence --task layout        # Just layout drift
    python manage.py ai_intelligence --task layout --report-file  # Save full report
    python manage.py ai_intelligence --task layout --dismiss contact:cnf_password:phantom_field --reason 'UI-only'
    python manage.py ai_intelligence --task layout --undismiss contact:cnf_password:phantom_field
    python manage.py ai_intelligence --task layout --history  # View correction history
    python manage.py ai_intelligence --llm               # Enable Ollama analysis
    python manage.py ai_intelligence --apply             # Apply changes (not dry run)
    python manage.py ai_intelligence --limit 1000        # Process more records
    python manage.py ai_intelligence --report            # Generate markdown report
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


TASK_CHOICES = ["all", "health", "drift", "cleanup", "optimize", "margins", "velocity", "layout"]


class Command(BaseCommand):
    help = "Run Phase 5 AI Intelligence tasks (health scoring, schema drift, data cleanup, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--task",
            type=str,
            default="all",
            choices=TASK_CHOICES,
            help="Which task to run (default: all)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max records to process per model (default: 500)",
        )
        parser.add_argument(
            "--llm",
            action="store_true",
            help="Enable Ollama LLM for enhanced analysis",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (JSON compaction, address cleaning). Without this flag, runs in dry-run/report mode.",
        )
        parser.add_argument(
            "--report",
            action="store_true",
            help="Generate and print a markdown report",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="",
            help="Limit to a specific model (e.g., 'contact', 'item')",
        )
        # Layout-specific options
        parser.add_argument(
            "--report-file",
            action="store_true",
            help="(layout) Save full report to readmes/topics/ai/layout-drift-report.md",
        )
        parser.add_argument(
            "--dismiss",
            type=str,
            default="",
            help="(layout) Dismiss an issue: model:field:type (e.g., contact:cnf_password:phantom_field)",
        )
        parser.add_argument(
            "--undismiss",
            type=str,
            default="",
            help="(layout) Undo a dismissal: model:field:type",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="",
            help="(layout) Reason for dismissal (used for LLM learning)",
        )
        parser.add_argument(
            "--history",
            action="store_true",
            help="(layout) Show correction history and trend",
        )

    def handle(self, *args, **options):
        task = options["task"]
        limit = options["limit"]
        use_llm = options["llm"]
        apply = options["apply"]
        report = options["report"]
        model = options.get("model", "")
        report_file = options.get("report_file", False)
        dismiss = options.get("dismiss", "")
        undismiss = options.get("undismiss", "")
        reason = options.get("reason", "")
        history = options.get("history", False)

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  AI Intelligence — Phase 5\n"
            f"  Task: {task} | Limit: {limit} | LLM: {use_llm} | Apply: {apply}\n"
            f"  {timezone.now():%Y-%m-%d %H:%M:%S}\n"
            f"{'='*60}\n"
        ))

        results = {}

        if task in ("all", "health"):
            results["health"] = self._run_health(limit, use_llm, model, report)

        if task in ("all", "drift"):
            results["drift"] = self._run_drift(use_llm, model, report)

        if task in ("all", "cleanup"):
            results["cleanup"] = self._run_cleanup(limit, use_llm, report)

        if task in ("all", "optimize"):
            results["optimize"] = self._run_optimize(limit, apply, report)

        if task in ("all", "margins"):
            results["margins"] = self._run_margins(limit, use_llm, report)

        if task in ("all", "velocity"):
            results["velocity"] = self._run_velocity(limit, use_llm, report)

        if task in ("all", "layout"):
            results["layout"] = self._run_layout(
                use_llm, model, report,
                report_file=report_file,
                dismiss=dismiss,
                undismiss=undismiss,
                reason=reason,
                history=history,
            )

        self.stdout.write(self.style.SUCCESS("\nAll tasks complete."))

    # ── Task runners ──────────────────────────────────────────────────

    def _run_health(self, limit, use_llm, model, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5E: Health Scoring"))

        from apps.ai_assistant.services.health_scorer import HealthScorer
        scorer = HealthScorer(use_llm=use_llm)

        if model:
            result = scorer.score_model(model, limit=limit)
            result = {"models_scored": 1, "total_processed": result.get("processed", 0),
                       "total_updated": result.get("updated", 0), "per_model": {model: result}}
        else:
            result = scorer.score_all(limit=limit)

        self.stdout.write(
            f"  Models: {result.get('models_scored', 0)} | "
            f"Records: {result.get('total_processed', 0)} | "
            f"Updated: {result.get('total_updated', 0)}"
        )

        if report:
            self.stdout.write(scorer.generate_report(result))

        return result

    def _run_drift(self, use_llm, model, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5D: Schema Drift Detection"))

        from apps.ai_assistant.services.watch_schemas import SchemaDriftDetector
        detector = SchemaDriftDetector(use_llm=use_llm)

        if model:
            result = detector.detect_model(model)
            result = {"models_checked": 1, "total_issues": len(result.get("issues", [])),
                       "severity_counts": {}, "per_model": {model: result}}
        else:
            result = detector.detect_all()

        severity = result.get("severity_counts", {})
        self.stdout.write(
            f"  Models: {result.get('models_checked', 0)} | "
            f"Issues: {result.get('total_issues', 0)} | "
            f"High: {severity.get('high', 0)} | Medium: {severity.get('medium', 0)} | Low: {severity.get('low', 0)}"
        )

        if report:
            self.stdout.write(detector.format_report(result))

        return result

    def _run_cleanup(self, limit, use_llm, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5C: Data Cleanup"))

        from apps.ai_assistant.services.data_parser import DataParser
        parser = DataParser(use_llm=use_llm)

        addr_result = parser.bulk_clean_addresses(limit=limit)
        phone_result = parser.bulk_clean_phones(limit=limit)

        self.stdout.write(
            f"  Addresses: {addr_result.get('processed', 0)} processed, {addr_result.get('cleaned', 0)} cleaned | "
            f"Phones: {phone_result.get('processed', 0)} processed, {phone_result.get('cleaned', 0)} cleaned"
        )

        if report:
            self.stdout.write(parser.generate_report(addr_result, phone_result))

        return {"addresses": addr_result, "phones": phone_result}

    def _run_optimize(self, limit, apply, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5B: JSON Envelope Optimization"))

        from apps.ai_assistant.services.json_optimizer import JSONOptimizer
        optimizer = JSONOptimizer()

        analysis = optimizer.analyze_all(limit=limit)

        compact_result = None
        if apply:
            compact_result = optimizer.compact_all(limit=limit, dry_run=False)
            self.stdout.write(
                f"  Compacted: {compact_result.get('compacted', 0)} / {compact_result.get('processed', 0)}"
            )
        else:
            self.stdout.write("  (Dry run — use --apply to compact)")

        self.stdout.write(
            f"  Models: {analysis.get('models_analyzed', 0)} | "
            f"Records with issues: {analysis.get('total_records_with_issues', 0)}"
        )

        if report:
            self.stdout.write(optimizer.format_report(analysis))

        return {"analysis": analysis, "compact": compact_result}

    def _run_margins(self, limit, use_llm, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5F: Margin Tracking"))

        from apps.ai_assistant.services.margin_tracker import MarginTracker
        tracker = MarginTracker(use_llm=use_llm)

        margin_report = tracker.compute_item_margins(limit=limit)

        self.stdout.write(
            f"  Items: {margin_report.get('items_analyzed', 0)} | "
            f"Avg Margin: {margin_report.get('avg_margin_pct', 0)}% | "
            f"Anomalies: {len(margin_report.get('anomalies', []))}"
        )

        if report:
            self.stdout.write(tracker.format_report(margin_report))

        return margin_report

    def _run_velocity(self, limit, use_llm, report):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5G: Inventory Velocity"))

        from apps.ai_assistant.services.margin_tracker import MarginTracker
        tracker = MarginTracker(use_llm=use_llm)

        velocity_report = tracker.compute_velocity(limit=limit)

        self.stdout.write(
            f"  Items: {velocity_report.get('items_analyzed', 0)} | "
            f"Investment: ${velocity_report.get('total_inventory_investment', 0):,.2f} | "
            f"Dead stock: {velocity_report.get('dead_stock_count', 0)} | "
            f"Slow movers: {velocity_report.get('slow_mover_count', 0)}"
        )

        if report:
            margin_report = tracker.compute_item_margins(limit=limit)
            self.stdout.write(tracker.format_report(margin_report, velocity_report))

        return velocity_report

    def _run_layout(self, use_llm, model, report, report_file=False,
                     dismiss="", undismiss="", reason="", history=False):
        self.stdout.write(self.style.HTTP_INFO("\n▶ 5H: Layout Drift Detection"))

        from apps.ai_assistant.services.watch_layouts import LayoutDriftDetector
        detector = LayoutDriftDetector(use_llm=use_llm)

        # Handle dismiss/undismiss/history sub-commands
        if dismiss:
            parts = dismiss.split(":", 2)
            if len(parts) != 3:
                self.stderr.write(self.style.ERROR(
                    "  --dismiss format: model:field:issue_type"
                ))
                return {}
            result = detector.dismiss_issue(parts[0], parts[1], parts[2], reason=reason)
            self.stdout.write(self.style.SUCCESS(
                f"  Dismissed: {dismiss} — {reason or 'no reason given'}"
            ))
            return result

        if undismiss:
            parts = undismiss.split(":", 2)
            if len(parts) != 3:
                self.stderr.write(self.style.ERROR(
                    "  --undismiss format: model:field:issue_type"
                ))
                return {}
            result = detector.undismiss_issue(parts[0], parts[1], parts[2])
            self.stdout.write(self.style.SUCCESS(f"  Undismissed: {undismiss}"))
            return result

        if history:
            hist = detector.get_correction_history()
            self.stdout.write(f"  Scan runs: {hist['total_runs']}")
            self.stdout.write(f"  Total corrections: {hist['total_corrections']}")
            self.stdout.write(f"  Trend: {hist['trend']}")
            if hist["correction_patterns"]:
                self.stdout.write("  Corrections by type:")
                for t, c in hist["correction_patterns"].items():
                    self.stdout.write(f"    {t}: {c}")
            if hist["recent_corrections"]:
                self.stdout.write("  Recent corrections:")
                for c in hist["recent_corrections"][-10:]:
                    self.stdout.write(
                        f"    {c['model']}.{c['field']} ({c['issue_type']}) "
                        f"resolved {c['resolved_at'][:10]}"
                    )
            dismissed = detector.list_dismissals()
            if dismissed:
                self.stdout.write(f"  Dismissed issues: {len(dismissed)}")
                for d in dismissed:
                    self.stdout.write(
                        f"    {d['model']}.{d['field']} ({d['issue_type']}): "
                        f"{d.get('reason', '—')}"
                    )
            return hist

        # Run detection
        if model:
            result = detector.detect_model(model)
            result = {"models_checked": 1, "total_issues": len(
                [i for i in result.get("issues", []) if i.get("severity") != "info"]
            ), "severity_counts": {}, "per_model": {model: result}}
        else:
            result = detector.detect_all()

        severity = result.get("severity_counts", {})
        self.stdout.write(
            f"  Models: {result.get('models_checked', 0)} | "
            f"Issues: {result.get('total_issues', 0)} | "
            f"High: {severity.get('high', 0)} | Medium: {severity.get('medium', 0)} | "
            f"Low: {severity.get('low', 0)} | Info: {severity.get('info', 0)}"
        )

        if report_file or report:
            full_report = detector.generate_full_report(result, save=report_file)
            self.stdout.write(full_report)
            if report_file:
                self.stdout.write(self.style.SUCCESS(
                    "\n  Report saved to readmes/topics/ai/layout-drift-report.md"
                ))

        return result
