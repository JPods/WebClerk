"""
Episode Bundle — telemetry-style episode exchange across WC3 instances.

Episodes flow like telemetry pings — published and generally available.
Each WC3 instance creates episodes locally. WCHQ harvests all episodes
from connected instances. Athena + Allie review them (some will be
foolish). Reviewed episodes become available in the feed. Other
instances poll the feed and ingest what's relevant.

    Any instance creates episode
            ↓
    WCHQ harvests (pulls from all connected instances)
            ↓
    Athena + Allie review (grade, filter)
            ↓
    Approved episodes available in feed
            ↓
    Other instances pick up what's useful

Three services:
    build_episode_feed()   — serve this instance's episodes (feed endpoint)
    harvest_episodes()     — WCHQ pulls episodes from a connected instance
    ingest_episodes()      — upsert incoming episodes into local database
    build_episode_bundle() — package local episodes for harvest

UUID is the cross-database identity. episode_id (EP-{hash}) is the
natural key for dedup. source_instance UUID stamps origin.
"""
import logging
import time
import uuid as uuid_lib

logger = logging.getLogger(__name__)


def _get_instance_uuid() -> str:
    """Get this installation's UUID from Setting(purpose='wc:company_profile')."""
    try:
        from apps.core.models import Setting
        company = Setting.objects.filter(
            purpose='wc:company_profile', is_active=True,
        ).first()
        if company and company.uuid:
            return str(company.uuid)
    except Exception:
        pass
    return ''


def _scrub_actors(actors: list) -> list:
    """Remove PII from actors list before episodes leave the instance.

    Keeps role identifiers (alice, claude, noelle) but strips
    customer/contact names. Everything unrecognized becomes 'user'.
    """
    safe_actors = {
        'alice', 'allie', 'claude', 'noelle', 'natalie', 'nora',
        'sally', 'athena', 'bill', 'system',
    }
    scrubbed = []
    for actor in (actors or []):
        name = str(actor).strip().lower()
        if name in safe_actors:
            scrubbed.append(actor)
        else:
            scrubbed.append('user')
    return scrubbed


# ── Feed: serve this instance's episodes ──────────────────────────────

def build_episode_feed(since_ms: int = 0, only_approved: bool = False,
                       limit: int = 200) -> dict:
    """Build the episode feed — what this instance publishes.

    For WCHQ, only_approved=True serves the reviewed/approved feed.
    For any instance, only_approved=False serves all local episodes
    (WCHQ will review them after harvest).

    Args:
        since_ms: Only episodes created after this timestamp (epoch ms).
        only_approved: If True, only serve reviewed+approved episodes.
        limit: Max episodes per response.

    Returns a dict — the feed payload.
    """
    from apps.ai_assistant.models import Episode

    instance_uuid = _get_instance_uuid()

    qs = Episode.objects.filter(is_active=True)
    if since_ms:
        qs = qs.filter(dt_created__gte=since_ms)
    if only_approved:
        qs = qs.filter(review_status='approved')

    qs = qs.order_by('dt_created')[:limit]

    episodes = []
    for ep in qs.values(
        'uuid', 'episode_id', 'episode_type', 'domain', 'title',
        'narrative', 'principle', 'actors', 'outcome', 'severity',
        'related_episodes', 'tags', 'source_ref',
        'recall_count', 'dt_start', 'dt_end', 'dt_created',
        'source_instance', 'review_status', 'quality_score',
    ):
        ep['actors'] = _scrub_actors(ep.get('actors'))
        # Stamp origin if not set
        if not ep.get('source_instance'):
            ep['source_instance'] = instance_uuid
        # Ensure uuid is string for JSON
        if ep.get('uuid'):
            ep['uuid'] = str(ep['uuid'])
        if ep.get('source_instance'):
            ep['source_instance'] = str(ep['source_instance'])
        episodes.append(ep)

    return {
        'type': 'episode_feed',
        'version': '1.0',
        'source_instance': instance_uuid,
        'dt_built': int(time.time() * 1000),
        'since_ms': since_ms,
        'only_approved': only_approved,
        'episodes': episodes,
        'count': len(episodes),
    }


# ── Harvest: WCHQ pulls episodes from a connected instance ───────────

def harvest_episodes(connection) -> dict:
    """WCHQ harvests episodes from a connected instance.

    Calls the instance's feed endpoint, ingests the response.
    Harvested episodes arrive as review_status='raw' — Athena
    and Allie review them before they enter the approved feed.

    Args:
        connection: Connection record for the instance to harvest from.

    Returns summary dict.
    """
    import httpx

    config = connection.config if isinstance(connection.config, dict) else {}
    endpoint = config.get('endpoint', '')
    key = config.get('key', '')

    if not endpoint or not key:
        raise ValueError(
            f"Connection {connection.ida} missing endpoint or key in config"
        )

    # Get last harvest timestamp from connection metadata
    last_harvest = 0
    if isinstance(config, dict):
        last_harvest = config.get('last_episode_harvest_ms', 0)

    url = endpoint.rstrip('/') + '/wcapi/episodes/feed/'

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                url,
                headers={'Authorization': f'Athena {config.get("athena_token", key)}'},
                params={'since_ms': last_harvest},
            )
            resp.raise_for_status()
            feed = resp.json()

    except httpx.ConnectError:
        raise ConnectionError(f"Cannot reach instance at {endpoint}")
    except Exception as e:
        logger.exception("Episode harvest failed for %s", connection.name)
        raise ConnectionError(f"Harvest error: {e}")

    # Ingest the episodes
    result = ingest_episodes(feed.get('episodes', []), review_status='raw')

    # Update last harvest timestamp on connection
    try:
        config['last_episode_harvest_ms'] = int(time.time() * 1000)
        connection.config = config
        connection.save(update_fields=['config'])
    except Exception:
        pass

    return result


# ── Ingest: upsert episodes into local database ──────────────────────

def ingest_episodes(episodes: list, review_status: str = 'raw') -> dict:
    """Upsert episodes into the local Episode table.

    Dedup by episode_id (natural key). Existing episodes updated only
    if incoming dt_created is newer. New episodes get the specified
    review_status (raw for harvested, approved for feed pulls).

    Args:
        episodes: List of episode dicts.
        review_status: Initial review_status for new episodes.

    Returns summary dict.
    """
    from apps.ai_assistant.models import Episode

    if not episodes:
        return {'created': 0, 'updated': 0, 'skipped': 0}

    created = 0
    updated = 0
    skipped = 0
    now_ms = int(time.time() * 1000)

    for ep_data in episodes:
        episode_id = ep_data.get('episode_id', '')
        if not episode_id:
            skipped += 1
            continue

        # Parse source_instance as UUID if present
        source_inst = ep_data.get('source_instance')
        if source_inst:
            try:
                source_inst = uuid_lib.UUID(str(source_inst))
            except (ValueError, AttributeError):
                source_inst = None

        try:
            existing = Episode.objects.filter(episode_id=episode_id).first()

            if existing:
                incoming_dt = ep_data.get('dt_created', 0)
                if incoming_dt > existing.dt_created:
                    for field in (
                        'episode_type', 'domain', 'title', 'narrative',
                        'principle', 'actors', 'outcome', 'severity',
                        'related_episodes', 'tags', 'source_ref',
                        'dt_start', 'dt_end',
                    ):
                        val = ep_data.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                    if source_inst:
                        existing.source_instance = source_inst
                    # Recall count: keep the higher value
                    incoming_recall = ep_data.get('recall_count', 0)
                    if incoming_recall > existing.recall_count:
                        existing.recall_count = incoming_recall
                    # Don't overwrite review status on update —
                    # once reviewed, it stays reviewed
                    existing.dt_modified = now_ms
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                Episode.objects.create(
                    episode_id=episode_id,
                    episode_type=ep_data.get('episode_type', 'pattern'),
                    domain=ep_data.get('domain', 'CROSS'),
                    title=ep_data.get('title', '(untitled)')[:200],
                    narrative=ep_data.get('narrative', ''),
                    principle=ep_data.get('principle', ''),
                    actors=ep_data.get('actors', []),
                    outcome=ep_data.get('outcome', 'unresolved'),
                    severity=ep_data.get('severity', 'lesson'),
                    related_episodes=ep_data.get('related_episodes', []),
                    tags=ep_data.get('tags', []),
                    source_ref=ep_data.get('source_ref', ''),
                    recall_count=ep_data.get('recall_count', 0),
                    dt_start=ep_data.get('dt_start', 0),
                    dt_end=ep_data.get('dt_end', 0),
                    source_instance=source_inst,
                    review_status=review_status,
                    dt_created=ep_data.get('dt_created', now_ms),
                    dt_modified=now_ms,
                )
                created += 1

        except Exception as e:
            logger.warning("Episode upsert failed for %s: %s", episode_id, e)
            skipped += 1

    logger.info(
        "Episode ingest: %d created, %d updated, %d skipped",
        created, updated, skipped,
    )
    return {'created': created, 'updated': updated, 'skipped': skipped}


# ── Legacy compat: receive_episodes called by BundleReceiveView ──────

def receive_episodes(payload: dict) -> dict:
    """Handle episode bundles arriving via /wcapi/sync/receive/.

    Delegates to ingest_episodes. Episodes arrive as 'raw' and
    need review before entering the feed.
    """
    return ingest_episodes(payload.get('episodes', []), review_status='raw')
