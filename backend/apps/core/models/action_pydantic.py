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

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


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

class LifecycleTransition(BaseModel):
    """One state transition in the lifecycle history."""
    state: str = ''                           # built | tested | reworked | approved
    by: str = ''                              # who triggered
    dt: Optional[int] = None                  # epoch ms
    session: str = ''                         # session identifier
    details: str = ''

    class Config:
        extra = 'forbid'


class ActionLifecycle(BaseModel):
    """Feature lifecycle state machine on config['lifecycle'].

    Written by action_lifecycle.py.
    """
    feature: str = ''
    current_state: str = ''                   # built | tested | reworked | approved
    transitions: list[LifecycleTransition] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class InquiryAnswer(BaseModel):
    """One of the site's questions (settings.INQUIRY_SITES[site].ask.questions), with the
    wording as asked — the questions will change; the answer keeps its own question."""
    q: str
    a: str = ''

    class Config:
        extra = 'forbid'


class InquiryNote(BaseModel):
    """A statement with a link, shown under the questions — e.g. "See TFM hours:" + url."""
    text: str
    url: str

    @field_validator('url')
    @classmethod
    def _https(cls, v):
        if not v.startswith('https://'):
            raise ValueError('note url must start with https://')
        return v

    class Config:
        extra = 'forbid'


class InquiryAsk(BaseModel):
    market_use: list[str] = []                # options for "how often do you use the market?"; set = required
    questions: list[str] = []                 # free-text questions, answers optional
    note: Optional[InquiryNote] = None

    class Config:
        extra = 'forbid'


# qq — tester exemption (Bill, 2026-09-18, one month): remove InquiryTester and
# InquiryLimits.testing once testing is done; grep "qq" finds every piece.
class InquiryTester(BaseModel):
    """A mailbox exempt from the inquiry limits until a sunset."""
    email: str                                # matched by mailbox: name+tag@x counts as name@x
    until_utc: str                            # ISO-8601 Z; the exemption ends here

    class Config:
        extra = 'forbid'


class InquiryLimits(BaseModel):
    """Spam limits for a public inquiry form. Per visitor IP is also capped in code
    (REST_FRAMEWORK throttle rates 'inquiry' / 'inquiry_form')."""
    links_per_mailbox_per_day: int = 3        # link emails to one mailbox per UTC day
    one_open_per_contact: bool = True         # a repeat submission is added to the open inquiry
    testing: list[InquiryTester] = []         # qq — tester exemption, remove after testing

    class Config:
        extra = 'forbid'


class InquiryForm(BaseModel):
    """Report.config.inquiry for a public inquiry site (Report category='form',
    model_name='action'). Who answers and what the form asks — data, edited in WebClerk.
    Where the link points and who may call stay in settings.INQUIRY_SITES."""
    site: str                                 # key in settings.INQUIRY_SITES
    assign: list[dict] = []                   # roster for the new Action, e.g. [{"email": …}]; first responsible
    ask: InquiryAsk = InquiryAsk()
    limits: InquiryLimits = InquiryLimits()

    class Config:
        extra = 'forbid'


class ActionInquiry(BaseModel):
    """Who asked, from the public inquiry form (inquiry_view), exactly as typed. The email is
    proven by the emailed link; nothing else the visitor typed is. contact_id is the Contact
    with that email — created by the form when none existed."""
    name: str
    email: str
    phone: str = ''
    company: str = ''
    role: str = ''                            # 'I am a…' — farmer, chef, city official, ...
    topic: str = ''
    page: str = ''                            # page the visitor started from
    email_verified: bool = False
    token_id: str = ''                        # sha256 of the emailed token: one Action per link
    followup_token_ids: list[str] = []        # later links whose submissions were added to this inquiry
    site: str = ''                            # settings.INQUIRY_SITES key
    contact_id: Optional[int] = None
    contact_created: bool = False             # False = the email already had a Contact
    market_use: str = ''                      # how often they use the market (site's options)
    answers: list[InquiryAnswer] = []

    class Config:
        extra = 'forbid'


class ActionConfig(ConfigBase):
    inquiry: Optional[ActionInquiry] = None
    times: Optional[ActionTimes] = None
    billable: Optional[ActionBillable] = None
    lifecycle: Optional[ActionLifecycle] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class ClaudeUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ActionMetadata(MetadataBase):
    # Agent proposals (~/Allie/scripts/agent-sprint.py writes, allie-reflect.py
    # rolls sprints forward). Flat so their metadata->>'key' queries hold.
    agent: bool = False
    source_agent: str = ''                    # nora, natalie, noelle, sally, alice…
    capacity: str = ''                        # ops | hc | librarian
    hypothesis_id: str = ''
    confidence: float = 0
    requires_human: bool = False
    requires_claude: bool = False
    sprint_week: Optional[int] = None         # ISO week the proposal belongs to
    claude_prompt: str = ''
    claude_response: str = ''                 # first 4000 chars
    claude_usage: 'ClaudeUsage' = Field(default_factory=lambda: ClaudeUsage())
    claude_error: str = ''
    result: str = ''
    dt_completed: Optional[int] = None        # epoch ms


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ActionPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class GanttDependency(BaseModel):
    """One Gantt dependency link (parent or child)."""
    id: int                                   # action_id of the dependency
    sequence: int = 0                         # ordering within the group

    class Config:
        extra = 'forbid'


class ActionRefsLinks(BaseModel):
    """Gantt dependency structure in refs.links."""
    children: list[GanttDependency] = Field(default_factory=list)
    parents: list[GanttDependency] = Field(default_factory=list)

    class Config:
        extra = 'allow'                       # other link types may exist


class ActionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
    links: ActionRefsLinks = Field(default_factory=ActionRefsLinks)  # type: ignore[assignment]
    contact_links: list[dict] = Field(default_factory=list)
