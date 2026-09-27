"""
Pydantic schemas for Sync Bundle JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Import bundles carry an ImportBundleHeader (from connection schema)
that must be signed off before processing. Athena reviews for hidden harms.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from apps.sync.models.connection_pydantic import ImportBundleHeader


# -- .config ----------------------------------------------------------------

class ImportApproval(BaseModel):
    by: str = ''                             # the approver's login email (Alice's, Athena's)
    by_id: Optional[int] = None
    dt: str = ''                             # UTC ISO
    content_hash: str = ''                   # what was approved; a changed bundle voids it
    notes: list[str] = Field(default_factory=list)


class ImportRun(BaseModel):
    """One import through the route (plan §17.13): what the pre-import found, who approved
    which content, and what the import did."""
    content_hash: str = ''
    preview: dict = Field(default_factory=dict)
    approvals: dict[str, ImportApproval] = Field(default_factory=dict)   # 'alice', 'athena'
    imported: dict = Field(default_factory=dict)


class BundleConfig(ConfigBase):
    """Bundle configuration — includes import header when channel='import'."""
    import_header: Optional[ImportBundleHeader] = None
    payload_path: str = ''                   # the JSON on disk (bundle_storage), relative to WORK_DIR
    import_run: Optional[ImportRun] = None


# -- .metadata (inherits MetadataBase) --------------------------------------

class BundleMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class BundlePrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class BundleRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
