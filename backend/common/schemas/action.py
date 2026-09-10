"""
Pydantic schemas for Action JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Times & Billable (established 2026-09-09):
  action.times  — clock in/out array for any action, billable or not.
  action.billable — billing config, estimates, actuals, invoice linkage.
  Kept as separate top-level JSON fields on the Action model so that
  time tracking and billing are independent concerns.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ═══════════════════════════════════════════════════════════════════════
# action.times — clock in/out entries for any action
# ═══════════════════════════════════════════════════════════════════════

class TimeEntry(BaseModel):
    """One clock-in / clock-out span on an action."""
    id: Optional[str] = None                  # uuid — assigned on creation
    who: Optional[int] = None                 # contact_id of person logging time
    dt_in: Optional[int] = None               # epoch ms — clock in
    dt_out: Optional[int] = None              # epoch ms — clock out (null = still clocked in)
    elapsed_ms: Optional[int] = None          # dt_out - dt_in (computed on clock-out)
    percent_active: int = Field(
        100, ge=0, le=100,
        description="Utilization — 100 = fully productive, 50 = half idle/waiting",
    )
    reason: str = ""                          # what this time span was for
    notes: str = ""                           # freeform detail
    tags: list[str] = Field(default_factory=list)   # industry/task tags
    issue: Optional[str] = None               # interruption, delay, problem encountered

    class Config:
        extra = "allow"                       # industries will add fields we haven't thought of

    @model_validator(mode="after")
    def compute_elapsed(self) -> "TimeEntry":
        if self.dt_in is not None and self.dt_out is not None and self.elapsed_ms is None:
            self.elapsed_ms = self.dt_out - self.dt_in
        return self


class ActionTimes(BaseModel):
    """action.times — time tracking for any action regardless of billing."""
    entries: list[TimeEntry] = Field(default_factory=list)
    total_elapsed_ms: Optional[int] = None    # sum of entries[].elapsed_ms
    total_active_ms: Optional[int] = None     # sum adjusted by percent_active

    class Config:
        extra = "forbid"


# ═══════════════════════════════════════════════════════════════════════
# action.billable — billing configuration, estimates, actuals
# ═══════════════════════════════════════════════════════════════════════

class ActionBillable(BaseModel):
    """action.billable — the money side of an action."""
    # -- who is billed --
    customer_id: Optional[int] = None         # billing party (customer record)
    contact_id: Optional[int] = None          # specific person on the account
    company: str = ""                         # display name (denormalized)
    attention: str = ""                       # attention line on invoice

    # -- rate --
    is_billable: bool = True
    rate: Optional[float] = None              # per rate_unit
    rate_unit: str = Field(
        "hour",
        description="hour | day | flat | unit",
    )
    currency: str = "USD"

    # -- categorization --
    skill_category: str = ""                  # journeyman_plumber, electrician, etc.
    activity: str = ""                        # installation, service, consultation, etc.

    # -- estimates vs actuals --
    hours_estimated: Optional[float] = None
    hours_actual: Optional[float] = None
    total_estimated: Optional[float] = None   # rate * hours_estimated (or flat amount)
    total_actual: Optional[float] = None      # rate * hours_actual (or flat amount)
    variance_pct: Optional[float] = None      # ((actual - estimated) / estimated) * 100

    # -- product set (what is being installed / serviced) --
    product_set: list[int] = Field(
        default_factory=list,
        description="Item IDs that this labor applies to",
    )

    # -- invoice linkage --
    invoice_id: Optional[int] = None
    invoice_line: Optional[int] = None

    # -- Alice learning signal --
    estimate_source: Optional[str] = Field(
        None,
        description="Who produced the estimate: alice | user | historical",
    )
    estimate_confidence: Optional[int] = Field(
        None, ge=1, le=10,
        description="1-10 confidence in the estimate (Alice or user)",
    )

    class Config:
        extra = "allow"                       # industries will add fields


# -- .config ----------------------------------------------------------------

class ActionConfig(ConfigBase):
    times: Optional[ActionTimes] = None
    billable: Optional[ActionBillable] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class ActionMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ActionPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ActionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
