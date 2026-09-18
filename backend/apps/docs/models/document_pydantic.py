"""
Pydantic schemas for Document JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class CopyrightGrant(BaseModel):
    """What the holder permits — enumerated, never assumed.

    Anything not granted is withheld. A reader deciding whether it may copy,
    publish or sell a document reads this block and nothing else.
    """
    distribute: Optional[str] = None        # none | company | by_uuid | public
    modify: Optional[bool] = None
    derive: Optional[bool] = None           # derivative works
    commercial: Optional[bool] = None
    resell: Optional[bool] = None
    share_alike: Optional[bool] = None      # derivatives carry these same terms
    attribution: Optional[str] = None       # the credit line that must ride along
    conditions: list[str] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class CopyrightSource(BaseModel):
    """Where the rights came from — the evidence behind the claim."""
    origin: Optional[str] = None            # "original work", "licensed", "public domain", "assigned"
    acquired_from: Optional[str] = None     # party the rights came from
    dt_acquired: Optional[int] = None       # epoch ms, UTC (Axiom 14)
    evidence_uuid: Optional[str] = None     # Document UUID of the agreement / license file
    evidence_path: Optional[str] = None

    class Config:
        extra = 'forbid'


class CopyrightTerm(BaseModel):
    """Rights are revocable and they end. Say when, and what happens then."""
    dt_start: Optional[int] = None          # epoch ms, UTC
    dt_expires: Optional[int] = None        # epoch ms, UTC; None = no stated end
    on_expiry: Optional[str] = None         # revert | archive | renew | public_domain
    revocable: Optional[bool] = None
    dt_revoked: Optional[int] = None

    class Config:
        extra = 'forbid'


class CopyrightContact(BaseModel):
    """Who to ask for permission beyond what is granted."""
    name: Optional[str] = None
    email: Optional[str] = None
    contact_id: Optional[int] = None        # Contact record, when the party is one

    class Config:
        extra = 'forbid'


class DocumentCopyright(BaseModel):
    """Who owns the document and on what terms it may be passed on.

    A declared term about the document, not observed state — so it lives in
    .config, which is permanent, rather than in .metadata, which changes with
    every save. (metadata.exif.copyright is a different thing: a string read
    out of an image file — a fact about the source, not a term.)

    Same shape as the rest of the ecosystem treats rights: permissions are
    enumerated, evidenced, and revocable. Silence is not consent.
    """
    holder: Optional[str] = None            # "JPods, Inc.", "Bill James"
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    license: Optional[str] = None           # "proprietary", "CC-BY-4.0", "public-domain"
    license_url: Optional[str] = None
    level: Optional[int] = None             # 0 = open … higher = more restricted
    jurisdiction: Optional[str] = None      # "US", "EU" — whose law governs
    path: Optional[str] = None              # where the notice / license text lives
    grant: Optional[CopyrightGrant] = None
    source: Optional[CopyrightSource] = None
    term: Optional[CopyrightTerm] = None
    contact: Optional[CopyrightContact] = None
    notes: list[str] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class QaEscalation(BaseModel):
    """One hop in a support Q&A escalation (support_qa.escalate_qa)."""
    agent: str = ''
    reason: str = ''
    dt: Optional[str] = None                # ISO UTC, as written by escalate_qa
    wchq_posted: Optional[bool] = None

    class Config:
        extra = 'forbid'


class QaTemplateDefaults(BaseModel):
    """Per-template answer options (qa_service.create_question_group);
    each question may override them."""
    allow_freeform: bool = False
    allow_multiple: bool = False
    require_image: bool = False
    image_max: int = 5
    image_types: list[str] = Field(default_factory=lambda: ['jpg', 'png', 'webp'])

    class Config:
        extra = 'forbid'


class AthenaCheckpoint(BaseModel):
    """One signed file in the Athena integrity manifest (athena_sign)."""
    path: str
    hash: str
    signed: Optional[str] = None            # ISO UTC
    type: str = 'unknown'

    class Config:
        extra = 'forbid'


class DocumentQuarantine(BaseModel):
    """Upload quarantine state (document_sanitizer.default_quarantine)."""
    status: str = 'pending'                 # pending | sanitized | cleared | failed
    sanitized: bool = False
    sanitized_at: Optional[int] = None      # epoch ms
    alice_cleared: bool = False
    alice_cleared_at: Optional[int] = None
    alice_findings: list[str] = Field(default_factory=list)
    athena_cleared: bool = False
    athena_cleared_at: Optional[int] = None
    athena_required: bool = True
    athena_reviewer: Optional[int] = None
    threats_found: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class DocumentConfig(ConfigBase):
    copyright: Optional[DocumentCopyright] = None

    # -- support Q&A (ai_assistant/services/support_qa.py) --
    source: Optional[str] = None            # user | readme_mining | ...
    domain: Optional[str] = None
    asked_by: Optional[str] = None
    dt_asked: Optional[str] = None          # ISO UTC
    answered_by: Optional[str] = None
    dt_answered: Optional[str] = None       # ISO UTC
    score_count: int = 0
    score_sum: int = 0
    score_avg: float = 0
    escalation_chain: list[QaEscalation] = Field(default_factory=list)
    context: Optional[dict] = None          # browser diagnostics captured at ask time
    wchq_posted: Optional[bool] = None
    wchq_bundle_id: Optional[int] = None
    wchq_dt_posted: Optional[str] = None    # ISO UTC

    # -- question templates (docs/services/qa_service.py) --
    template: Optional[QaTemplateDefaults] = None
    questions: list[dict] = Field(default_factory=list)

    # -- Athena integrity manifest (support/scheduler/tasks.py, athena_sign) --
    checkpoints: list[AthenaCheckpoint] = Field(default_factory=list)
    last_sign: Optional[str] = None         # ISO UTC
    last_check: Optional[str] = None        # ISO UTC
    last_result: Optional[str] = None       # PASS | FAIL
    check_count: int = 0

    # -- uploads (docs/views/upload_view.py, docs/services/document_sanitizer.py) --
    quarantine: Optional[DocumentQuarantine] = None
    inline_encoding: Optional[str] = None   # zlib+base64
    inline_content_b64: Optional[str] = None
    inline_size_bytes: Optional[int] = None

    # -- serial trends (products/services/serial/serial_trends.py) --
    item_id: Optional[int] = None
    item_ida: Optional[str] = None
    data: Optional[dict] = None

    # -- WCHQ hook review (ai_assistant/services/hook_review_hq.py) --
    instance_uuid: Optional[str] = None
    report_ida: Optional[str] = None
    hook_hash: Optional[str] = None
    hooks: Optional[dict] = None
    note: Optional[str] = None
    findings: list = Field(default_factory=list)
    simulation: Optional[dict] = None
    elapsed_ms: Optional[int] = None
    decision: Optional[Literal['cleared', 'denied', 'auto_cleared']] = None  # lifecycle is Document.status
    signed_off_by: Optional[str] = None
    reason: Optional[str] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class DocumentMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class DocumentPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class DocumentRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
