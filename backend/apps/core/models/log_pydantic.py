"""
Pydantic schemas for APILog and UserDailyLog JSON envelopes.

Mirrors log.py structure — both log models in one file.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import (
    ConfigBase, MetadataBase, RecordPrefsBase, RefsBase,
    CommentsBase, ActionsBase, SourceRef,
)


# ═══════════════════════════════════════════════════════════════════════
# ApiLog (Django class: APILog)
# ═══════════════════════════════════════════════════════════════════════

class ApiLogConfig(ConfigBase):
    """ApiLog config. Request/response data on model fields."""
    pass

class ApiLogMetadata(MetadataBase):
    pass

class ApiLogPrefs(RecordPrefsBase):
    pass

class ApiLogRefs(RefsBase):
    """Relationship cache. user FK is truth."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class ApiLogComments(CommentsBase):
    pass

class ApiLogActions(ActionsBase):
    pass

class ApiLogSettingDefaults(BaseModel):
    status: str = "active"


# ═══════════════════════════════════════════════════════════════════════
# UserDailyLog
# ═══════════════════════════════════════════════════════════════════════

class UserDailyLogConfig(ConfigBase):
    """UserDailyLog config. Aggregated data on model fields."""
    pass

class UserDailyLogMetadata(MetadataBase):
    pass

class UserDailyLogPrefs(RecordPrefsBase):
    pass

class UserDailyLogRefs(RefsBase):
    """Relationship cache. user FK is truth."""
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None

class UserDailyLogComments(CommentsBase):
    pass

class UserDailyLogActions(ActionsBase):
    pass

class UserDailyLogSettingDefaults(BaseModel):
    status: str = "active"
