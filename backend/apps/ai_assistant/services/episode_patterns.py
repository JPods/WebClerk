"""
Episode Pattern Detection — find recurring clusters in rejected episodes.

Foolish/wrong episodes are not problems to suppress — they are signals
to measure. When the same class of rejected episode keeps appearing
across instances, that recurrence IS the diagnostic signal.

This service:
  1. Clusters rejected episodes by text similarity
  2. When a cluster crosses the recurrence threshold, creates a
     pattern episode that enters the approved feed
  3. Creates an AliceObservation to notify administrators
  4. Provides episode summary statistics for the admin console

The pattern episode says "this keeps happening, which means..." —
not "don't do this." The recurring pattern might reveal a design
flaw, a training gap, or a common misconception.

Usage:
    from apps.ai_assistant.services.episode_patterns import (
        detect_rejected_patterns,
        get_episode_summary,
    )
"""
import hashlib
import logging
import time
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Minimum rejected episodes in a cluster to trigger pattern creation
RECURRENCE_THRESHOLD = 3

# How similar two rejected episodes must be to cluster together
# (measured by shared tags + same domain + similar title words)
SIMILARITY_THRESHOLD = 0.4


def _title_words(title: str) -> set:
    """Extract significant words from a title for similarity comparison."""
    stop = {
        'the', 'a', 'an', 'is', 'was', 'were', 'are', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'and', 'or', 'but', 'not', 'no', 'that', 'this', 'it',
    }
    words = set(w.lower() for w in title.split() if len(w) > 2)
    return words - stop


def _episode_similarity(ep_a: dict, ep_b: dict) -> float:
    """Score similarity between two episodes. 0.0 = unrelated, 1.0 = identical."""
    score = 0.0
    weights = 0.0

    # Domain match (weight 0.3)
    weights += 0.3
    if ep_a.get('domain') == ep_b.get('domain'):
        score += 0.3

    # Episode type match (weight 0.1)
    weights += 0.1
    if ep_a.get('episode_type') == ep_b.get('episode_type'):
        score += 0.1

    # Tag overlap (weight 0.3)
    weights += 0.3
    tags_a = set(ep_a.get('tags') or [])
    tags_b = set(ep_b.get('tags') or [])
    if tags_a and tags_b:
        overlap = len(tags_a & tags_b) / max(len(tags_a | tags_b), 1)
        score += 0.3 * overlap
    elif not tags_a and not tags_b:
        pass  # both empty — no signal

    # Title word overlap (weight 0.3)
    weights += 0.3
    words_a = _title_words(ep_a.get('title', ''))
    words_b = _title_words(ep_b.get('title', ''))
    if words_a and words_b:
        word_overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
        score += 0.3 * word_overlap

    return score / weights if weights else 0.0


def _cluster_episodes(episodes: list) -> list:
    """Group similar rejected episodes into clusters.

    Simple single-linkage clustering — episodes above SIMILARITY_THRESHOLD
    join the same cluster.

    Returns list of clusters, each a list of episode dicts.
    """
    if not episodes:
        return []

    assigned = [False] * len(episodes)
    clusters = []

    for i, ep_a in enumerate(episodes):
        if assigned[i]:
            continue

        cluster = [ep_a]
        assigned[i] = True

        for j in range(i + 1, len(episodes)):
            if assigned[j]:
                continue
            if _episode_similarity(ep_a, episodes[j]) >= SIMILARITY_THRESHOLD:
                cluster.append(episodes[j])
                assigned[j] = True

        clusters.append(cluster)

    return clusters


def detect_rejected_patterns(since_days: int = 30) -> dict:
    """Scan rejected episodes for recurring patterns.

    When a cluster of similar rejected episodes crosses the recurrence
    threshold, creates:
      1. A pattern Episode (approved, enters the feed)
      2. An AliceObservation (notifies administrators)

    Args:
        since_days: Look back this many days for rejected episodes.

    Returns summary of what was found and created.
    """
    from apps.ai_assistant.models import Episode
    from apps.ai_assistant.models.alice import AliceObservation

    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (since_days * 86400 * 1000)

    rejected = Episode.objects.filter(
        review_status='rejected',
        dt_created__gte=since_ms,
        is_active=True,
    ).values(
        'episode_id', 'episode_type', 'domain', 'title',
        'narrative', 'principle', 'tags', 'review_note',
        'source_instance', 'dt_created',
    )

    rejected_list = list(rejected)
    if not rejected_list:
        return {'clusters_found': 0, 'patterns_created': 0, 'observations_created': 0}

    clusters = _cluster_episodes(rejected_list)
    patterns_created = 0
    observations_created = 0
    clusters_found = 0

    for cluster in clusters:
        if len(cluster) < RECURRENCE_THRESHOLD:
            continue

        clusters_found += 1

        # Check if we already created a pattern for this cluster
        # Use a hash of the cluster's common domain + title words
        common_domain = Counter(ep.get('domain', 'CROSS') for ep in cluster).most_common(1)[0][0]
        all_title_words = set()
        for ep in cluster:
            all_title_words |= _title_words(ep.get('title', ''))
        # Top 5 most common words across the cluster
        word_counts = Counter()
        for ep in cluster:
            word_counts.update(_title_words(ep.get('title', '')))
        common_words = [w for w, _ in word_counts.most_common(5)]
        cluster_key = f"rejected-pattern-{common_domain}-{'-'.join(sorted(common_words[:3]))}"
        cluster_hash = hashlib.md5(cluster_key.encode()).hexdigest()[:12]
        pattern_episode_id = f"EP-{cluster_hash}"

        # Skip if pattern already exists
        if Episode.objects.filter(episode_id=pattern_episode_id).exists():
            continue

        # Collect source instances
        source_instances = set()
        for ep in cluster:
            si = ep.get('source_instance')
            if si:
                source_instances.add(str(si))

        # Build narrative from the cluster
        sample_titles = [ep.get('title', '')[:100] for ep in cluster[:5]]
        sample_notes = [ep.get('review_note', '') for ep in cluster if ep.get('review_note')][:3]

        narrative = (
            f"Recurring pattern detected: {len(cluster)} rejected episodes "
            f"with similar characteristics in domain [{common_domain}].\n\n"
            f"Common themes: {', '.join(common_words)}\n\n"
            f"Sample episodes:\n"
            + '\n'.join(f"  - {t}" for t in sample_titles)
        )
        if sample_notes:
            narrative += '\n\nReview notes:\n' + '\n'.join(f"  - {n[:200]}" for n in sample_notes)

        if len(source_instances) > 1:
            narrative += f"\n\nAppears across {len(source_instances)} instances."

        # Create the pattern episode — approved, enters the feed
        Episode.objects.create(
            episode_id=pattern_episode_id,
            episode_type='pattern',
            domain=common_domain,
            title=f"Recurring rejected pattern: {' '.join(common_words[:4])}",
            narrative=narrative,
            principle=(
                f"This class of episode keeps being created and rejected. "
                f"The recurrence across {len(cluster)} episodes "
                f"{'from ' + str(len(source_instances)) + ' instances ' if len(source_instances) > 1 else ''}"
                f"suggests a systemic cause — investigate why this "
                f"misconception or error keeps surfacing."
            ),
            actors=['alice'],
            outcome='ongoing',
            severity='lesson',
            tags=list(common_words) + ['recurring-pattern', 'rejected-cluster'],
            source_ref=f"pattern:{cluster_key}",
            review_status='approved',
            reviewed_by='alice',
            dt_reviewed=now_ms,
            quality_score=0.5,
            related_episodes=[ep['episode_id'] for ep in cluster],
            dt_created=now_ms,
            dt_modified=now_ms,
        )
        patterns_created += 1

        # Notify administrators via AliceObservation
        AliceObservation.objects.create(
            category='pattern',
            source='alice',
            priority=1,
            message=(
                f"Recurring rejected episode pattern in [{common_domain}]: "
                f"{len(cluster)} similar episodes rejected. "
                f"Common themes: {', '.join(common_words)}."
            ),
            detail=narrative,
            model_name='Episode',
            dedup_key=f"ep-pattern-{cluster_hash}",
        )
        observations_created += 1

        logger.info(
            "Created pattern episode %s from %d rejected episodes in %s",
            pattern_episode_id, len(cluster), common_domain,
        )

    return {
        'rejected_scanned': len(rejected_list),
        'clusters_found': clusters_found,
        'patterns_created': patterns_created,
        'observations_created': observations_created,
    }


# ── Admin Summary ─────────────────────────────────────────────────────

def get_episode_summary(period_days: int = 7) -> dict:
    """Episode summary for the admin console.

    Answers three questions:
      1. What do we have? (counts by type, status, severity)
      2. What's new? (this period, local vs harvested)
      3. What's recurring? (pattern clusters needing attention)

    Args:
        period_days: "New" = created within this many days.

    Returns dict for the admin dashboard.
    """
    from apps.ai_assistant.models import Episode
    from django.db.models import Count, Q

    now_ms = int(time.time() * 1000)
    period_start = now_ms - (period_days * 86400 * 1000)
    instance_uuid = None
    try:
        from apps.core.models import Setting
        company = Setting.objects.filter(
            purpose='wc:company_profile', is_active=True,
        ).first()
        if company and company.uuid:
            instance_uuid = company.uuid
    except Exception:
        pass

    # Total counts
    total = Episode.objects.filter(is_active=True).count()

    # By type
    by_type = dict(
        Episode.objects.filter(is_active=True)
        .values_list('episode_type')
        .annotate(n=Count('id'))
    )

    # By review status
    by_review = dict(
        Episode.objects.filter(is_active=True)
        .values_list('review_status')
        .annotate(n=Count('id'))
    )

    # By severity
    by_severity = dict(
        Episode.objects.filter(is_active=True)
        .values_list('severity')
        .annotate(n=Count('id'))
    )

    # New this period
    new_total = Episode.objects.filter(
        is_active=True, dt_created__gte=period_start,
    ).count()

    # Local vs harvested (local = source_instance matches this instance)
    if instance_uuid:
        new_local = Episode.objects.filter(
            is_active=True, dt_created__gte=period_start,
            source_instance=instance_uuid,
        ).count()
        # Also count episodes with no source_instance (created locally before sync)
        new_local += Episode.objects.filter(
            is_active=True, dt_created__gte=period_start,
            source_instance__isnull=True,
        ).count()
    else:
        new_local = new_total

    new_harvested = new_total - new_local

    # Pending review
    pending_review = Episode.objects.filter(
        is_active=True,
        review_status__in=('raw', 'pending'),
    ).count()

    # Top domains this period
    top_domains = list(
        Episode.objects.filter(
            is_active=True, dt_created__gte=period_start,
        )
        .values('domain')
        .annotate(n=Count('id'))
        .order_by('-n')[:5]
    )

    # Recent patterns (episodes of type 'pattern' that are recurring signals)
    recent_patterns = list(
        Episode.objects.filter(
            is_active=True,
            episode_type='pattern',
            dt_created__gte=period_start,
        )
        .values('episode_id', 'title', 'domain', 'quality_score', 'dt_created')
        .order_by('-dt_created')[:5]
    )

    # Most recalled (what the team keeps coming back to)
    most_recalled = list(
        Episode.objects.filter(
            is_active=True,
            recall_count__gt=0,
        )
        .values('episode_id', 'title', 'domain', 'recall_count', 'severity')
        .order_by('-recall_count')[:5]
    )

    return {
        'total': total,
        'period_days': period_days,
        'by_type': by_type,
        'by_review_status': by_review,
        'by_severity': by_severity,
        'new_this_period': {
            'total': new_total,
            'local': new_local,
            'harvested': new_harvested,
        },
        'pending_review': pending_review,
        'top_domains': top_domains,
        'recent_patterns': recent_patterns,
        'most_recalled': most_recalled,
    }
