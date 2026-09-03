"""
Support Feed — WCHQ support services for connected instances.

Three services flow through the same telemetry model as episodes:

    1. Coaching distribution — WCHQ serves coaching content, instances poll
    2. Help pattern aggregation — WCHQ collects help requests, detects patterns
    3. Support summary — admin dashboard showing support health

Coaching content lives in Setting records (purpose='wc:coaching') and
Document records. Instances pull coaching updates like they pull
episode feeds — poll, take what's useful, leave the rest.

Help patterns aggregate from support_qa escalations. When multiple
instances hit the same wall, that pattern becomes a coaching candidate.

    Instance asks question (support_qa)
            ↓
    Escalated to WCHQ (Bundle on wchq-conn-upstream)
            ↓
    WCHQ aggregates patterns across instances
            ↓
    Pattern → coaching candidate → new coaching content
            ↓
    Instances poll coaching feed, pick up improvements
"""
import logging
import time
from collections import Counter

logger = logging.getLogger(__name__)


# ── Coaching Feed ─────────────────────────────────────────────────────

def build_coaching_feed(since_ms: int = 0) -> dict:
    """Build the coaching feed — Setting and Document records for distribution.

    WCHQ serves this. Instances poll it. Coaching content includes:
      - Setting records (purpose='wc:coaching') — field help, tips, warnings
      - Document records (config.purpose='coaching') — how-to guides
      - AlicePreset records (source='wchq') — paved paths

    Args:
        since_ms: Only content modified after this timestamp.

    Returns dict — the coaching feed payload.
    """
    from apps.core.models import Setting
    from apps.docs.models.document import Document

    now_ms = int(time.time() * 1000)

    # Coaching settings — field help, tips per model
    settings_qs = Setting.objects.filter(
        purpose='wc:coaching', is_active=True,
    )
    if since_ms:
        settings_qs = settings_qs.filter(dt_modified__gte=since_ms)

    coaching_settings = []
    for s in settings_qs.values('uuid', 'ida', 'name', 'config', 'dt_modified'):
        s['uuid'] = str(s['uuid']) if s['uuid'] else ''
        coaching_settings.append(s)

    # Coaching documents — how-to guides
    docs_qs = Document.objects.filter(
        config__purpose='coaching', is_active=True, status='published',
    )
    if since_ms:
        docs_qs = docs_qs.filter(dt_modified__gte=since_ms)

    coaching_docs = []
    for d in docs_qs.values('uuid', 'ida', 'name', 'body', 'config', 'dt_modified'):
        d['uuid'] = str(d['uuid']) if d['uuid'] else ''
        # Don't send full body in feed — just metadata + preview
        d['body_preview'] = (d.pop('body', '') or '')[:500]
        coaching_docs.append(d)

    return {
        'type': 'coaching_feed',
        'version': '1.0',
        'dt_built': now_ms,
        'since_ms': since_ms,
        'settings': coaching_settings,
        'documents': coaching_docs,
        'counts': {
            'settings': len(coaching_settings),
            'documents': len(coaching_docs),
        },
    }


def ingest_coaching(feed: dict) -> dict:
    """Ingest coaching content from WCHQ feed into local instance.

    Upserts by uuid. Local customizations are preserved — WCHQ
    coaching merges, it doesn't overwrite.

    Args:
        feed: The coaching feed dict from build_coaching_feed().

    Returns summary.
    """
    from apps.core.models import Setting

    settings = feed.get('settings', [])
    created = 0
    updated = 0
    skipped = 0

    for s_data in settings:
        ida = s_data.get('ida', '')
        if not ida:
            skipped += 1
            continue

        try:
            existing = Setting.objects.filter(ida=ida, purpose='wc:coaching').first()
            if existing:
                # Merge — don't overwrite local customizations
                incoming_config = s_data.get('config', {})
                local_config = existing.config if isinstance(existing.config, dict) else {}

                # Merge tips, field_help, warnings — append new, keep existing
                for key in ('tips', 'warnings', 'code_examples'):
                    incoming_items = incoming_config.get(key, [])
                    local_items = local_config.get(key, [])
                    # Add items not already present (by text content)
                    local_texts = {str(item) for item in local_items}
                    for item in incoming_items:
                        if str(item) not in local_texts:
                            local_items.append(item)
                    local_config[key] = local_items

                # field_help — merge keys, don't overwrite existing
                incoming_help = incoming_config.get('field_help', {})
                local_help = local_config.get('field_help', {})
                for field, help_text in incoming_help.items():
                    if field not in local_help:
                        local_help[field] = help_text
                local_config['field_help'] = local_help

                existing.config = local_config
                existing.save()
                updated += 1
            else:
                Setting.objects.create(
                    ida=ida,
                    name=s_data.get('name', ''),
                    purpose='wc:coaching',
                    config=s_data.get('config', {}),
                )
                created += 1

        except Exception as e:
            logger.warning("Coaching ingest failed for %s: %s", ida, e)
            skipped += 1

    return {'created': created, 'updated': updated, 'skipped': skipped}


# ── Help Pattern Aggregation ──────────────────────────────────────────

def detect_help_patterns(since_days: int = 30) -> dict:
    """Scan escalated support Q&A for recurring help patterns.

    When multiple instances ask the same kind of question, that
    pattern becomes a coaching candidate. Creates:
      1. AliceObservation (notifies admin of the pattern)
      2. Optionally, a coaching Setting candidate

    Args:
        since_days: Look back this many days.

    Returns summary.
    """
    from apps.docs.models.document import Document
    from apps.ai_assistant.models.alice import AliceObservation
    from django.apps import apps
    import hashlib

    Bundle = apps.get_model('sync', 'Bundle')

    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (since_days * 86400 * 1000)

    # Find escalated Q&A bundles from connected instances
    qa_bundles = Bundle.objects.filter(
        config__content_type='support_qa',
        dt_created__gte=since_ms,
        is_active=True,
    ).order_by('dt_created')

    if not qa_bundles.exists():
        return {'bundles_scanned': 0, 'patterns_found': 0, 'observations_created': 0}

    # Group questions by model/domain
    by_model = Counter()
    by_keyword = Counter()
    questions = []

    for bundle in qa_bundles:
        payload = bundle.payload if isinstance(bundle.payload, dict) else {}
        question = payload.get('question', '')
        context = payload.get('context', {})
        config = payload.get('config', {})

        model = context.get('model', 'unknown')
        by_model[model] += 1

        keywords = config.get('keywords', [])
        for kw in keywords:
            by_keyword[kw] += 1

        questions.append({
            'question': question,
            'model': model,
            'screen': context.get('screen', ''),
            'source_connection': bundle.connection_id,
        })

    # Find recurring patterns (model + keyword combinations appearing 3+ times)
    patterns_found = 0
    observations_created = 0

    for model, count in by_model.most_common():
        if count < 3:
            continue

        patterns_found += 1
        pattern_key = f"help-pattern-{model}"
        dedup_key = f"hp-{hashlib.md5(pattern_key.encode()).hexdigest()[:12]}"

        # Skip if already observed
        if AliceObservation.objects.filter(dedup_key=dedup_key, resolved=False).exists():
            continue

        model_questions = [q for q in questions if q['model'] == model]
        sample_qs = [q['question'][:100] for q in model_questions[:5]]

        # Count unique sources (instances)
        unique_sources = len(set(q['source_connection'] for q in model_questions))

        AliceObservation.objects.create(
            category='coaching',
            source='alice',
            priority=1 if unique_sources > 1 else 0,
            message=(
                f"Help pattern: {count} questions about '{model}' "
                f"from {unique_sources} instance(s). Consider adding coaching content."
            ),
            detail=(
                f"Model: {model}\n"
                f"Question count: {count}\n"
                f"Unique instances: {unique_sources}\n"
                f"Sample questions:\n"
                + '\n'.join(f"  - {q}" for q in sample_qs)
            ),
            model_name='Document',
            dedup_key=dedup_key,
        )
        observations_created += 1

    return {
        'bundles_scanned': qa_bundles.count(),
        'patterns_found': patterns_found,
        'observations_created': observations_created,
        'top_models': dict(by_model.most_common(10)),
        'top_keywords': dict(by_keyword.most_common(10)),
    }


# ── Support Summary ──────────────────────────────────────────────────

def get_support_summary(period_days: int = 7) -> dict:
    """Support summary for the admin console.

    Answers:
      1. Q&A health — answered, unanswered, low-scored, escalated
      2. Coaching coverage — how many models have coaching content
      3. Help patterns — recurring questions across instances
      4. Escalation volume — how many questions left the instance

    Args:
        period_days: "Recent" = within this many days.

    Returns dict for the admin dashboard.
    """
    from apps.docs.models.document import Document
    from apps.core.models import Setting
    from apps.ai_assistant.models.alice import AliceObservation, AliceCoachingLog
    from django.apps import apps
    from django.db.models import Count, Avg

    Bundle = apps.get_model('sync', 'Bundle')

    now_ms = int(time.time() * 1000)
    period_start = now_ms - (period_days * 86400 * 1000)

    # Q&A counts
    qa_base = Document.objects.filter(
        config__purpose='support_qa', is_active=True,
    )
    qa_total = qa_base.count()
    qa_published = qa_base.filter(status='published').count()
    qa_draft = qa_base.filter(status='draft').count()

    # Low-scored (avg < 2.0 with 3+ ratings)
    qa_low_scored = 0
    for doc in qa_base.filter(status='published'):
        cfg = doc.config or {}
        if cfg.get('score_count', 0) >= 3 and cfg.get('score_avg', 5) < 2.0:
            qa_low_scored += 1

    # Escalated (posted to WCHQ)
    qa_escalated = qa_base.filter(config__wchq_posted=True).count()

    # New Q&A this period
    qa_new = qa_base.filter(dt_created__gte=period_start).count()

    # Coaching coverage
    coaching_settings = Setting.objects.filter(
        purpose='wc:coaching', is_active=True,
    ).count()

    # Coaching drills completed this period
    drills_completed = AliceCoachingLog.objects.filter(
        completed=True, dt_completed__gte=period_start,
    ).count()
    drills_passed = AliceCoachingLog.objects.filter(
        passed=True, dt_completed__gte=period_start,
    ).count()

    # Escalation bundles this period
    escalation_bundles = Bundle.objects.filter(
        config__content_type='support_qa',
        dt_created__gte=period_start,
        is_active=True,
    ).count()

    # Active coaching observations (unresolved help patterns)
    coaching_observations = AliceObservation.objects.filter(
        category='coaching',
        resolved=False,
        is_active=True,
    ).count()

    return {
        'period_days': period_days,
        'qa': {
            'total': qa_total,
            'published': qa_published,
            'unanswered': qa_draft,
            'low_scored': qa_low_scored,
            'escalated': qa_escalated,
            'new_this_period': qa_new,
        },
        'coaching': {
            'models_covered': coaching_settings,
            'drills_completed': drills_completed,
            'drills_passed': drills_passed,
            'pass_rate': round(drills_passed / max(drills_completed, 1) * 100, 1),
        },
        'escalation': {
            'bundles_this_period': escalation_bundles,
            'pending_patterns': coaching_observations,
        },
    }
