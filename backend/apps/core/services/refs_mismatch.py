"""
Refs mismatch — a record's FK-based and refs.links-based related sets disagree.

The front end POSTs what it saw (/wcapi/_refs_mismatch/); the nightly task_audit_refs_fk walks
customers and vendors. A difference is written to the one Log, purpose refs_mismatch (read them
at /wcapi/log/?purpose=refs_mismatch).
"""
from __future__ import annotations

from apps.core.models.log import Log


def log_refs_mismatch(*, parent_model: str, parent_id: int, related_model: str, fk_field: str,
                      fk_ids: list, refs_ids: list, caller: str = '', user=None,
                      details: dict | None = None) -> Log | None:
    """Compare the two id sets; write a Log when they differ. None when they match."""
    fk_set, refs_set = set(fk_ids), set(refs_ids)
    if fk_set == refs_set:
        return None
    only_fk, only_refs = sorted(fk_set - refs_set), sorted(refs_set - fk_set)
    mismatch_type = ('fk_only' if only_fk and not only_refs
                     else 'refs_only' if only_refs and not only_fk else 'both_differ')
    return Log.write(
        'refs_mismatch', mismatch_type, user=user, model_name=parent_model, record_id=parent_id,
        details={'related_model': related_model, 'fk_field': fk_field, 'fk_ids': sorted(fk_set),
                 'refs_ids': sorted(refs_set), 'only_in_fk': only_fk, 'only_in_refs': only_refs,
                 'caller': caller, **({'context': details} if details else {})},
    )
