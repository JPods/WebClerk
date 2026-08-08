"""
Pydantic schemas for Contact JSON envelopes.

Inherits standard bases from envelopes.py.
Adds contact-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import (
    MetadataBase, RecordPrefsBase, RefsBase, SourceRef,
    StaffPrefsMixin, RepPrefsMixin, EmployeePrefsMixin, CartPrefsMixin,
)
from .images import ContactImages


# ── .config ────────────────────────────────────────────────────────────

class ContactConfig(BaseModel):
    """Structural data — import originals."""
    original_mac: Optional[dict] = None
    phone_original: Optional[str] = None

    class Config:
        extra = "allow"


# ── .metadata (inherits MetadataBase) ──────────────────────────────

class ZeroBounceValidation(BaseModel):
    """Email validation result from ZeroBounce."""
    domain: str = ""
    status: str = ""
    validated: str = ""
    free_email: bool = False
    sub_status: str = ""
    did_you_mean: Optional[str] = None
    smtp_provider: str = ""


class SearchLogEntry(BaseModel):
    dt: int = 0
    term: str = ""
    model: str = ""
    results: int = 0


class NavigationLogEntry(BaseModel):
    dt: int = 0
    model: str = ""


class ContactMetadata(MetadataBase):
    """Contact-specific metadata. Inherits all standard fields."""
    zb: Optional[ZeroBounceValidation] = None
    images: dict = Field(default_factory=dict)    # legacy image paths
    search_log: list[SearchLogEntry] = Field(default_factory=list)
    navigation_log: list[NavigationLogEntry] = Field(default_factory=list)


# ── .prefs (inherits RecordPrefsBase) ──────────────────────────────

class OrgLink(BaseModel):
    """One org relationship this contact cares about.

    Users add what matters for their context — buyer adds customer,
    purchasing adds vendor + terms. No canonical fields for every
    possible org relationship. Users control what's here.
    """
    model: str                                # org_type: customer, vendor, manufacturer, employee, rep
    id: Optional[int] = None                  # OrgBase FK
    company: Optional[str] = None             # display name (denormalized for convenience)
    role: Optional[str] = None                # contact's role at this org
    terms: Optional[str] = None               # payment terms if relevant
    note: Optional[str] = None                # user's note about this relationship

    class Config:
        extra = 'allow'                       # users will add fields we haven't thought of


class ContactPrefs(RecordPrefsBase):
    """Contact prefs — role-conditional sections activated by Setting.

    Base (every contact): userdefined, tags, pinned
    orgs: org relationships this contact cares about
    staff: is_staff or employee FK
    employee: employee FK
    rep: rep FK
    cart: customer-facing contacts
    """
    orgs: list[OrgLink] = Field(default_factory=list)
    staff: Optional[StaffPrefsMixin] = None
    employee: Optional[EmployeePrefsMixin] = None
    rep: Optional[RepPrefsMixin] = None
    cart: Optional[CartPrefsMixin] = None


# ── .refs ──────────────────────────────────────────────────────────

class ContactRefsLinks(BaseModel):
    """Communication and relationship cache."""
    rep: list = Field(default_factory=list)
    item: list = Field(default_factory=list)
    email: list[dict] = Field(default_factory=list)
    order: list = Field(default_factory=list)
    phone: list[dict] = Field(default_factory=list)
    vendor: list = Field(default_factory=list)
    address: list[dict] = Field(default_factory=list)
    contact: list = Field(default_factory=list)
    project: list = Field(default_factory=list)
    customer: list = Field(default_factory=list)
    document: list = Field(default_factory=list)
    location: list = Field(default_factory=list)
    manufacturer: list = Field(default_factory=list)

    class Config:
        extra = "allow"


class ContactRefs(RefsBase):
    links: ContactRefsLinks = Field(default_factory=ContactRefsLinks)  # type: ignore[assignment]
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    parents: list = Field(default_factory=list)
    depends_on: dict = Field(default_factory=dict)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── Setting defaults ──────────────────────────────────────────────

class ContactSettingDefaults(BaseModel):
    role: str = "user"
    is_active: bool = True
