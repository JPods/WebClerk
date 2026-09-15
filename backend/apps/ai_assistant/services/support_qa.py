"""Support Q&A — search, ask, score, escalate.

The question lifecycle:
  1. search_qa: find existing answers by keyword (full-text search on Documents)
  2. ask_qa: create a new question if no match (status=draft, awaits answer)
  3. answer_qa: answer a draft question (status=published)
  4. score_qa: user rates an answer 1-5
  5. escalate_qa: mark question as needing Bill (source=bill_question)

All Q&A lives in Document records with config.purpose='support_qa'.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def search_qa(params: dict[str, Any]) -> dict[str, Any]:
    """Search existing Q&A by keyword. Returns matches sorted by score."""
    from apps.docs.models.document import Document

    query = params.get('query', '').strip()
    limit = int(params.get('limit', 10))

    if not query:
        return {'results': [], 'count': 0}

    qs = Document.objects.filter(
        config__purpose='support_qa',
        status='published',
    )

    # Full-text search on name (question) + body (answer)
    from django.contrib.postgres.search import SearchQuery, SearchRank
    search_query = SearchQuery(query, search_type='websearch')
    qs = qs.filter(search_vector=search_query)
    qs = qs.annotate(rank=SearchRank('search_vector', search_query))
    qs = qs.order_by('-rank')[:limit]

    results = []
    for doc in qs:
        cfg = doc.config or {}
        results.append({
            'id': doc.id,
            'ida': doc.ida,
            'question': doc.name,
            'answer_preview': (doc.body or '')[:300],
            'score_avg': cfg.get('score_avg', 0),
            'score_count': cfg.get('score_count', 0),
            'source': cfg.get('source', ''),
            'rank': float(doc.rank) if hasattr(doc, 'rank') else 0,
        })

    return {'results': results, 'count': len(results), 'query': query}


def ask_qa(params: dict[str, Any]) -> dict[str, Any]:
    """Create a new Q&A question. Status=draft until answered."""
    from apps.docs.models.document import Document

    question = params.get('question', '').strip()
    if not question:
        raise ValueError('question is required')

    asked_by = params.get('asked_by', 'user')
    context = params.get('context', '')
    now = datetime.now(timezone.utc).isoformat()

    doc = Document.objects.create(
        name=question,
        description=context[:255] if context else '',
        status='draft',
        config={
            'purpose': 'support_qa',
            'source': 'user',
            'asked_by': asked_by,
            'dt_asked': now,
            'dt_answered': None,
            'answered_by': None,
            'score_count': 0,
            'score_sum': 0,
            'score_avg': 0,
            'escalation_chain': [],
            'keywords': [],
        },
        refs={'tags': ['support', 'qa']},
    )

    return {
        'id': doc.id,
        'ida': doc.ida,
        'question': doc.name,
        'status': doc.status,
        'message': 'Question created. Alice, Claude, and Bill will review.',
    }


def answer_qa(params: dict[str, Any]) -> dict[str, Any]:
    """Answer an existing Q&A question. Sets status=published."""
    from apps.docs.models.document import Document

    doc_id = params.get('document_id')
    answer = params.get('answer', '').strip()
    answered_by = params.get('answered_by', 'unknown')

    if not doc_id or not answer:
        raise ValueError('document_id and answer are required')

    doc = Document.objects.get(pk=doc_id)
    cfg = doc.config or {}
    if cfg.get('purpose') != 'support_qa':
        raise ValueError('Document is not a support Q&A record')

    doc.body = answer
    doc.status = 'published'
    cfg['dt_answered'] = datetime.now(timezone.utc).isoformat()
    cfg['answered_by'] = answered_by
    doc.config = cfg
    doc.save()

    return {
        'id': doc.id,
        'ida': doc.ida,
        'status': 'published',
        'answered_by': answered_by,
    }


def score_qa(params: dict[str, Any]) -> dict[str, Any]:
    """Score an answered Q&A. Accumulates running average."""
    from apps.docs.models.document import Document

    doc_id = params.get('document_id')
    score = int(params.get('score', 0))

    if not doc_id or score < 1 or score > 5:
        raise ValueError('document_id and score (1-5) are required')

    doc = Document.objects.get(pk=doc_id)
    cfg = doc.config or {}
    if cfg.get('purpose') != 'support_qa':
        raise ValueError('Document is not a support Q&A record')

    cfg['score_count'] = cfg.get('score_count', 0) + 1
    cfg['score_sum'] = cfg.get('score_sum', 0) + score
    cfg['score_avg'] = round(cfg['score_sum'] / cfg['score_count'], 2)

    # If score drops below 2.0 after 3+ ratings, flag for review
    if cfg['score_avg'] < 2.0 and cfg['score_count'] >= 3:
        doc.status = 'needs_review'

    doc.config = cfg
    doc.save()

    return {
        'id': doc.id,
        'score_avg': cfg['score_avg'],
        'score_count': cfg['score_count'],
        'status': doc.status,
    }


def escalate_qa(params: dict[str, Any]) -> dict[str, Any]:
    """Escalate a question — Alice/Claude couldn't answer, needs Bill."""
    from apps.docs.models.document import Document

    doc_id = params.get('document_id')
    escalated_by = params.get('escalated_by', 'unknown')
    reason = params.get('reason', '')

    if not doc_id:
        raise ValueError('document_id is required')

    doc = Document.objects.get(pk=doc_id)
    cfg = doc.config or {}
    if cfg.get('purpose') != 'support_qa':
        raise ValueError('Document is not a support Q&A record')

    chain = cfg.get('escalation_chain', [])
    chain.append({
        'agent': escalated_by,
        'reason': reason,
        'dt': datetime.now(timezone.utc).isoformat(),
    })
    cfg['escalation_chain'] = chain
    doc.config = cfg
    doc.save()

    # Auto-post to WCHQ so the whole team can see and answer
    try:
        wchq_result = post_qa_to_wchq({'document_id': doc.id})
        chain[-1]['wchq_posted'] = wchq_result.get('ok', False)
        cfg['escalation_chain'] = chain
        doc.config = cfg
        doc.save()
    except Exception as e:
        logger.warning('Failed to post escalated Q&A to WCHQ: %s', e)

    return {
        'id': doc.id,
        'escalation_chain': chain,
        'message': f'Escalated by {escalated_by}. Posted to WCHQ for team answer.',
    }


def post_qa_to_wchq(params: dict[str, Any]) -> dict[str, Any]:
    """Post a Q&A question to WCHQ (webclerk.com) via Bundle.

    Creates an outbound Bundle on the wchq-conn-upstream Connection.
    The question becomes visible to Bill, Alice, Allie, Andi, and Claude
    at WCHQ. When answered there, the answer syncs back to all deployments.

    Also checks if this question was already asked and answered at WCHQ
    (dedup by name/question text hash).
    """
    from apps.docs.models.document import Document
    from django.apps import apps
    import time

    Connection = apps.get_model('sync', 'Connection')
    Bundle = apps.get_model('sync', 'Bundle')

    doc_id = params.get('document_id')
    if not doc_id:
        raise ValueError('document_id is required')

    doc = Document.objects.get(pk=doc_id)
    cfg = doc.config or {}
    if cfg.get('purpose') != 'support_qa':
        raise ValueError('Document is not a support Q&A record')

    # Find the WCHQ upstream connection
    conn = Connection.objects.filter(ida='wchq-conn-upstream', is_active=True).first()
    if not conn:
        return {'ok': False, 'error': 'no_wchq_connection', 'message': 'WCHQ upstream connection not configured'}

    # Build the payload — question + context + escalation history + diagnostics
    #
    # Diagnostic context (passed in params.context or doc.config.context):
    #   screen       — page path where user was (e.g., /db/invoice)
    #   model        — model being viewed (e.g., invoice)
    #   field        — field in focus when question arose
    #   recent_nav   — last 5 pages visited (from navigation tracking)
    #   recent_actions — last 5 manage actions called (from console)
    #   recent_errors — last 3 console errors (from consoleCapture)
    #   recent_console — last 10 console entries (log+warn+error, what was happening)
    #   memory_mb    — browser heap used (performance.memory.usedJSHeapSize)
    #   viewport     — { width, height } of browser window
    #   user_agent   — browser string (for platform/version)
    #   user_role    — contact role (staff, rep, vendor, customer)
    #   alice_hints  — recent Alice hints shown on this page
    #   uptime_min   — minutes since app boot (session length)
    #
    context = params.get('context') or cfg.get('context') or {}

    payload = {
        'content_type': 'support_qa',
        'question': doc.name,
        'answer': doc.body or '',
        'status': doc.status,
        'uuid': str(doc.uuid) if doc.uuid else None,
        'ida': doc.ida,
        'config': {
            'purpose': 'support_qa',
            'source': cfg.get('source', 'user'),
            'domain': cfg.get('domain', ''),
            'score_avg': cfg.get('score_avg', 0),
            'score_count': cfg.get('score_count', 0),
            'escalation_chain': cfg.get('escalation_chain', []),
            'keywords': cfg.get('keywords', []),
        },
        'context': {
            'screen': context.get('screen', ''),
            'model': context.get('model', ''),
            'field': context.get('field', ''),
            'recent_nav': context.get('recent_nav', [])[:5],
            'recent_actions': context.get('recent_actions', [])[:5],
            'recent_errors': context.get('recent_errors', [])[:3],
            'recent_console': context.get('recent_console', [])[:10],
            'memory_mb': context.get('memory_mb'),
            'viewport': context.get('viewport'),
            'user_agent': context.get('user_agent', ''),
            'user_role': context.get('user_role', ''),
            'alice_hints': context.get('alice_hints', [])[:5],
            'uptime_min': context.get('uptime_min'),
        },
        'refs': {'tags': (doc.refs or {}).get('tags', [])},
    }

    started = time.perf_counter()
    try:
        bundle = Bundle.objects.create(
            connection=conn,
            direction='outbound',
            status='ok',
            payload=payload,
            size=len(str(payload)),
            duration=int((time.perf_counter() - started) * 1000),
            config={
                'content_type': 'support_qa',
                'document_id': doc.id,
                'document_uuid': str(doc.uuid) if doc.uuid else None,
            },
            response={
                'status': 'queued',
                'review': {'status': 'pending'},
            },
        )

        # Mark the Document as posted to WCHQ and preserve context
        cfg['wchq_posted'] = True
        if context:
            cfg['context'] = context
        cfg['wchq_bundle_id'] = bundle.id
        cfg['wchq_dt_posted'] = datetime.now(timezone.utc).isoformat()
        doc.config = cfg
        doc.save()

        return {
            'ok': True,
            'bundle_id': bundle.id,
            'document_id': doc.id,
            'message': 'Question posted to WCHQ. Team will review and answer.',
        }

    except Exception as e:
        logger.exception('Failed to create WCHQ bundle for Q&A %s', doc_id)
        return {'ok': False, 'error': str(e)}
