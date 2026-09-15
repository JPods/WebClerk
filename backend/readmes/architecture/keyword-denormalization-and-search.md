# Keyword Denormalization and Search Contract

Action: Define and enforce keyword-first list search contract for wcapi/get with denormalized refs.keywords.
Function: WCAPIGetView._parse_search + WCAPIGetView._apply_search + update_keywords() + audit_refs_templates.
Frequency: On every list-search feature change and after schema/keyword-field changes.
Process: Write/update keyword fields -> denormalize refs.keywords on save/maintenance -> query with keyword param -> verify with audit/readme checks.

## Purpose

This readme defines the contract between r25 and wc3 for keyword-driven list search.

- Frontend sends: /wcapi/get/?model_name=[model]&keyword=this,that,other
- Backend parses keyword exactly like search/q aliases.
- Query behavior uses comma-separated AND fragments.
- refs.keywords is the denormalized index used for resilient matching.

## API Contract

Preferred query parameter:

- keyword

Backward-compatible aliases:

- search
- q

Saved search selectors:

- saved_search_id
- saved_search

Contract examples:

- /wcapi/get/?model_name=customer&keyword=acme
- /wcapi/get/?model_name=customer&keyword=acme,west
- /wcapi/get/?model_name=item&keyword=@widget

Fragment semantics:

- acme means prefix-style fragment matching in configured fields.
- @acme means contains matching.
- acme,west means AND logic (both fragments must match).

## Denormalization Source

Keyword matching depends on refs.keywords being populated and refreshed.

Primary mechanisms:

- Base model keyword update flow: update_keywords()
- Save path keyword refresh in wcapi/save
- Scheduled refresh for pending keyword updates
- Field/template governance in settings and link defaults

When refs.keywords drifts from FK/scalar source fields, search quality degrades.

## Alice-Assisted Operations

Alice should assist with visibility, audit notes, and maintenance outcomes.

Recommended operations:

1. Run refs template audit:

- python manage.py audit_refs_templates

1. Run communication/contact reconciliation when applicable:

- python manage.py contact_communications_maintenance

1. Keep Alice logging enabled during these runs unless explicitly debugging without it.

1. Capture outcomes in alice_log/alice_pending for schema gaps, data drift, and action items.

## Saved Search Governance

Saved searches are role-shared and global admin-managed.

- Storage model: setting
- Setting.purpose: search
- Setting.parent_model: canonical model key (for example, customer, item, invoice)
- Setting.role: role allowed to use this search (or all/*/blank for shared)

Execution rules:

- Non-admin users may only apply a saved search when Setting.role matches their role (or role is open).
- Admin users may apply any saved search.
- Saved search params are merged as defaults; explicit request params override them.

Recommended data payload shape:

```json
{
  "keyword": "acme,@west",
  "search_fields": ["company", "display_name", "email"],
  "filters": {
    "status": "active",
    "is_active": true
  },
  "ordering": "-dt_modified",
  "pagination": {
    "limit": 50,
    "offset": 0
  },
  "request_keyword": "assigned_to",
  "request_filters": {
    "begin": {"field": "dt_created", "lookup": "gte"},
    "end": {"field": "dt_created", "lookup": "lte"}
  },
  "relative_period": {
    "field": "dt_created",
    "preset": "current_month"
  }
}
```

Preset runtime rules:

- Explicit request params still win.
- request_keyword reads a named request param and uses it as the keyword search input when keyword/search/q is not already present.
- request_filters maps named request params into validated model filters.
- relative_period currently supports current_month and current_quarter for epoch-ms fields such as dt_created.

Standard seeded presets:

- Transaction header models: in_period, current_month, current_quarter
- Action: assigned_to_in_period, assigned_to_is_active, assigned_to_is_active_priority

Seed command:

- python manage.py seed_search_presets

## Implementation Notes

r25:

- Shared wcapi client normalizes list search params to keyword.
- Legacy callers still passing search or q are mapped to keyword at request time.

wc3:

- WCAPIGetView accepts keyword/search/q as equivalent search input.
- Search applies fragment parsing and includes refs.keywords matching.

## Verification Checklist

1. r25 network request uses keyword in wcapi/get list call.
2. wc3 returns expected filtered rows for single and comma-separated fragments.
3. refs.keywords exists and is non-empty for representative records.
4. audit_refs_templates completes with no blocking gaps for active models.
5. At least one automated test covers keyword query parameter behavior.

## Related Docs

- readmes/topics/architecture/refs-denormalization-playbook.md
- common/search_utils.py
- apps/core/views/wcapi.py
