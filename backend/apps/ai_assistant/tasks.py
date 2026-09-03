"""
Phase 5 Celery tasks — Autonomous Data Intelligence.

Plain functions (project convention) wrapping service calls.
Schedule via Celery Beat in settings or register with django-celery-beat.

Beat schedule example (settings.py):
    CELERY_BEAT_SCHEDULE = {
        'ai-health-scoring-nightly': {
            'task': 'ai_assistant.tasks.health_scoring_task',
            'schedule': crontab(hour=2, minute=0),
        },
        'ai-json-optimize-nightly': {
            'task': 'ai_assistant.tasks.json_optimize_task',
            'schedule': crontab(hour=2, minute=30),
        },
        'ai-data-cleanup-nightly': {
            'task': 'ai_assistant.tasks.data_cleanup_task',
            'schedule': crontab(hour=3, minute=0),
        },
        'ai-schema-drift-weekly': {
            'task': 'ai_assistant.tasks.schema_drift_task',
            'schedule': crontab(hour=4, minute=0, day_of_week=1),
        },
        'ai-margin-tracking-weekly': {
            'task': 'ai_assistant.tasks.margin_tracking_task',
            'schedule': crontab(hour=4, minute=30, day_of_week=1),
        },
        'ai-velocity-weekly': {
            'task': 'ai_assistant.tasks.velocity_task',
            'schedule': crontab(hour=5, minute=0, day_of_week=1),
        },
        'ai-relationship-scan-nightly': {
            'task': 'ai_assistant.tasks.relationship_scan_task',
            'schedule': crontab(hour=3, minute=30),
        },
    }
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Alice: Schema Watch ─────────────────────────────────────────────

@shared_task
def alice_schema_watch_task() -> dict:
    """Nightly task: let Alice assess schema changes and impacted pages.

    Uses working tree/staged git diff context, writes Alice notes, and
    emits a markdown report artifact under readmes/topics/ai/reports.
    """
    logger.info("Starting Alice schema watch task")
    started = timezone.now()

    from django.core.management import call_command

    call_command("alice_schema_watch", quiet=True)

    duration = (timezone.now() - started).total_seconds()
    result = {
        "status": "ok",
        "duration_seconds": duration,
    }
    logger.info("Alice schema watch complete in %.1fs", duration)
    return result


# ─── 5E: Health Scoring ───────────────────────────────────────────────

@shared_task
def health_scoring_task(limit: int = 500, use_llm: bool = False) -> dict:
    """Nightly task: score data health for all HealthMixin models.

    Updates health_rating (0-100) on each record.
    """
    logger.info("Starting health scoring task (limit=%d, use_llm=%s)", limit, use_llm)
    started = timezone.now()

    from apps.ai_assistant.services.health_scorer import HealthScorer

    scorer = HealthScorer(use_llm=use_llm)
    result = scorer.score_all(limit=limit)

    duration = (timezone.now() - started).total_seconds()
    result["duration_seconds"] = duration
    logger.info(
        "Health scoring complete: %d models, %d records, %d updated in %.1fs",
        result.get("models_scored", 0),
        result.get("total_processed", 0),
        result.get("total_updated", 0),
        duration,
    )
    return result


# ─── 5D: Schema Drift Detection ───────────────────────────────────────

@shared_task
def schema_drift_task(use_llm: bool = False) -> dict:
    """Weekly task: detect Django ↔ TypeScript schema drift.

    Compares model fields against TS interfaces and flags mismatches.
    """
    logger.info("Starting schema drift detection")
    started = timezone.now()

    from apps.ai_assistant.services.watch_schemas import SchemaDriftDetector

    detector = SchemaDriftDetector(use_llm=use_llm)
    report = detector.detect_all()

    duration = (timezone.now() - started).total_seconds()
    report["duration_seconds"] = duration
    logger.info(
        "Schema drift complete: %d models checked, %d issues found in %.1fs",
        report.get("models_checked", 0),
        report.get("total_issues", 0),
        duration,
    )
    return report


# ─── 5C: Data Cleanup ─────────────────────────────────────────────────

@shared_task
def data_cleanup_task(limit: int = 500, use_llm: bool = True) -> dict:
    """Nightly task: clean and normalize addresses and phone numbers.

    Uses deterministic parsers first, Ollama for fuzzy cases.
    """
    logger.info("Starting data cleanup task (limit=%d)", limit)
    started = timezone.now()

    from apps.ai_assistant.services.data_parser import DataParser

    parser = DataParser(use_llm=use_llm)
    address_result = parser.bulk_clean_addresses(limit=limit)
    phone_result = parser.bulk_clean_phones(limit=limit)

    duration = (timezone.now() - started).total_seconds()
    result = {
        "addresses": address_result,
        "phones": phone_result,
        "duration_seconds": duration,
    }
    logger.info(
        "Data cleanup complete: %d addresses (%d cleaned), %d phones (%d cleaned) in %.1fs",
        address_result.get("processed", 0),
        address_result.get("cleaned", 0),
        phone_result.get("processed", 0),
        phone_result.get("cleaned", 0),
        duration,
    )
    return result


# ─── 5B: JSON Envelope Optimization ───────────────────────────────────

@shared_task
def json_optimize_task(limit: int = 500, dry_run: bool = True) -> dict:
    """Nightly task: analyze and optionally compact JSON envelopes.

    Set dry_run=False to actually apply auto-fixable optimizations.
    """
    logger.info("Starting JSON optimization task (limit=%d, dry_run=%s)", limit, dry_run)
    started = timezone.now()

    from apps.ai_assistant.services.json_optimizer import JSONOptimizer

    optimizer = JSONOptimizer()

    # Analyze first
    analysis = optimizer.analyze_all(limit=limit)

    # Compact if not dry run
    compact_result = None
    if not dry_run:
        compact_result = optimizer.compact_all(limit=limit, dry_run=False)

    duration = (timezone.now() - started).total_seconds()
    result = {
        "analysis": analysis,
        "compact": compact_result,
        "dry_run": dry_run,
        "duration_seconds": duration,
    }
    logger.info(
        "JSON optimization complete: %d models, %d records with issues in %.1fs",
        analysis.get("models_analyzed", 0),
        analysis.get("total_records_with_issues", 0),
        duration,
    )
    return result


# ─── 5F: Margin Tracking ──────────────────────────────────────────────

@shared_task
def margin_tracking_task(limit: int = 500, use_llm: bool = False) -> dict:
    """Weekly task: compute and analyze product margins.

    Runs deterministic margin math and optionally generates LLM narrative.
    """
    logger.info("Starting margin tracking task (limit=%d)", limit)
    started = timezone.now()

    from apps.ai_assistant.services.margin_tracker import MarginTracker

    tracker = MarginTracker(use_llm=use_llm)
    margin_report = tracker.compute_item_margins(limit=limit)

    llm_analysis = ""
    if use_llm:
        llm_analysis = tracker.llm_margin_analysis(margin_report)

    duration = (timezone.now() - started).total_seconds()
    result = {
        "margins": margin_report,
        "llm_analysis": llm_analysis,
        "duration_seconds": duration,
    }
    logger.info(
        "Margin tracking complete: %d items, avg margin %.1f%%, %d anomalies in %.1fs",
        margin_report.get("items_analyzed", 0),
        margin_report.get("avg_margin_pct", 0),
        len(margin_report.get("anomalies", [])),
        duration,
    )
    return result


# ─── 5G: Inventory Velocity ───────────────────────────────────────────

@shared_task
def velocity_task(limit: int = 500, use_llm: bool = False) -> dict:
    """Weekly task: compute inventory velocity and investment efficiency.

    Measures margin earned per unit of time capital is tied up.
    """
    logger.info("Starting velocity task (limit=%d)", limit)
    started = timezone.now()

    from apps.ai_assistant.services.margin_tracker import MarginTracker

    tracker = MarginTracker(use_llm=use_llm)
    velocity_report = tracker.compute_velocity(limit=limit)

    # Update ItemUsage records with velocity metrics
    update_result = tracker.update_usage_velocity(limit=limit)

    llm_analysis = ""
    if use_llm:
        llm_analysis = tracker.llm_velocity_analysis(velocity_report)

    duration = (timezone.now() - started).total_seconds()
    result = {
        "velocity": velocity_report,
        "usage_updated": update_result.get("updated", 0),
        "llm_analysis": llm_analysis,
        "duration_seconds": duration,
    }
    logger.info(
        "Velocity task complete: %d items, $%.2f total investment, "
        "%d dead stock, %d slow movers in %.1fs",
        velocity_report.get("items_analyzed", 0),
        velocity_report.get("total_inventory_investment", 0),
        velocity_report.get("dead_stock_count", 0),
        velocity_report.get("slow_mover_count", 0),
        duration,
    )
    return result

# ─── 5H: Layout Drift Detection ───────────────────────────────────

@shared_task
def layout_drift_task(use_llm: bool = False) -> dict:
    """Weekly task: detect Django ↔ React layout field drift.

    Compares model fields against actual field references in page components
    (Detail forms, List columns, Display views).
    Records correction history for LLM learning.
    """
    logger.info("Starting layout drift detection")
    started = timezone.now()

    from apps.ai_assistant.services.watch_layouts import LayoutDriftDetector

    detector = LayoutDriftDetector(use_llm=use_llm)
    report = detector.detect_all()

    # Generate full report and record in correction history
    detector.generate_full_report(report, save=True)

    duration = (timezone.now() - started).total_seconds()
    report["duration_seconds"] = duration
    logger.info(
        "Layout drift complete: %d models checked, %d issues found in %.1fs",
        report.get("models_checked", 0),
        report.get("total_issues", 0),
        duration,
    )
    return report

# ─── Apply Pending Layouts ───────────────────────────────────────────

@shared_task
def apply_pending_layouts_task() -> dict:
    """Process pending layout changes from Pending → Setting.

    Reads Pending records with purpose='layout_change' and dt_processed=0.
    Applies each view to the corresponding Setting record, then marks processed.
    """
    started = timezone.now()

    from apps.core.models import Setting
    from apps.core.models.pending import Pending

    pending_qs = Pending.objects.filter(
        purpose='layout_change',
        dt_processed=0,
    ).order_by('dt_created')

    applied = 0
    errors = 0
    for p in pending_qs:
        data = p.config or {}
        target_model = data.get('target_model')
        view = data.get('view')  # the layout change {list, detail, views}

        if not target_model or not view:
            p.config = {**data, 'error': 'missing target_model or view'}
            p.mark_processed()
            errors += 1
            continue

        try:
            # Try wc:model first (consolidated), fall back to legacy
            setting = Setting.objects.filter(
                parent_model=target_model,
                purpose='wc:model',
            ).first()

            if setting:
                cfg = setting.config or {}
                cfg['columns'] = view
                setting.config = cfg
                setting.save(update_fields=['config', 'dt_modified'])
                logger.info(f"[apply_pending_layouts] Updated wc:model #{setting.id} columns for {target_model}")
            else:
                setting = Setting.objects.filter(
                    parent_model=target_model,
                    purpose='wc:workbench_fields',
                ).first()

                if not setting:
                    setting = Setting.objects.create(
                        name=f'{target_model} Model Definition',
                        ida=f'wc-model-{target_model}',
                        parent_model=target_model,
                        purpose='wc:model',
                        scope='system',
                        config={'columns': view},
                    )
                    logger.info(f"[apply_pending_layouts] Created wc:model #{setting.id} for {target_model}")
                else:
                    setting.config = view
                    setting.save(update_fields=['config', 'dt_modified'])
                    logger.info(f"[apply_pending_layouts] Updated legacy #{setting.id} for {target_model}")

            p.config = {**data, 'setting_id': setting.id, 'status': 'applied'}
            p.mark_processed()
            applied += 1

        except Exception as e:
            logger.exception(f"[apply_pending_layouts] Failed for {target_model}")
            p.config = {**data, 'error': str(e)}
            p.mark_processed()
            errors += 1

    duration = (timezone.now() - started).total_seconds()
    result = {'applied': applied, 'errors': errors, 'duration_seconds': duration}
    if applied > 0:
        logger.info(f"[apply_pending_layouts] Applied {applied}, errors {errors} in {duration:.1f}s")
    return result


# ─── 5I: Relationship Intelligence ───────────────────────────────────

@shared_task
def relationship_scan_task(customer_limit: int = 500, vendor_limit: int = 200) -> dict:
    """Nightly task: scan all relationships for health, lifecycle, and triggers.

    Alice hunts for ways to enhance the value of every relationship —
    customers, vendors, employees, reps. Creates AliceObservation records
    for actionable findings and updates metadata.health with relationship signals.
    """
    logger.info("Starting relationship intelligence scan")
    started = timezone.now()

    from apps.ai_assistant.services.relationship_intelligence import RelationshipIntelligence

    ri = RelationshipIntelligence()
    result = ri.scan_all(customer_limit=customer_limit, vendor_limit=vendor_limit)

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration

    cust = result.get('customers', {})
    vend = result.get('vendors', {})
    logger.info(
        "Relationship scan complete: %d customers (%d obs), %d vendors (%d obs) in %.1fs",
        cust.get('scanned', 0), cust.get('observations_created', 0),
        vend.get('scanned', 0), vend.get('observations_created', 0),
        duration,
    )
    return result


# ─── Combined: Full Intelligence Run ──────────────────────────────────

@shared_task
def full_intelligence_run(limit: int = 500, use_llm: bool = False, dry_run: bool = True) -> dict:
    """Run all Phase 5 tasks in sequence. Suitable for a nightly mega-task.

    Returns combined results from all sub-tasks.
    """
    logger.info("Starting full intelligence run (limit=%d, use_llm=%s, dry_run=%s)", limit, use_llm, dry_run)
    started = timezone.now()

    results = {}

    results["health"] = health_scoring_task(limit=limit, use_llm=use_llm)
    results["schema_drift"] = schema_drift_task(use_llm=use_llm)
    results["data_cleanup"] = data_cleanup_task(limit=limit, use_llm=use_llm)
    results["json_optimization"] = json_optimize_task(limit=limit, dry_run=dry_run)
    results["margins"] = margin_tracking_task(limit=limit, use_llm=use_llm)
    results["velocity"] = velocity_task(limit=limit, use_llm=use_llm)
    results["layout_drift"] = layout_drift_task(use_llm=use_llm)
    results["relationships"] = relationship_scan_task()
    results["dedup"] = dedup_scan_task()
    results["accounting"] = accounting_watchdog_task()
    results["inventory"] = inventory_watchdog_task()
    results["select_lists"] = select_list_watchdog_task()

    total_duration = (timezone.now() - started).total_seconds()
    results["total_duration_seconds"] = total_duration
    logger.info("Full intelligence run complete in %.1fs", total_duration)

    return results


# ─── Duplicate Detection ────────────────────────────────────────────────

@shared_task
def dedup_scan_task(limit_per_model: int = 500, auto_extract: bool = False) -> dict:
    """Nightly task: scan all models for duplicate records.

    Alice identifies duplicates, serializes them to sync/dedup/pending/,
    creates Bundle records referencing the retained record, and deactivates
    duplicates in the database.

    Set auto_extract=True to automatically extract found duplicates.
    Default is scan-only (creates AliceObservation records for review).

    Args:
        limit_per_model: max records to scan per model
        auto_extract: if True, extract high-confidence duplicates automatically
    """
    logger.info("Starting dedup scan (limit=%d, auto_extract=%s)", limit_per_model, auto_extract)
    started = timezone.now()

    from apps.ai_assistant.services.dedup import DedupService

    svc = DedupService()
    scan_results = svc.scan_all(limit_per_model=limit_per_model)

    extracted = 0
    if auto_extract:
        for model_name in scan_results:
            groups = svc.scan_model(model_name, limit=limit_per_model)
            for group in groups:
                if group['confidence'] == 'high':
                    result = svc.extract_duplicates(group)
                    if not result.get('error'):
                        extracted += 1

    scan_results['auto_extracted'] = extracted

    duration = (timezone.now() - started).total_seconds()
    scan_results['duration_seconds'] = duration

    total_groups = sum(v.get('groups_found', 0) for v in scan_results.values() if isinstance(v, dict))
    total_dups = sum(v.get('total_duplicates', 0) for v in scan_results.values() if isinstance(v, dict))
    logger.info(
        "Dedup scan complete: %d groups, %d duplicates, %d auto-extracted in %.1fs",
        total_groups, total_dups, extracted, duration,
    )
    return scan_results


# ─── Alice Inbox (real-time bus processing) ──────────────────────────

@shared_task
def alice_inbox_task(batch_size: int = 50) -> dict:
    """Process Alice's agent bus inbox (every 60s).

    Reads unread messages from agent_messages, processes by category,
    creates AliceObservation records for anomalies, marks messages read.
    This is Alice's real-time awareness layer.
    """
    from apps.ai_assistant.services.inbox import process_inbox
    return process_inbox(batch_size=batch_size)


# ─── Accounting Watchdog ─────────────────────────────────────────────

@shared_task
def accounting_watchdog_task() -> dict:
    """Nightly task: scan for GL imbalances, payment anomalies, aging issues.

    Alice checks:
    - GL batch balance (debits == credits)
    - Invoice balance vs payments applied
    - Unapplied payments
    - Orphaned ledger entries
    - 90+ day past-due aging
    """
    logger.info("Starting accounting watchdog")
    started = timezone.now()

    from apps.ai_assistant.services.watch_accounting import run_accounting_watchdog
    result = run_accounting_watchdog()

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration
    logger.info("Accounting watchdog complete in %.1fs", duration)
    return result


# ─── Inventory Watchdog ──────────────────────────────────────────────

@shared_task
def inventory_watchdog_task(limit: int = 1000) -> dict:
    """Nightly task: scan for over/understock, dead stock, quantity errors.

    Alice checks:
    - Items below reorder point (understock)
    - Items above max stock (overstock)
    - Negative on_hand (data error)
    - Quantity calculation mismatches
    - Dead stock (no sales 90+ days)
    """
    logger.info("Starting inventory watchdog")
    started = timezone.now()

    from apps.ai_assistant.services.watch_inventory import run_inventory_watchdog
    result = run_inventory_watchdog(limit=limit)

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration
    logger.info("Inventory watchdog complete in %.1fs", duration)
    return result


# ─── Select List Watchdog ────────────────────────────────────────────

@shared_task
def select_list_watchdog_task(limit: int = 500) -> dict:
    """Weekly task: detect hallucinated options and unlisted values.

    Alice checks:
    - UNLISTED: values in DB not in select options (real-world values baseline missed)
    - UNUSED: options defined but never used (hallucination candidates, after 30+ days)
    - COVERAGE: % of defined options actually in use per field
    """
    logger.info("Starting select list watchdog")
    started = timezone.now()

    from apps.ai_assistant.services.watch_select_lists import run_select_list_watchdog
    result = run_select_list_watchdog(limit=limit)

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration
    logger.info("Select list watchdog complete in %.1fs", duration)
    return result


# ─── Episode Harvest (all active connections) ────────────────────────

@shared_task
def harvest_all_episodes_task() -> dict:
    """Every 6 hours: harvest episodes from all active Connections
    with config.episode_harvest=true.

    Iterates qualifying connections, calls harvest_episodes() for each,
    and logs aggregate results.
    """
    logger.info("Starting episode harvest for all connections")
    started = timezone.now()

    from apps.sync.models.connection import Connection
    from apps.sync.services.episode_bundle import harvest_episodes

    connections = Connection.objects.filter(status='active')
    harvested = 0
    errors = 0
    results_by_connection = {}

    for conn in connections:
        cfg = conn.config or {}
        if not cfg.get('episode_harvest'):
            continue
        try:
            result = harvest_episodes(conn)
            results_by_connection[conn.id] = result
            harvested += 1
        except Exception:
            logger.exception("Episode harvest failed for connection %s (%s)", conn.id, conn.name)
            results_by_connection[conn.id] = {'error': True}
            errors += 1

    duration = (timezone.now() - started).total_seconds()
    result = {
        'connections_harvested': harvested,
        'errors': errors,
        'details': results_by_connection,
        'duration_seconds': duration,
    }
    logger.info(
        "Episode harvest complete: %d connections harvested, %d errors in %.1fs",
        harvested, errors, duration,
    )
    return result


# ─── Episode Pattern Detection ───────────────────────────────────────

@shared_task
def detect_episode_patterns_task(since_days: int = 30) -> dict:
    """Nightly task: detect rejected patterns in recent episodes.

    Calls detect_rejected_patterns() to find recurring rejection signals
    and creates observations for actionable findings.
    """
    logger.info("Starting episode pattern detection (since_days=%d)", since_days)
    started = timezone.now()

    from apps.ai_assistant.services.episode_patterns import detect_rejected_patterns

    result = detect_rejected_patterns(since_days=since_days)

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration
    logger.info("Episode pattern detection complete in %.1fs", duration)
    return result


# ─── Help Pattern Detection ──────────────────────────────────────────

@shared_task
def detect_help_patterns_task(since_days: int = 30) -> dict:
    """Nightly task: detect patterns in support/help requests.

    Calls detect_help_patterns() to identify recurring support themes
    and creates observations for actionable findings.
    """
    logger.info("Starting help pattern detection (since_days=%d)", since_days)
    started = timezone.now()

    from apps.ai_assistant.services.support_feed import detect_help_patterns

    result = detect_help_patterns(since_days=since_days)

    duration = (timezone.now() - started).total_seconds()
    result['duration_seconds'] = duration
    logger.info("Help pattern detection complete in %.1fs", duration)
    return result


# ─── Alice: Settings Backup (7-day cycle) ───────────────────────────

@shared_task
def config_backup_task() -> dict:
    """Daily task: export Settings and Reports to local JSON bundles.

    Alice keeps a 7-day rolling window of both. These are the only two
    models that hold user-created configuration — everything else is
    commerce data managed by standard user backups.

    - Settings: system behavior, field layouts, model definitions
    - Reports: form templates, print layouts, dashboard definitions

    Schedule: daily at 01:00 (before any nightly intelligence tasks).
    """
    logger.info("Starting config backup (Settings + Reports)")
    started = timezone.now()

    from apps.core.services.setting_bootstrap import (
        export_settings_bundle, prune_old_backups,
        export_report_bundle, prune_old_report_backups,
    )

    settings_export = export_settings_bundle()
    settings_prune = prune_old_backups()
    report_export = export_report_bundle()
    report_prune = prune_old_report_backups()

    duration = (timezone.now() - started).total_seconds()
    result = {
        'settings': {
            **settings_export,
            'pruned': settings_prune['pruned'],
            'kept': settings_prune['kept'],
        },
        'reports': {
            **report_export,
            'pruned': report_prune['pruned'],
            'kept': report_prune['kept'],
        },
        'duration_seconds': duration,
    }
    logger.info(
        "Config backup complete: %d settings (%d bytes), %d reports (%d bytes), %.1fs",
        settings_export.get('count', 0), settings_export.get('size_bytes', 0),
        report_export.get('count', 0), report_export.get('size_bytes', 0),
        duration,
    )
    return result
