"""
Pydantic schemas for Connection JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class CarrierCredentials(BaseModel):
    """Carrier API credentials (UPS, FedEx, USPS, DHL)."""
    client_id: str = ''
    client_secret: str = ''
    account_number: str = ''

    class Config:
        extra = "allow"  # carrier-specific fields


class CarrierSettings(BaseModel):
    """Carrier-specific operational settings."""
    test_mode: bool = True
    label_format: str = 'pdf'
    fuel_factor: float = 0.0
    handling_charge: float = 0.0
    markup_percent: float = 0.0

    class Config:
        extra = "allow"


class EscalationProtocol(BaseModel):
    """Alice → Claude Code escalation configuration."""
    action_ida_prefix: str = ''
    required_fields: list[str] = Field(default_factory=list)
    priority_levels: list[str] = Field(default_factory=list)
    pickup_trigger: str = ''
    resolution: str = ''


class ConnectionConfig(BaseModel):
    """Integration protocol metadata.

    Connection.config varies by channel type: bundle sync, carrier API,
    agent escalation, server deployment. The base fields cover the common
    patterns; extra='allow' for channel-specific extensions.
    """
    channel: str = ''                        # bundle, action_queue, carrier, server
    direction: str = ''                      # push, pull, bidirectional
    endpoint: str = ''                       # URL or host
    auth_method: str = ''                    # api_key, oauth, token
    api_key_setting: str = ''                # Setting ida for credentials
    content_types: list[str] = Field(default_factory=list)
    review_required: bool = False
    # Carrier-specific
    carrier_code: str = ''                   # ups, fedex, usps, dhl
    credentials: Optional[CarrierCredentials] = None
    settings: Optional[CarrierSettings] = None
    # Agent escalation
    from_agent: str = ''
    to_agent: str = ''
    escalation_protocol: Optional[EscalationProtocol] = None

    class Config:
        extra = "allow"  # channel-specific extensions


# -- .metadata (inherits MetadataBase) --------------------------------------

class ConnectionMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ConnectionPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ConnectionRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
