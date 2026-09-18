"""Action aspects — the JSON fields on Action beyond its envelopes.

Text an Action shows people is keyed by language (action.action.en). Only the
languages declared on LocalizedText are leaves; add one here to use it.
dt values are epoch milliseconds (UTC).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LocalizedText(BaseModel):
    """One piece of text in each supported language."""
    en: str = ''
    es: str = ''


class UserStamp(BaseModel):
    """Who did something, and when. created_by / updated_by / *_by are lists of these."""
    id: Optional[int] = None                 # contact id
    email: Optional[str] = None
    dt: Optional[int] = None


class ImpactTransaction(BaseModel):
    model: str = ''
    id: Optional[int] = None
    ida: str = ''
    value: float = 0


class ImpactRefs(BaseModel):
    transactions: List[ImpactTransaction] = Field(default_factory=list)
    explanation: str = ''                    # why predicted and actual differ


class ActionImpact(BaseModel):
    """Not precision — retrospection. The gap between predicted and actual is the lesson."""
    predicted: int = 0                       # 1-5 gut feel when the action was set
    actual: int = 0                          # 1-5 looking back
    refs: ImpactRefs = Field(default_factory=ImpactRefs)


class ActionRetrospection(BaseModel):
    """Structured learning from one action."""
    intent: str = ''
    points_for: str = ''
    points_against: str = ''
    harms: str = ''
    benefits: str = ''
    risk: str = ''
    unknowns: str = ''
    tfts: str = ''                           # try-fail-try-succeed arc
    confidence: int = 0
    grade: str = ''                          # A-F against the memory markers
    grade_note: str = ''


class AssignedPerson(BaseModel):
    """One person on an action's roster. The first entry is responsible.

    org_id is the person's organisation: it is how a customer or vendor login
    finds the actions they are on (kanban), scoped to their own org.
    Same {id, name} shape the ContactSelectWidget reads and writes.
    """
    id: Optional[int] = None                 # contact id
    org_id: Optional[int] = None
    name: str = ''
    email: str = ''
    role: str = ''                           # customer, vendor, rep, sales, admin, agent …
