"""Pydantic schema layer for OrgBase aspects (requires pydantic).

These schemas provide validation / normalization for OrgBase aspect JSON blobs.
We keep them decoupled so validation can be opt-in (service layer, ETL, or tests).
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ContactMini(BaseModel):
    id: Optional[int] = Field(None, description="Foreign key id to master contact record (may be None for ad-hoc)")
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=320)
    phone: Optional[str] = Field(None, max_length=40)


class LocationMini(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = Field(None, description="billing|shipping|office|warehouse|other")
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = Field(None, description="State/Province/Region")
    postal: Optional[str] = None
    country: Optional[str] = Field(None, max_length=2, description="ISO country code")
    geo: Optional[Dict[str, float]] = Field(None, description="{'lat':..,'lng':..}")


class DomainMini(BaseModel):
    domain: str = Field(..., pattern=r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    verified: bool = False
    dt_verified: Optional[int] = None  # epoch / timestamp placeholder


class PhoneMini(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = None
    number: str = Field(..., max_length=40)
    ext: Optional[str] = Field(None, max_length=10)
    primary: bool = False


class EmailMini(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = None
    email: str = Field(..., max_length=320)
    primary: bool = False
    bounce_count: int = 0


class RelationsSnapshot(BaseModel):
    parents: List[int] = Field(default_factory=list)
    children: List[int] = Field(default_factory=list)
    linked_ids: List[int] = Field(default_factory=list)


class CreditInfo(BaseModel):
    limit: Optional[float] = None
    used: Optional[float] = None


class FinancialSnapshot(BaseModel):
    credit: CreditInfo = Field(default_factory=CreditInfo)
    balances: Dict[str, float] = Field(default_factory=dict)
    due_buckets: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class DocMini(BaseModel):
    id: Optional[int] = None
    kind: Optional[str] = None
    name: Optional[str] = None
    size: Optional[int] = None
    sha256: Optional[str] = None


class ConnectionSnapshot(BaseModel):
    """External connection pointers / integration handles (service credentials, etc.)."""
    email_svc: Optional[str] = Field(None, description="Vault pointer or secret reference id")


class MetricsSnapshot(BaseModel):
    counts: Dict[str, int] = Field(default_factory=dict)
    periods: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class OrgSnapshot(BaseModel):
    org_type: str
    company: str
    status: Optional[str] = None
    is_active: bool = True
    contacts: List[ContactMini] = Field(default_factory=list)
    locations: List[LocationMini] = Field(default_factory=list)
    domains: List[DomainMini] = Field(default_factory=list)
    phones: List[PhoneMini] = Field(default_factory=list)
    emails: List[EmailMini] = Field(default_factory=list)
    relations: RelationsSnapshot = Field(default_factory=RelationsSnapshot)
    financial: FinancialSnapshot = Field(default_factory=FinancialSnapshot)
    docs: List[DocMini] = Field(default_factory=list)
    connections: ConnectionSnapshot = Field(default_factory=ConnectionSnapshot)  # type: ignore[arg-type]
    data: Dict[str, Any] = Field(default_factory=dict)
    metrics: MetricsSnapshot = Field(default_factory=MetricsSnapshot)
    gl_accounts: Dict[str, str] = Field(default_factory=dict)

    @validator('org_type')
    def _validate_org_type(cls, v):  # pragma: no cover - simple constraint
        allowed = {"customer", "vendor", "rep", "employee", "manufacturer", "other"}
        if v not in allowed:
            raise ValueError(f"org_type '{v}' not in {allowed}")
        return v


class OrgSnapshotPatch(BaseModel):  # all optional, for partial updates
    org_type: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    contacts: Optional[List[ContactMini]] = None
    locations: Optional[List[LocationMini]] = None
    domains: Optional[List[DomainMini]] = None
    phones: Optional[List[PhoneMini]] = None
    emails: Optional[List[EmailMini]] = None
    relations: Optional[RelationsSnapshot] = None
    financial: Optional[FinancialSnapshot] = None
    docs: Optional[List[DocMini]] = None
    connections: Optional[ConnectionSnapshot] = None
    data: Optional[Dict[str, Any]] = None
    metrics: Optional[MetricsSnapshot] = None
    gl_accounts: Optional[Dict[str, str]] = None


def build_org_snapshot(org) -> OrgSnapshot:
    """Construct OrgSnapshot from OrgBase instance (no additional DB hits)."""
    access_payload = getattr(org, 'connections', {})
    return OrgSnapshot(
        org_type=org.org_type,
        company=org.company,
        status=org.status,
        is_active=org.is_active,
        contacts=org.contacts or [],
        locations=org.locations or [],
        domains=org.domains or [],
        phones=org.phones or [],
        emails=org.emails or [],
        relations=org.relations or RelationsSnapshot(),
        financial=org.financial or FinancialSnapshot(),
        docs=org.docs or [],
    connections=ConnectionSnapshot(**(access_payload or {})),
        data=org.data or {},
        metrics=org.metrics or MetricsSnapshot(),
        gl_accounts=org.gl_accounts or {},
    )

# End of file
