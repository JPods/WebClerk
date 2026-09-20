"""Importing exported records — one loader, matching on identity.

Export writes JSON (`report_registry.export_report`, `bundle_catalogue.pack_*`).
This reads it back. Every importer in WebClerk was doing the same loop with its
own rules; this is that loop, once.

## What a record is matched on

**`uuid`, when the uuid is authored once and distributed.** A bundle from WC_HQ,
a tally report seeded from a uuid5 of its key, a settings baseline — all of these
carry a uuid that every installation derives or receives identically, so the uuid
*is* the identity and matching on it is correct.

**A natural key, when two systems created the thing independently.** Scar (2026-09-17):

> Never move keyed assets between systems on the row key. A primary key, an ida,
> or a per-record uuid is local to the system that issued it and silently diverges
> across instances of the same data. Find the field that identifies what the thing
> IS — a manufacturer part number, a source-system id, a GTIN — and map through that.

Both are supported, and the caller must say which applies. `match_on` is not
optional and has no default, because guessing it wrong is exactly the failure the
scar records: the import appears to work and quietly creates duplicates.

## What it does to a record it finds

**Baseline merge.** Scalars fill only if the target is empty. JSON fields deep-merge:
keys the owner does not have are added; keys they have are left alone. `prefs` is
never touched in any mode — it is the user's space.

**Foundational protection.** A record whose `metadata.foundational` is true is skipped
unless the caller is the authority for it (`authoritative=True`, which is what the
init bundle passes).

**Replace mode** overwrites config/metadata/refs entirely. It exists for restoring
corrupted records from a known-good copy, and still never touches `prefs`.

## Foreign keys

Records exported from another database carry that database's primary keys, which mean
nothing here. `uuid_pk_map` translates: as each model is imported it records
`uuid → new pk`, and a later record pointing at an old pk is repointed. Salvaged from
`load_demo_data`, which solved this and kept the solution to itself.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence

logger = logging.getLogger(__name__)

# Never overwritten, in any mode. The user's space.
SOVEREIGN_FIELDS = ('prefs',)

# Deep-merged rather than replaced, unless replace=True.
MERGE_FIELDS = ('config', 'metadata', 'refs', 'paths')


class ImportRefused(Exception):
    """The import cannot proceed as asked — say why rather than guess."""


def deep_merge_baseline(current: dict, incoming: dict) -> dict:
    """Add the keys the owner does not have. Never replace one they do."""
    merged = dict(current)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_baseline(merged[key], value)
    return merged


def is_foundational(record) -> bool:
    meta = getattr(record, 'metadata', None)
    return bool(isinstance(meta, dict) and meta.get('foundational'))


def _model(label: str):
    from django.apps import apps as dj_apps

    try:
        return dj_apps.get_model(label)
    except (LookupError, ValueError) as exc:
        raise ImportRefused(f'Unknown model "{label}": {exc}') from exc


def _concrete_fields(Model) -> set[str]:
    return {f.name for f in Model._meta.concrete_fields}


def _match_existing(Model, rec: dict, match_on: Sequence[str]):
    """The record this one is, or None. Refuses a record that cannot be matched."""
    lookup = {}
    for field in match_on:
        value = rec.get(field)
        if value in (None, ''):
            raise ImportRefused(
                f'record cannot be matched: "{field}" is empty '
                f'(matching on {", ".join(match_on)})')
        lookup[field] = value
    return Model.objects.filter(**lookup).first()


def import_records(
    model_label: str,
    records: Iterable[dict],
    *,
    match_on: Sequence[str],
    authoritative: bool = False,
    replace: bool = False,
    dry_run: bool = False,
    uuid_pk_map: dict[str, dict[str, int]] | None = None,
    fk_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Import records into one model, matching on `match_on`.

    match_on     the field(s) that identify the thing — ('uuid',) for a distributed
                 bundle, a natural key for data two systems made independently.
                 Required: see the scar in this module's docstring.
    authoritative the caller owns foundational records (the init bundle does).
    replace      overwrite config/metadata/refs instead of baseline-merging.
                 `prefs` is still never touched.
    uuid_pk_map  {model_label: {uuid: new_pk}} built as models are imported, so a
                 record pointing at another database's pk can be repointed.
    fk_fields    {field_name: model_label} — which fields to translate through the map.

    Returns {created, updated, replaced, protected, skipped, errors}.
    """
    if not match_on:
        raise ImportRefused(
            'match_on is required. Matching on uuid is right for a distributed '
            'bundle and wrong for records two systems created independently — '
            'the caller has to say which this is.')

    Model = _model(model_label)
    fields = _concrete_fields(Model)
    uuid_pk_map = uuid_pk_map if uuid_pk_map is not None else {}
    fk_fields = fk_fields or {}

    created = updated = replaced_n = protected = skipped = 0
    errors: list[str] = []
    local_map: dict[str, int] = {}

    for rec in records:
        if not isinstance(rec, dict):
            errors.append(f'not an object: {rec!r:.60}')
            continue
        label = rec.get('ida') or rec.get('name') or rec.get('uuid') or '?'
        try:
            existing = _match_existing(Model, rec, match_on)
        except ImportRefused as exc:
            errors.append(f'{label}: {exc}')
            continue

        try:
            incoming = _translate_fks(rec, fk_fields, uuid_pk_map)

            if existing is not None:
                if is_foundational(existing) and not authoritative:
                    protected += 1
                    continue
                if dry_run:
                    updated += 1
                    continue
                changed = _apply(existing, incoming, fields, replace=replace)
                _authorize(existing)
                existing.save()
                if replace:
                    replaced_n += 1
                else:
                    updated += 1
                if not changed:
                    pass  # a no-op update still counts — the record was seen
            else:
                if dry_run:
                    created += 1
                    continue
                obj = Model()
                _apply(obj, incoming, fields, replace=True, creating=True)
                _authorize(obj)
                obj.save()
                created += 1

            target = existing if existing is not None else obj
            rec_uuid = rec.get('uuid')
            if rec_uuid:
                local_map[str(rec_uuid)] = target.pk

        except Exception as exc:
            errors.append(f'{label}: {exc}')
            logger.exception('record_import: %s on %s', model_label, label)

    if local_map:
        uuid_pk_map.setdefault(model_label, {}).update(local_map)

    if protected:
        logger.info('record_import: %d foundational %s records protected',
                    protected, model_label)
    logger.info(
        'record_import %s: created=%d updated=%d replaced=%d protected=%d errors=%d',
        model_label, created, updated, replaced_n, protected, len(errors))

    return {'created': created, 'updated': updated, 'replaced': replaced_n,
            'protected': protected, 'skipped': skipped, 'errors': errors}


def _translate_fks(rec: dict, fk_fields: dict[str, str],
                   uuid_pk_map: dict[str, dict[str, int]]) -> dict:
    """Repoint foreign keys that carry another database's primary keys."""
    if not fk_fields:
        return rec
    out = dict(rec)
    for field, target_label in fk_fields.items():
        by_uuid = rec.get(f'{field}_uuid')
        if not by_uuid:
            continue
        new_pk = (uuid_pk_map.get(target_label) or {}).get(str(by_uuid))
        if new_pk is not None:
            out[field] = new_pk
        else:
            out.pop(field, None)   # better absent than pointing at a stranger
    return out


def _apply(obj, rec: dict, fields: set[str], *, replace: bool,
           creating: bool = False) -> bool:
    """Write the record onto the object. Returns whether anything changed."""
    changed = False
    for key, value in rec.items():
        if key not in fields or key in SOVEREIGN_FIELDS:
            continue
        if key == 'id':
            continue          # this database issues its own primary keys
        if key == 'uuid' and not creating:
            continue          # the match key is not a field to rewrite

        if key in MERGE_FIELDS and not replace:
            current = getattr(obj, key, None) or {}
            if isinstance(current, dict) and isinstance(value, dict):
                merged = deep_merge_baseline(current, value)
                if merged != current:
                    setattr(obj, key, merged)
                    changed = True
                continue
            if current:
                continue
        elif not replace and not creating:
            # Scalars fill only when the target is empty.
            if getattr(obj, key, None) not in (None, '', 0):
                continue

        if getattr(obj, key, None) != value:
            setattr(obj, key, value)
            changed = True

    # prefs lands only on a record being created — never on one that exists.
    if creating:
        for key in SOVEREIGN_FIELDS:
            if key in rec and key in fields:
                setattr(obj, key, rec[key])
    return changed


def _authorize(obj) -> None:
    """Settings guard their own writes; an approved import says so."""
    obj._setting_update_authorized = True
    obj._setting_create_authorized = True
