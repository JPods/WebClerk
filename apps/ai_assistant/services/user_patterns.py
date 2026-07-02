"""
User Pattern Detection — Alice watches how users work and coaches.

Tracks navigation patterns (which models users view, in what order, how often)
and suggests improvements: combined dashboards, shortcuts, training.

Stores observations in contact.metadata.alice_observations and navigation
history in contact.metadata.navigation_log.
"""
from __future__ import annotations

import time
from collections import Counter
from itertools import groupby

from django.apps import apps as dj_apps


def _now_ms():
    return int(time.time() * 1000)


def log_user_navigation(contact_id: int, entries: list[dict]) -> dict:
    """Record navigation entries for a user.

    Called from the frontend — batched model view events.
    Stores in contact.metadata.navigation_log (rolling window, last 500).

    Args:
        contact_id: Contact PK
        entries: [{model: str, dt: epoch_ms}, ...]

    Returns: {logged: int}
    """
    Contact = dj_apps.get_model('core', 'Contact')
    try:
        contact = Contact.objects.get(pk=contact_id)
    except Contact.DoesNotExist:
        return {'logged': 0, 'error': 'Contact not found'}

    metadata = contact.metadata or {}
    nav_log = metadata.get('navigation_log', [])

    for entry in entries:
        nav_log.append({
            'model': entry.get('model', ''),
            'dt': entry.get('dt', _now_ms()),
        })

    # Rolling window — keep last 500 entries
    if len(nav_log) > 500:
        nav_log = nav_log[-500:]

    metadata['navigation_log'] = nav_log
    Contact.objects.filter(pk=contact_id).update(metadata=metadata, dt_modified=_now_ms())

    return {'logged': len(entries)}


def analyze_user_patterns(contact_id: int) -> dict:
    """Analyze a user's navigation patterns and generate coaching suggestions.

    Looks for:
    1. Frequent model sequences (A→B→C visited repeatedly)
    2. Most-used models (where they spend time)
    3. Unused features (models never visited)
    4. Time-of-day patterns

    Returns: {
        frequent_sequences: [{sequence, count, suggestion}],
        top_models: [{model, count, pct}],
        suggestions: [str],
    }
    """
    Contact = dj_apps.get_model('core', 'Contact')
    try:
        contact = Contact.objects.get(pk=contact_id)
    except Contact.DoesNotExist:
        return {'error': 'Contact not found'}

    metadata = contact.metadata or {}
    nav_log = metadata.get('navigation_log', [])

    if len(nav_log) < 10:
        return {'suggestions': ['Not enough navigation data yet — need at least 10 model views.'], 'frequent_sequences': [], 'top_models': []}

    # 1. Top models by frequency
    model_counts = Counter(e['model'] for e in nav_log)
    total = sum(model_counts.values())
    top_models = [
        {'model': m, 'count': c, 'pct': round(c / total * 100, 1)}
        for m, c in model_counts.most_common(10)
    ]

    # 2. Frequent sequences (pairs and triples)
    models = [e['model'] for e in nav_log]
    # Remove consecutive duplicates (staying on same model isn't a sequence)
    deduped = [k for k, _ in groupby(models)]

    pair_counts = Counter()
    triple_counts = Counter()
    for i in range(len(deduped) - 1):
        pair_counts[(deduped[i], deduped[i + 1])] += 1
    for i in range(len(deduped) - 2):
        triple_counts[(deduped[i], deduped[i + 1], deduped[i + 2])] += 1

    frequent_sequences = []
    for seq, count in triple_counts.most_common(5):
        if count >= 3:  # seen at least 3 times
            frequent_sequences.append({
                'sequence': list(seq),
                'count': count,
                'suggestion': f'You frequently view {seq[0]} → {seq[1]} → {seq[2]}. Consider a combined dashboard with all three.',
            })

    for seq, count in pair_counts.most_common(5):
        if count >= 5 and not any(set(seq).issubset(set(fs['sequence'])) for fs in frequent_sequences):
            frequent_sequences.append({
                'sequence': list(seq),
                'count': count,
                'suggestion': f'You often go from {seq[0]} to {seq[1]}. Consider adding a quick-link or split view.',
            })

    # 3. Generate suggestions
    suggestions = []

    # Suggest dashboard if 3+ models visited frequently together
    if frequent_sequences:
        all_freq_models = set()
        for fs in frequent_sequences:
            all_freq_models.update(fs['sequence'])
        if len(all_freq_models) >= 3:
            suggestions.append(
                f'Alice recommends a custom dashboard combining: {", ".join(sorted(all_freq_models))}. '
                f'You visit these models together {sum(fs["count"] for fs in frequent_sequences)} times.'
            )

    # Suggest training if user rarely uses certain transaction types
    tx_models = {'order', 'invoice', 'proposal', 'purchase', 'payment'}
    used_tx = tx_models.intersection(model_counts.keys())
    unused_tx = tx_models - used_tx
    if unused_tx and len(nav_log) > 50:
        suggestions.append(
            f'You haven\'t used: {", ".join(sorted(unused_tx))}. '
            f'Training available — search Help for these topics.'
        )

    # Suggest if user views the same record type > 40% of the time
    if top_models and top_models[0]['pct'] > 40:
        m = top_models[0]
        suggestions.append(
            f'{m["model"]} is {m["pct"]}% of your navigation. '
            f'Consider pinning it or making it your default landing page.'
        )

    return {
        'frequent_sequences': frequent_sequences,
        'top_models': top_models,
        'suggestions': suggestions,
        'total_views': total,
        'unique_models': len(model_counts),
    }


def get_all_user_patterns() -> list[dict]:
    """Analyze patterns for all active users. Alice's batch analysis."""
    Contact = dj_apps.get_model('core', 'Contact')
    results = []

    contacts = Contact.objects.filter(
        is_active=True,
        metadata__navigation_log__isnull=False,
    ).exclude(metadata__navigation_log=[])

    for contact in contacts:
        nav_log = (contact.metadata or {}).get('navigation_log', [])
        if len(nav_log) < 10:
            continue
        analysis = analyze_user_patterns(contact.pk)
        if analysis.get('suggestions'):
            results.append({
                'contact_id': contact.pk,
                'name': f'{contact.name_first} {contact.name_last}'.strip() or contact.email or f'Contact #{contact.pk}',
                'analysis': analysis,
            })

    return results


def log_user_search(contact_id: int, model: str, search_term: str, result_count: int = 0) -> dict:
    """Record a search for a user.

    Stored in contact.metadata.search_log (rolling 200).
    When Alice analyzes, searches used by multiple users get promoted to presets.

    Args:
        contact_id: Contact PK
        model: model being searched
        search_term: what the user typed
        result_count: how many results came back
    """
    Contact = dj_apps.get_model('core', 'Contact')
    try:
        contact = Contact.objects.get(pk=contact_id)
    except Contact.DoesNotExist:
        return {'logged': False}

    metadata = contact.metadata or {}
    search_log = metadata.get('search_log', [])
    search_log.append({
        'model': model,
        'term': search_term,
        'results': result_count,
        'dt': _now_ms(),
    })

    if len(search_log) > 200:
        search_log = search_log[-200:]

    metadata['search_log'] = search_log
    Contact.objects.filter(pk=contact_id).update(metadata=metadata, dt_modified=_now_ms())
    return {'logged': True}


def analyze_search_patterns() -> dict:
    """Find searches used by multiple users — candidates for presets.

    Walks all contacts' search_log, groups by (model, term), counts unique users.
    Searches used by 2+ users become preset candidates.

    Returns: {
        preset_candidates: [{model, term, user_count, total_uses, avg_results}],
        per_user: [{contact_id, name, top_searches: [{model, term, count}]}],
    }
    """
    Contact = dj_apps.get_model('core', 'Contact')
    contacts = Contact.objects.filter(is_active=True)

    # {(model, term): {users: set, total: int, results_sum: int}}
    global_searches: dict[tuple, dict] = {}
    per_user = []

    for contact in contacts:
        search_log = (contact.metadata or {}).get('search_log', [])
        if not search_log:
            continue

        user_searches = Counter()
        for entry in search_log:
            model = entry.get('model', '')
            term = entry.get('term', '').strip().lower()
            if not term or len(term) < 2:
                continue

            key = (model, term)
            user_searches[key] += 1

            if key not in global_searches:
                global_searches[key] = {'users': set(), 'total': 0, 'results_sum': 0}
            global_searches[key]['users'].add(contact.pk)
            global_searches[key]['total'] += 1
            global_searches[key]['results_sum'] += entry.get('results', 0)

        if user_searches:
            top = user_searches.most_common(5)
            per_user.append({
                'contact_id': contact.pk,
                'name': f'{contact.name_first} {contact.name_last}'.strip() or contact.email or f'#{contact.pk}',
                'top_searches': [{'model': k[0], 'term': k[1], 'count': c} for k, c in top],
            })

    # Preset candidates — used by 2+ users, or 5+ times by one user
    candidates = []
    for (model, term), data in global_searches.items():
        user_count = len(data['users'])
        total = data['total']
        avg_results = round(data['results_sum'] / total, 1) if total else 0

        if user_count >= 2 or total >= 5:
            candidates.append({
                'model': model,
                'term': term,
                'user_count': user_count,
                'total_uses': total,
                'avg_results': avg_results,
            })

    candidates.sort(key=lambda x: (x['user_count'], x['total_uses']), reverse=True)

    return {
        'preset_candidates': candidates[:20],
        'per_user': per_user,
    }


def promote_search_preset(model: str, term: str, label: str = '') -> dict:
    """Promote a search to a shared preset. Stored in a Setting record.

    Presets are available to all users as quick-search buttons.
    """
    Setting = dj_apps.get_model('core', 'Setting')
    setting_name = 'search_presets'

    setting = Setting.objects.filter(name=setting_name, is_active=True).first()
    if not setting:
        setting = Setting.objects.create(
            name=setting_name,
            data={'presets': []},
        )

    data = setting.data or {}
    presets = data.get('presets', [])

    # Don't duplicate
    for p in presets:
        if p.get('model') == model and p.get('term', '').lower() == term.lower():
            return {'already_exists': True}

    presets.append({
        'model': model,
        'term': term,
        'label': label or f'{model}: {term}',
        'dt_promoted': _now_ms(),
        'source': 'alice_pattern_detection',
    })

    data['presets'] = presets
    Setting.objects.filter(pk=setting.pk).update(data=data, dt_modified=_now_ms())

    return {'promoted': True, 'preset_count': len(presets)}


def infer_frequency(timestamps: list[int]) -> str:
    """Infer usage frequency from a list of epoch-ms timestamps.

    Returns: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', or 'sporadic'
    """
    if len(timestamps) < 2:
        return 'sporadic'

    sorted_ts = sorted(timestamps)
    gaps_days = [(sorted_ts[i + 1] - sorted_ts[i]) / 86400000 for i in range(len(sorted_ts) - 1)]
    avg_gap = sum(gaps_days) / len(gaps_days)

    if avg_gap < 2:
        return 'daily'
    elif avg_gap < 10:
        return 'weekly'
    elif avg_gap < 45:
        return 'monthly'
    elif avg_gap < 120:
        return 'quarterly'
    elif avg_gap < 400:
        return 'yearly'
    return 'sporadic'


def prune_user_metadata(contact_id: int = None, max_age_days: int = 90) -> dict:
    """Prune old navigation/search entries from contact metadata.

    Run as part of Alice's scheduled housekeeping.
    If contact_id is None, prunes all contacts.

    Rules:
    - navigation_log entries older than max_age_days → pruned
    - search_log entries older than max_age_days → pruned UNLESS promoted=True
    - alice_observations acknowledged and older than 30 days → pruned

    Before pruning searches, checks frequency. If a search is infrequent but
    periodic (yearly, quarterly), Alice offers to promote it instead of pruning.
    """
    Contact = dj_apps.get_model('core', 'Contact')
    cutoff_ms = _now_ms() - (max_age_days * 86400 * 1000)
    obs_cutoff_ms = _now_ms() - (30 * 86400 * 1000)

    if contact_id:
        contacts = Contact.objects.filter(pk=contact_id)
    else:
        contacts = Contact.objects.filter(is_active=True)

    pruned_count = 0
    promote_candidates = []

    for contact in contacts:
        metadata = contact.metadata or {}
        changed = False

        # Prune navigation log
        nav_log = metadata.get('navigation_log', [])
        if nav_log:
            before = len(nav_log)
            nav_log = [e for e in nav_log if e.get('dt', 0) > cutoff_ms]
            if len(nav_log) != before:
                metadata['navigation_log'] = nav_log
                changed = True

        # Prune search log — but detect periodic patterns first
        search_log = metadata.get('search_log', [])
        if search_log:
            # Group by (model, term) to detect periodic searches
            from collections import defaultdict
            grouped: dict[tuple, list] = defaultdict(list)
            for e in search_log:
                key = (e.get('model', ''), e.get('term', '').strip().lower())
                grouped[key].append(e.get('dt', 0))

            keep = []
            for entry in search_log:
                # Always keep promoted entries
                if entry.get('promoted'):
                    keep.append(entry)
                    continue
                # Keep entries within cutoff
                if entry.get('dt', 0) > cutoff_ms:
                    keep.append(entry)
                    continue
                # Old entry — check if it's periodic before dropping
                key = (entry.get('model', ''), entry.get('term', '').strip().lower())
                freq = infer_frequency(grouped.get(key, []))
                if freq in ('yearly', 'quarterly'):
                    # Don't prune — flag for promotion instead
                    entry['_frequency'] = freq
                    keep.append(entry)
                    promote_candidates.append({
                        'contact_id': contact.pk,
                        'model': key[0],
                        'term': key[1],
                        'frequency': freq,
                        'suggestion': f'Search "{key[1]}" in {key[0]} is used {freq} — promote to permanent preset?',
                    })
                # else: drop it (sporadic old entry)

            if len(keep) != len(search_log):
                metadata['search_log'] = keep
                changed = True

        # Prune acknowledged observations older than 30 days
        observations = metadata.get('alice_observations', [])
        if observations:
            before = len(observations)
            observations = [o for o in observations
                          if not (o.get('acknowledged') and o.get('dt', 0) < obs_cutoff_ms)]
            if len(observations) != before:
                metadata['alice_observations'] = observations
                changed = True

        if changed:
            Contact.objects.filter(pk=contact.pk).update(metadata=metadata, dt_modified=_now_ms())
            pruned_count += 1

    return {
        'contacts_pruned': pruned_count,
        'promote_candidates': promote_candidates,
    }


def save_alice_observation(contact_id: int, observation: str, category: str = 'workflow') -> dict:
    """Save an Alice observation to the user's contact record.

    Stored in contact.metadata.alice_observations[].
    """
    Contact = dj_apps.get_model('core', 'Contact')
    try:
        contact = Contact.objects.get(pk=contact_id)
    except Contact.DoesNotExist:
        return {'error': 'Contact not found'}

    metadata = contact.metadata or {}
    observations = metadata.get('alice_observations', [])
    observations.append({
        'dt': _now_ms(),
        'category': category,
        'observation': observation,
        'acknowledged': False,
    })

    # Keep last 50 observations
    if len(observations) > 50:
        observations = observations[-50:]

    metadata['alice_observations'] = observations
    Contact.objects.filter(pk=contact_id).update(metadata=metadata, dt_modified=_now_ms())

    return {'saved': True, 'observation_count': len(observations)}
