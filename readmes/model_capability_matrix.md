# Model capability matrix

This document summarizes model composition discovered by scanning the codebase (apps/*) and the canonical capability definitions in [`common/models.py`](common/models.py:1).

Scan notes:
- Registry / WCAPI: [`apps/core/wcapi/urls.py`](apps/core/wcapi/urls.py:1) and [`apps/core/services/wcapi_registry.py`](apps/core/services/wcapi_registry.py:1).
- Universal Base definitions: [`common/models.py`](common/models.py:1).
- Save endpoint reference: [`apps/core/views/save_view.py`](apps/core/views/save_view.py:1).

Key:
- CoreModel: minimal identity + version/timestamps (feature_flags: core)
- BaseModel: full composition; includes feature_flags: metadata, refs, prefs, comments, actions, keywords, atomic_json, health, lifecycle, universal_dict (see [`common/models.py`](common/models.py:987))

High-level findings
- Most domain models inherit BaseModel → they receive the full envelope and atomic helpers.
- A few specialized models are CoreModel-only (ephemeral / queue) — e.g. [`apps/core/models/pending.py`](apps/core/models/pending.py:6).

Capability table (representative sample)

| App | Model | Inherits | Capabilities (summary) |
|-----|-------|----------|-----------------------|
| core | Action | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| core | Pending | CoreModel | core (id, uuid, ida, dt_created, dt_modified, version) |
| core | Setting | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| communications | Email | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| communications | Phone | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| communications | Location | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| docs | Document | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| products | Catalog | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |
| transactions | TransactionBaseModel | BaseModel | metadata, refs, prefs, comments, actions, keywords, atomic_json, lifecycle, health, universal_dict |

Notes and caveats
- The table above is a representative sample produced from static scanning. Because `BaseModel` composes many mixins, any model subclassing `BaseModel` will inherit those capabilities by default (see [`common/models.py`](common/models.py:987)).
- Some models may override or intentionally omit particular JSON fields; a per-file read confirms overrides (e.g., fields declared explicitly in model file).
- Feature flags are discoverable at runtime with `common.models.model_capabilities(Model)` — this is the most accurate method if you want exact flags per model instance.

Next steps I can run (choose one)
- Expand this matrix to include every model file (produce CSV / full markdown with one row per model).
- Run runtime introspection (Django script) to call `model_capabilities` for every registered model and generate a definitive CSV.
- Start designing migration plan for moving some models from BaseModel -> CoreModel+selected mixins (suggest candidates).

I recommend generating the full per-model matrix next so we have a precise target list for migration and tests.