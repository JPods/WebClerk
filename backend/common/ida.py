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
    Transaction documents — config.sequences.{key}.format from the company profile,
        default {number}-{tag}: 1001-qt, 1001-so, 1001-inv, 1001-po, 1001-wo, 1001-c.
        Each type counts on its own. Training documents (flight simulator) end in -qq
        whatever the format: 1002-inv-qq.
    Everything else — the record's pk: "1039".

The format is the company's (Bill, 2026-09-26: "add the model indicator … define a prefix or
suffix (maybe 2 digit year)"). Tokens: {number} (required, padded), {tag}, {yy}, {yyyy}, {mm};
anything else is literal text. ``reset: "yearly"`` restarts the number each year and needs a
year token (else two documents would share an ida). The year and month are the company's local
date (config.regional.timezone): a document written on Dec 31 evening belongs to that year.

Where a record was born is not encoded in the ida; uuid carries identity
across databases. (The old {DATA_SET_ID}-{pk} form, e.g. DEV-42, is retired.)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# model _meta.model_name -> config.sequences key
DOCUMENT_SEQUENCES = {
    'quote': 'quote',
    'order': 'order',
    'invoice': 'invoice',
    'purchase': 'purchase',
    'workorder': 'work_order',
    'cash': 'cash',
}

TRAINING_SUFFIX = 'qq'

# The standard sequences a new company profile starts with (config.sequences).
DEFAULT_SEQUENCES = {
    'quote': {'tag': 'qt', 'pad': 4, 'next': 1001, 'format': '{number}-{tag}'},
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


DEFAULT_FORMAT = '{number}-{tag}'
TOKENS = ('number', 'tag', 'yy', 'yyyy', 'mm')
YEAR_TOKENS = ('{yy}', '{yyyy}')


def validate_sequences(sequences: Optional[dict]) -> None:
    """Refuse a company profile whose sequences cannot make unique idas — with coaching."""
    import string
    for key, seq in (sequences or {}).items():
        if not isinstance(seq, dict):
            continue                                   # e.g. the 'note' string
        fmt = seq.get('format') or DEFAULT_FORMAT
        try:
            names = {f for _, f, _, _ in string.Formatter().parse(fmt) if f is not None}
        except ValueError as e:
            raise ValueError(f'sequences.{key}.format "{fmt}" is not a format: {e}')
        unknown = names - set(TOKENS)
        if unknown:
            raise ValueError(f'sequences.{key}.format "{fmt}" uses {sorted(unknown)}; the tokens are '
                             f'{{{"}, {".join(TOKENS)}}}, anything else is literal text.')
        if 'number' not in names:
            raise ValueError(f'sequences.{key}.format "{fmt}" needs {{number}}: without it every '
                             f'{key} would get the same ida.')
        if seq.get('reset') not in (None, '', 'never', 'yearly'):
            raise ValueError(f'sequences.{key}.reset is "{seq.get("reset")}"; use "yearly" or leave it out.')
        if seq.get('reset') == 'yearly' and not any(t in fmt for t in YEAR_TOKENS):
            raise ValueError(f'sequences.{key} restarts yearly, so its format needs {{yy}} or {{yyyy}}; '
                             f'"{fmt}" would repeat last year\'s idas.')


def format_document_ida(number: int, sequence: dict, training: bool = False, on=None) -> str:
    """The ida for a document number in its sequence's format, on the company's local date."""
    on = on or date.today()
    pad = int(sequence.get('pad') or 0)
    ida = (sequence.get('format') or DEFAULT_FORMAT).format(
        number=f"{number:0{pad}d}", tag=sequence.get('tag', ''),
        yy=f"{on.year % 100:02d}", yyyy=f"{on.year:04d}", mm=f"{on.month:02d}")
    return f"{ida}-{TRAINING_SUFFIX}" if training else ida


def company_today(company_config: Optional[dict]):
    """Today in the company's timezone (config.regional.timezone), UTC when none is set."""
    tz_name = ((company_config or {}).get('regional') or {}).get('timezone')
    try:
        tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    except Exception:
        raise ValueError(f'Company profile regional.timezone "{tz_name}" is not a timezone '
                         f'(e.g. America/New_York).')
    return datetime.now(tz).date()


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
        today = company_today(company.config)
        if sequence.get('reset') == 'yearly' and sequence.get('year') != today.year:
            sequence['next'] = int(sequence.get('start') or 1)     # a new year starts over
        sequence['year'] = today.year
        number = int(sequence.get('next') or 1)
        sequence['next'] = number + 1
        config = dict(company.config)
        config['sequences'] = dict(sequences, **{key: sequence})
        # Queryset update: advancing a counter is not a settings edit.
        Setting.objects.filter(pk=company.pk).update(config=config)
    return format_document_ida(number, sequence, training, on=today)
