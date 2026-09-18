"""
ida — the human-facing identifier on every record.

Identity Model (§25 — Sync Topologies):
    id   — PK, dataset-scoped. Primary's id overwrites satellites in
           hub-spoke merge; always new in peer transfer.
    ida  — Soft identifier people read and type. Generated once on first
           save. CAN be overwritten during hub-spoke merge (primary is
           authoritative); always new in peer transfer.
    uuid — Cross-database matching key. ONLY truly immutable identity.

Two forms, meaningful characters first so people type the part that tells
records apart:
    Transaction documents — {number}-{tag} from company profile
        config.sequences.{key}: 1001-qt, 1001-so, 1001-inv, 1001-po,
        1001-wo, 1001-c. Each type counts on its own. Training documents
        (flight simulator) end in -qq: 1002-inv-qq.
    Everything else — the record's pk: "1039".

Where a record was born is not encoded in the ida; uuid carries identity
across databases. (The old {DATA_SET_ID}-{pk} form, e.g. DEV-42, is retired.)
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# model _meta.model_name -> config.sequences key
DOCUMENT_SEQUENCES = {
    'proposal': 'proposal',
    'order': 'order',
    'invoice': 'invoice',
    'purchase': 'purchase',
    'workorder': 'work_order',
    'cash': 'cash',
}

TRAINING_SUFFIX = 'qq'

# The standard sequences a new company profile starts with (config.sequences).
DEFAULT_SEQUENCES = {
    'proposal': {'tag': 'qt', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
    'order': {'tag': 'so', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
    'invoice': {'tag': 'inv', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
    'purchase': {'tag': 'po', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
    'work_order': {'tag': 'wo', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
    'cash': {'tag': 'c', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
}


def generate_ida(pk: int, prefix: Optional[str] = None) -> str:
    """ida for a non-document record: its pk, or "{prefix}-{pk}" when a caller
    explicitly asks for a prefix (e.g. set_all_ida_from_pk --prefix)."""
    return f"{prefix}-{pk}" if prefix else str(pk)


def format_document_ida(number: int, sequence: dict, training: bool = False) -> str:
    pad = int(sequence.get('pad') or 0)
    ida = f"{number:0{pad}d}-{sequence['tag']}"
    return f"{ida}-{TRAINING_SUFFIX}" if training else ida


def next_document_ida(model_name: str, training: bool = False) -> str:
    """Take the next number for a transaction document and advance the sequence.

    Reads and increments company profile config.sequences.{key} under a row
    lock, so two saves never get the same number. Raises when the company
    profile has no sequence for this document type — a document never gets
    a made-up ida.
    """
    from django.db import transaction
    from apps.core.models import Setting

    key = DOCUMENT_SEQUENCES[model_name]
    with transaction.atomic():
        company = (Setting.objects.select_for_update()
                   .filter(purpose='wc:company_profile', is_active=True).first())
        sequences = (company.config or {}).get('sequences') if company else None
        sequence = (sequences or {}).get(key)
        if not sequence or not sequence.get('tag'):
            raise ValueError(f'Company profile has no ida sequence for "{key}" (config.sequences.{key}.tag/next).')
        number = int(sequence.get('next') or 1)
        sequence['next'] = number + 1
        config = dict(company.config)
        config['sequences'] = dict(sequences, **{key: sequence})
        # Queryset update: advancing a counter is not a settings edit.
        Setting.objects.filter(pk=company.pk).update(config=config)
    return format_document_ida(number, sequence, training)
