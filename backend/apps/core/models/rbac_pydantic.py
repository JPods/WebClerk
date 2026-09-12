"""
Pydantic schemas for RBAC model JSON envelopes.

Four models: RoleConfig, ModelRoleConfig, ModelLinkConfig, UserProfile.
Mirrors rbac.py structure.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# RoleConfig
# ═══════════════════════════════════════════════════════════════════════

class RoleConfigConfig(ConfigBase):
    """Role-specific config. Permissions are on the model field, not here."""
    pass

class RoleConfigMetadata(MetadataBase):
    pass

class RoleConfigPrefs(RecordPrefsBase):
    pass

class RoleConfigRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class RoleConfigComments(CommentsBase):
    pass

class RoleConfigActions(ActionsBase):
    pass

class RoleConfigSettingDefaults(BaseModel):
    status: str = "active"


# ═══════════════════════════════════════════════════════════════════════
# ModelRoleConfig
# ═══════════════════════════════════════════════════════════════════════

class ModelRoleConfigConfig(ConfigBase):
    """Filter structures are on model fields, not config."""
    pass

class ModelRoleConfigMetadata(MetadataBase):
    pass

class ModelRoleConfigPrefs(RecordPrefsBase):
    pass

class ModelRoleConfigRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class ModelRoleConfigComments(CommentsBase):
    pass

class ModelRoleConfigActions(ActionsBase):
    pass

class ModelRoleConfigSettingDefaults(BaseModel):
    status: str = "active"


# ═══════════════════════════════════════════════════════════════════════
# ModelLinkConfig
# ═══════════════════════════════════════════════════════════════════════

class ModelLinkConfigConfig(ConfigBase):
    """Link config. Template structures are on model fields."""
    pass

class ModelLinkConfigMetadata(MetadataBase):
    pass

class ModelLinkConfigPrefs(RecordPrefsBase):
    pass

class ModelLinkConfigRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class ModelLinkConfigComments(CommentsBase):
    pass

class ModelLinkConfigActions(ActionsBase):
    pass

class ModelLinkConfigSettingDefaults(BaseModel):
    status: str = "active"


# ═══════════════════════════════════════════════════════════════════════
# UserProfile
# ═══════════════════════════════════════════════════════════════════════

class UserProfileConfig(ConfigBase):
    """UserProfile config. Cached roles are on model field."""
    pass

class UserProfileMetadata(MetadataBase):
    pass

class UserProfilePrefs(RecordPrefsBase):
    pass

class UserProfileRefs(RefsBase):
    """Relationship cache. user (OneToOne) and contact FK are truth."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class UserProfileComments(CommentsBase):
    pass

class UserProfileActions(ActionsBase):
    pass

class UserProfileSettingDefaults(BaseModel):
    status: str = "active"
