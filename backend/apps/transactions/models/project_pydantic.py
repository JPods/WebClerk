"""
Pydantic schemas for Project JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class ProjectConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class ProjectMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class ProjectActionPrefs(BaseModel):
    """Auto-assigned palette color for project's actions."""
    color: str = ''                           # e.g. 'blue-500' — from PROJECT_COLOR_PALETTE

    class Config:
        extra = 'forbid'


class ProjectGanttPrefs(BaseModel):
    """Gantt lane display weight. 0=hidden, 3=normal, 4-5=pinned."""
    weight: int = 3                           # 0 for child projects, 3 for top-level

    class Config:
        extra = 'forbid'


class ProjectPrefs(RecordPrefsBase):
    """Project prefs. Color and Gantt weight auto-assigned on save."""
    action: ProjectActionPrefs = Field(default_factory=ProjectActionPrefs)
    gantt: ProjectGanttPrefs = Field(default_factory=ProjectGanttPrefs)


# -- .refs (inherits RefsBase) ----------------------------------------------

class ProjectRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
