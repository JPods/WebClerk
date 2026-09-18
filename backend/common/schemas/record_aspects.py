"""Record aspects — single-model JSON fields that had no schema.

Each shape was read from the stored data and the code that writes it
(2026-09-18). dt values are epoch milliseconds (UTC).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Item ────────────────────────────────────────────────────────────────

class ItemGls(BaseModel):
    """GL account per posting role."""
    revenue: str = ''
    cogs: str = ''
    inventory: str = ''
    purchase: str = ''
    variance: str = ''


class ItemFlags(BaseModel):
    linked: bool = False
    pacing: bool = False
    serialized: bool = False
    not_tracked: bool = False
    discountable: bool = False
    tally_by_type: bool = False
    print_suppressed: bool = False
    back_order_allowed: bool = False


class ItemTaxCode(BaseModel):
    code: str = ''
    category: str = ''
    rate: Optional[float] = None
    jurisdiction: str = ''
    jurisdiction_params: List[str] = Field(default_factory=list)
    exemptions: List[str] = Field(default_factory=list)


# ── Project ─────────────────────────────────────────────────────────────

class ProjectSuccess(BaseModel):
    definition: str = ''
    metrics: List[str] = Field(default_factory=list)


class ProjectScope(BaseModel):
    in_: List[str] = Field(default_factory=list, alias='in')
    out: List[str] = Field(default_factory=list)

    model_config = {'populate_by_name': True}


class ProjectObjective(BaseModel):
    summary: str = ''
    success: ProjectSuccess = Field(default_factory=ProjectSuccess)
    scope: ProjectScope = Field(default_factory=ProjectScope)


class ProjectTask(BaseModel):
    id: Optional[int] = None
    title: str = ''
    done: bool = False
    weight: int = 1


class ProjectTasks(BaseModel):
    items: List[ProjectTask] = Field(default_factory=list)
    total: int = 0
    completed: int = 0
    weight_total: int = 0
    weight_completed: int = 0
    notes: str = ''                          # free text, before tasks were itemised


class ProjectLogistics(BaseModel):
    budget: float = 0
    deadline: Optional[int] = None
    timezone: str = ''
    resources: List[str] = Field(default_factory=list)
    notes: str = ''


# ── Setting / Document paths ────────────────────────────────────────────

class SettingPaths(BaseModel):
    """Where a Setting's schema and model live."""
    schema_: str = Field('', alias='schema')
    model: str = ''
    setting_model: str = ''

    model_config = {'populate_by_name': True}


class DocumentPath(BaseModel):
    """Every location a document is known by."""
    type: str = ''
    key: str = ''
    url: str = ''
    source: str = ''
    local: str = ''
    description: str = ''
    heading: str = ''
    file: str = ''
    relative: str = ''
    full: str = ''
    git_path: str = ''
    storage: str = ''
    dot: str = ''
    svg: str = ''
    mapping: str = ''


# ── Serial / Warehouse ──────────────────────────────────────────────────

class SerialSite(BaseModel):
    warehouse_id: Optional[int] = None
    bin: str = ''


class SerialWarranty(BaseModel):
    provider: str = ''
    terms: str = ''
    dt_start: Optional[int] = None
    dt_end: Optional[int] = None


class WarehouseLocation(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class WarehouseCount(BaseModel):
    """The last physical count at this location."""
    aisle: str = ''
    shelf: str = ''
    column: str = ''
    bin: str = ''
    value: int = 0
    deviation: int = 0
    counted_by: str = ''
    counted_by_id: Optional[int] = None      # contact id
    dt_counted: Optional[int] = None


# ── Metrics by period ───────────────────────────────────────────────────

class MetricPeriod(BaseModel):
    """One period's aggregates. Periods are entries, not keys (Bill, 2026-09-18)."""
    period: str = ''                         # e.g. 2026Q3, 2026-09
    sales: float = 0
    purchases: float = 0
    margin: float = 0
    orders: int = 0
    invoices: int = 0


class MetricCounts(BaseModel):
    orders: int = 0
    invoices: int = 0
    proposals: int = 0
    purchases: int = 0
    cash_entries: int = 0


class PeriodMetrics(BaseModel):
    counts: MetricCounts = Field(default_factory=MetricCounts)
    periods: List[MetricPeriod] = Field(default_factory=list)
