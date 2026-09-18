"""
Pydantic schemas for Document JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
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


class DocumentConfig(ConfigBase):
    copyright: Optional[DocumentCopyright] = None


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
