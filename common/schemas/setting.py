"""
Pydantic schemas for Setting JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Settings with purpose='wc:workbench_fields' use config.db to store
DataBrowser layouts:
  config.db.list[]   — columns visible in the list view
  config.db.detail[] — fields visible in the detail view
  config.db.panel[]  — columns shown in embedded panels (related records, line items)
  config.db.views[]  — named layout snapshots
"""
from __future__ import annotations

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── DataBrowser layout types ─────────────────────────────────────────────

class DbFieldSpec(BaseModel):
    """One field in a list or detail layout."""
    field: str
    width: Optional[int] = None              # px — user sets via drag or type
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    align: Optional[Literal['left', 'center', 'right']] = None
    visible: bool = True
    format: Optional[Literal[
        'currency', 'percent', 'date', 'number',
        'json', 'phone', 'masked'
    ]] = None
    wrap: bool = False                       # true = word-wrap, false = ellipsis
    frozen: bool = False                     # sticky left
    summary: Optional[Literal['sum', 'avg', 'count']] = None
    alice_note: Optional[str] = None         # Alice's annotation
    type_hint: Optional[str] = None          # override auto-detected widget type

    class Config:
        extra = 'forbid'


class DbNamedView(BaseModel):
    """A named layout snapshot — saved set of all four layout types."""
    name: str
    list: List[DbFieldSpec] = Field(default_factory=list)
    detail: List[DbFieldSpec] = Field(default_factory=list)
    panel: List[DbFieldSpec] = Field(default_factory=list)
    card: List[DbFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class DbLayout(BaseModel):
    """DataBrowser layout — lives at config.db on workbench_fields Settings.

    Four layout types:
      list   — columns in the list/grid view
      detail — fields in the record detail view
      panel  — columns shown in embedded panels (related records, line items)
      card   — fields shown in card/tile view
    """
    list: List[DbFieldSpec] = Field(default_factory=list)
    detail: List[DbFieldSpec] = Field(default_factory=list)
    panel: List[DbFieldSpec] = Field(default_factory=list)
    card: List[DbFieldSpec] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)  # FK model names to show as panels in detail
    views: List[DbNamedView] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


# -- .config ----------------------------------------------------------------

class SettingConfig(ConfigBase):
    db: Optional[DbLayout] = None

    class Config:
        extra = 'allow'  # Settings carry diverse config by purpose


# -- .metadata (inherits MetadataBase) --------------------------------------

class SettingMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class SettingPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class SettingRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None
