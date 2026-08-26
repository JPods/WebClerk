"""
Pydantic schemas for Setting JSON envelopes.

Inherits standard bases. Add model-specific fields only.

Settings with purpose='wc:model' use config.layout to store layouts:

  config.layout.active       — which named layout is selected per type
  config.layout.list.*       — named list layouts (toolbar grid + pairings)
  config.layout.column.*     — named column layouts (panel grid, no toolbar)
  config.layout.detail.*     — named detail layouts (all fields, collapsible groups + pairings)
  config.layout.form.*       — named form layouts (curated business forms — cards, tabs, lines + pairings)
  config.layout.panel[]      — panel field specs (not paired)
  config.layout.card{}       — named card definitions (not paired)

Terms established 2026-08-18. See db-layout-schema.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── DataBrowser layout types ─────────────────────────────────────────────

class DbFieldSpec(BaseModel):
    """One field in a list, column, or detail layout.

    Layout properties only — which fields, how wide, how arranged.
    Behavioral properties (type, widget, precision) belong in the Pydantic
    schema via json_schema_extra.  The renderer reads from the schema first;
    ``format`` here is an optional user-preference override for cases where
    one layout wants a different display (e.g. currency in one view, plain
    number in another).  When format is None the schema is authoritative.
    """
    field: str
    width: Optional[int] = None              # px — user sets via drag or type
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    align: Optional[Literal['left', 'center', 'right']] = None
    visible: bool = True
    # User-preference display override.  Schema (json_schema_extra.widget)
    # is the authority; this overrides only when explicitly set per layout.
    format: Optional[Literal[
        'currency', 'percent', 'date', 'number',
        'json', 'phone', 'masked'
    ]] = None
    wrap: bool = False                       # true = word-wrap, false = ellipsis
    frozen: bool = False                     # sticky left
    summary: Optional[Literal['sum', 'avg', 'count']] = None
    alice_note: Optional[str] = None         # Alice's annotation

    class Config:
        extra = 'forbid'


class NamedListLayout(BaseModel):
    """A named list layout — toolbar grid columns + pairings to detail and form."""
    detail: str = 'default'                  # paired detail layout name
    form: str = 'default'                    # paired form layout name
    columns: List[DbFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class NamedColumnLayout(BaseModel):
    """A named column layout — panel grid (no toolbar) + pairings."""
    detail: str = 'default'                  # paired detail layout name
    form: str = 'default'                    # paired form layout name
    columns: List[DbFieldSpec] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class NamedDetailLayout(BaseModel):
    """A named detail layout — all fields, collapsible groups + pairings to list and form.

    The 'sections' field holds the DynamicDetail definition (model, family,
    sections[], edit_rules). It's typed as Any because DynamicDetail schemas
    are complex and defined elsewhere.
    """
    list: str = 'default'                    # paired list layout name
    form: str = 'default'                    # paired form layout name
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

    Cards are the building blocks of form layouts. Most cards are pure JSON
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


class FormHeader(BaseModel):
    """Header section of a form layout — arranges cards."""
    layout: str = 'columns'                  # columns, rows, stacked
    cards: List[str] = Field(default_factory=list)  # card names from layout.card

    class Config:
        extra = 'allow'


class FormLines(BaseModel):
    """Line items section of a form layout."""
    family: Optional[str] = None             # sell, exec
    toolbar: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)

    class Config:
        extra = 'allow'


class FormTab(BaseModel):
    """A tab in a form layout."""
    label: str
    content: str                             # panel name: summary, actions, documents, etc.

    class Config:
        extra = 'allow'


class EditRules(BaseModel):
    """Edit locking rules for a form layout."""
    locked_statuses: List[str] = Field(default_factory=list)
    status_field: str = 'status'
    require_unlock_for: List[str] = Field(default_factory=list)

    class Config:
        extra = 'allow'


class NamedFormLayout(BaseModel):
    """A named form layout — curated business form (cards, tabs, lines, edit rules).

    Pairings to list and detail. The form layout drives header cards,
    line items, tabs, and edit rules for the full detail view in App mode.
    """
    list: str = 'default'                    # paired list layout name
    detail: str = 'default'                  # paired detail layout name
    header: Optional[FormHeader] = None
    lines: Optional[FormLines] = None
    tabs: List[FormTab] = Field(default_factory=list)
    edit_rules: Optional[EditRules] = None

    class Config:
        extra = 'allow'                      # form layouts carry diverse keys


class ActiveLayout(BaseModel):
    """Tracks which named layout is currently selected per type."""
    list: str = 'default'
    column: str = 'default'
    detail: str = 'default'
    form: str = 'default'

    class Config:
        extra = 'forbid'


class LayoutConfig(BaseModel):
    """Layout configuration — lives at config.layout on wc:model Settings.

    Four paired types — each named layout declares which layouts it pairs
    with in the other types. Pick any one, the others follow.
      - list    — toolbar grid (DataBrowser main view)
      - column  — panel grid (no toolbar, hamburger to configure)
      - detail  — all fields, collapsible groups (Admin mode)
      - form    — curated business form with cards, tabs, lines (App mode)

    Two unpaired types (panel, card) — always rendered in their specific
    context regardless of which paired layout is active.

    Terms established 2026-08-18. See db-layout-schema.md.
    """
    active: ActiveLayout = Field(default_factory=ActiveLayout)
    list: Dict[str, NamedListLayout] = Field(default_factory=lambda: {'default': NamedListLayout()})
    column: Dict[str, NamedColumnLayout] = Field(default_factory=lambda: {'default': NamedColumnLayout()})
    detail: Dict[str, NamedDetailLayout] = Field(default_factory=lambda: {'default': NamedDetailLayout()})
    form: Dict[str, NamedFormLayout] = Field(default_factory=lambda: {'default': NamedFormLayout()})
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
