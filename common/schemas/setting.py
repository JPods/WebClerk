"""
Pydantic schemas for Setting JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Settings with purpose='wc:model' use config.layout to store layouts:

  config.layout.active       — which named layout is selected per type
  config.layout.list.*       — named list layouts (toolbar grid + pairings)
  config.layout.column.*     — named column layouts (panel grid, no toolbar)
  config.layout.dynamic.*    — named dynamic layouts (DynamicDetail sections + pairings)
  config.layout.display.*    — named display layouts (JSON-driven detail pages + pairings)
  config.layout.panel[]      — panel field specs (not paired)
  config.layout.card[]       — card field specs (not paired)
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── DataBrowser layout types ─────────────────────────────────────────────

class DbFieldSpec(BaseModel):
    """One field in a list, column, or dynamic layout."""
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


class NamedListLayout(BaseModel):
    """A named list layout — toolbar grid columns + pairings to dynamic and display."""
    dynamic: str = 'default'                 # paired dynamic layout name
    display: str = 'default'                 # paired display layout name
    columns: List[DbFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class NamedColumnLayout(BaseModel):
    """A named column layout — panel grid (no toolbar) + pairings."""
    dynamic: str = 'default'                 # paired dynamic layout name
    display: str = 'default'                 # paired display layout name
    columns: List[DbFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class NamedDynamicLayout(BaseModel):
    """A named dynamic layout — DynamicDetail sections + pairings to list and display.

    The 'sections' field holds the DynamicDetail definition (model, family,
    sections[], edit_rules). It's typed as Any because DynamicDetail schemas
    are complex and defined elsewhere.
    """
    list: str = 'default'                    # paired list layout name
    display: str = 'default'                 # paired display layout name
    sections: Any = None                     # DynamicDetail definition dict

    class Config:
        extra = 'allow'                      # DynamicDetail carries diverse keys


class CardFieldSpec(BaseModel):
    """One field inside a card definition."""
    field: str
    label: Optional[str] = None
    type: Optional[str] = None               # select, readonly, editable, search, action
    options: Optional[List[str]] = None      # for select fields
    help: Optional[str] = None               # Shift+hover tooltip

    class Config:
        extra = 'allow'


class CardSpec(BaseModel):
    """A reusable card definition — named block of fields with optional component override.

    Cards are the building blocks of db.display layouts. Most cards are pure JSON
    (fields rendered via FieldRow). Cards that need interactive behavior reference
    a registered React component by name.
    """
    title: str
    title_ida: Optional[str] = None          # field name for ID badge (e.g. "customer_id")
    component: Optional[str] = None          # registered React component name
    footer: Optional[str] = None             # registered footer component name
    source: Optional[str] = None             # dot-path prefix for all fields
    fields: List[CardFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'allow'


class DisplayHeader(BaseModel):
    """Header section of a display layout — arranges cards."""
    layout: str = 'columns'                  # columns, rows, stacked
    cards: List[str] = Field(default_factory=list)  # card names from layout.card

    class Config:
        extra = 'allow'


class DisplayLines(BaseModel):
    """Line items section of a display layout."""
    family: Optional[str] = None             # sell, exec
    toolbar: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)

    class Config:
        extra = 'allow'


class DisplayTab(BaseModel):
    """A tab in a display layout."""
    label: str
    content: str                             # panel name: summary, actions, documents, etc.

    class Config:
        extra = 'allow'


class EditRules(BaseModel):
    """Edit locking rules for a display layout."""
    locked_statuses: List[str] = Field(default_factory=list)
    status_field: str = 'status'
    require_unlock_for: List[str] = Field(default_factory=list)

    class Config:
        extra = 'allow'


class NamedDisplayLayout(BaseModel):
    """A named display layout — JSON-driven detail page (replaces *DetailJson.tsx hardcoding).

    Pairings to list and dynamic. The display layout drives header cards,
    line items, tabs, and edit rules for the full detail view.
    """
    list: str = 'default'                    # paired list layout name
    dynamic: str = 'default'                 # paired dynamic layout name
    header: Optional[DisplayHeader] = None
    lines: Optional[DisplayLines] = None
    tabs: List[DisplayTab] = Field(default_factory=list)
    edit_rules: Optional[EditRules] = None

    class Config:
        extra = 'allow'                      # display layouts carry diverse keys


class ActiveLayout(BaseModel):
    """Tracks which named layout is currently selected per type."""
    list: str = 'default'
    column: str = 'default'
    dynamic: str = 'default'
    display: str = 'default'

    class Config:
        extra = 'forbid'


class LayoutConfig(BaseModel):
    """Layout configuration — lives at config.layout on wc:model Settings.

    Four paired types — each named layout declares which layouts it pairs
    with in the other types. Pick any one, the others follow.
      - list    — toolbar grid (DataBrowser main view)
      - column  — panel grid (no toolbar, hamburger to configure)
      - dynamic — DynamicDetail sections (form builder)
      - display — JSON-driven detail page (ContactDetailJson pattern)

    Two unpaired types (panel, card) — always rendered in their specific
    context regardless of which paired layout is active.
    """
    active: ActiveLayout = Field(default_factory=ActiveLayout)
    list: Dict[str, NamedListLayout] = Field(default_factory=lambda: {'default': NamedListLayout()})
    column: Dict[str, NamedColumnLayout] = Field(default_factory=lambda: {'default': NamedColumnLayout()})
    dynamic: Dict[str, NamedDynamicLayout] = Field(default_factory=lambda: {'default': NamedDynamicLayout()})
    display: Dict[str, NamedDisplayLayout] = Field(default_factory=lambda: {'default': NamedDisplayLayout()})
    panel: List[DbFieldSpec] = Field(default_factory=list)
    card: Dict[str, CardSpec] = Field(default_factory=dict)
    related: List[str] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


# -- .config ----------------------------------------------------------------

class SettingConfig(ConfigBase):
    layout: Optional[LayoutConfig] = None

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
    categories: list[str] = Field(default_factory=list)
    parents: list = Field(default_factory=list)
    depends_on: dict = Field(default_factory=dict)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None
