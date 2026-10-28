"""
Pydantic schemas for Log JSON envelopes.

Log — the one log (CoreModel + RefsMixin). Why a row exists is the `purpose` scalar; which
record it is about is `model_name` / `record_id`; who is `user` — never duplicated here.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, RefsBase


class LogConfig(ConfigBase):
    """The entry's content: three typed leaves, so access can name them (an untyped key is no
    leaf and no reader sees it). What each purpose puts in details:

    audit           changes {field: {old, new}}; details: ip_address, user_agent, session_id
    alice           name (the readable line); details: what Alice observed
    refs_mismatch   details: related_model, fk_field, fk_ids, refs_ids, only_in_fk, only_in_refs, caller
    coaching        details: drill_id, drill_name, category, score, duration_seconds,
                    dt_started, dt_completed, document_id, contact_id
    inventory       name: the readable line; details: item_code, document {model, id, ida},
                    line_id, quantity_before / after / delta, unit_cost, unit_price, on_hand,
                    on_order, on_purchase, available, reorder_point, org_id
    foreign_*       details: a summary of the foreign event; the record stays in its database
    """
    name: str = ''
    changes: dict = Field(default_factory=dict)
    details: dict = Field(default_factory=dict)


class ForeignRef(BaseModel):
    """A record kept in another database (Bill, 2026-10-28): the path to it, never a copy."""
    database: str
    model: str
    uuid: str


class ActorRef(BaseModel):
    """The kind of actor behind an entry and its channel; the person is Log.user."""
    kind: str                       # user, staff, public, sync, system
    source: str                     # wcapi, admin, command, task, sync
    connection_id: Optional[int] = None


class LogRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    actor: Optional[ActorRef] = None
    foreign: Optional[ForeignRef] = None
