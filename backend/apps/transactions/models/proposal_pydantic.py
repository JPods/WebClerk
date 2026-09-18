"""
Pydantic schemas for Proposal JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.transaction_envelopes import TransactionSignoff


# -- .config ----------------------------------------------------------------

class ProposalConfig(ConfigBase):
    """Proposal config. Signoff written by validate_status.py."""
    signoff: Optional[TransactionSignoff] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class ProposalMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ProposalPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class ProposalRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
