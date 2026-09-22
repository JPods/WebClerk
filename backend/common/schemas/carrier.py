"""Carrier signals — the `_variables` a record carries between client and server.

Bill, 2026-09-22: "_delete is better... We may have other reasons to create signaling tools
between the back and front that are not subject to view/edit", and on the shape: individual
`_variables` uniformly defined by a schema, not a nested object.

A carrier signal is **not a field**. It never reaches a column, it is never gated by the
field view/edit policy, and it says what to DO with a record rather than what the record IS:

    {"id": 12, "quantity": {...}, "_dirty": true, "_delete": true}

Why the aliases: pydantic treats a name beginning with an underscore as a private attribute,
so a field declared `_delete: bool` is **silently dropped** — the model ends up with no fields
at all and validates nothing (verified 2026-09-22). The wire name lives in the alias; the
python name does not carry the underscore.

Unknown or malformed signals raise. A misspelled `_delte` used to be dropped as "denied" and
the save reported success (Bill: "failing hard will make seeing the failure more clear").
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CarrierBase(BaseModel):
    """Signals a client may send with a record. One definition for every model."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    dirty: bool = Field(True, alias='_dirty',
                        description="The client changed this record; false means skip the save.")
    new: bool = Field(False, alias='_new',
                      description="The client made this record; it has no id yet.")
    delete: bool = Field(False, alias='_delete',
                         description="Delete this record. The delete runs in the same save as its "
                                     "parent, so the Pendings for what it held are written with it.")
    index: Optional[int] = Field(None, alias='_index',
                                 description="The record's position in the array it arrived in.")


#: Every wire name this schema accepts — the registry the write policy checks against.
CARRIER_KEYS: frozenset[str] = frozenset(
    f.alias or name for name, f in CarrierBase.model_fields.items()
)


class CarrierError(ValueError):
    """A signal that is not one of ours, or not the type it should be."""

    def __init__(self, detail: str):
        super().__init__(
            f"{detail}. Carrier signals are {', '.join(sorted(CARRIER_KEYS))} — "
            f"a signal is not a field, and an unknown one is refused rather than ignored.")


def read_carrier(payload: dict[str, Any]) -> CarrierBase:
    """The signals on one record. Raises CarrierError on anything unknown or ill-typed."""
    signals = {k: v for k, v in (payload or {}).items()
               if isinstance(k, str) and k.startswith('_')}
    try:
        return CarrierBase(**signals)
    except ValidationError as exc:
        raise CarrierError(
            '; '.join(f"{'.'.join(str(p) for p in e['loc']) or '?'}: {e['msg']}"
                      for e in exc.errors())) from exc


def without_carrier(payload: dict[str, Any]) -> dict[str, Any]:
    """The record without its signals — what the field layer sees."""
    return {k: v for k, v in (payload or {}).items()
            if not (isinstance(k, str) and k.startswith('_'))}
