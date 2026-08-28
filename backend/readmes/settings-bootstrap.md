# Settings Bootstrap Architecture

Settings are the operating system. Running without them is undefined behavior.

## Overview

Every WC3 installation requires a complete, healthy set of Setting records. On startup, the React app runs a health check. If Settings are missing or corrupt, the app blocks with a bootstrap dialog — no dismiss, no skip, no "remind me later."

## Three Sources

| Source | Path | Auth | When |
|--------|------|------|------|
| **WC_HQ API** | `webclerk.com/wcapi/settings-bundle/` | Athena token | Primary — DB is master |
| **Git snapshot** | `settings-bundle.json` in repo | None (local file) | Fallback — offline use |
| **Seed commands** | `manage.py seed_model_definitions` | None | Initial dev setup |

WC_HQ database is the master. Git file is a snapshot for offline/fallback. They deliver the same data through different pipes.

## Startup Flow

```
React App mounts
    │
    ├── GET /wcapi/settings-health/
    │       │
    │       ├── healthy=true → render app
    │       │
    │       └── healthy=false → BLOCK
    │               │
    │               ├── Show: what's wrong (missing + corrupt list)
    │               │
    │               ├── [Fix from Git] → file picker → upload settings-bundle.json
    │               │       → POST /wcapi/settings-bootstrap/
    │               │       → re-check health
    │               │
    │               ├── [Fix from WC_HQ] → enter Athena token
    │               │       → POST /wcapi/settings-fetch-hq/
    │               │       → WC3 backend calls webclerk.com/wcapi/settings-bundle/
    │               │       → re-check health
    │               │
    │               └── [Quit] → app stops
```

## Merge Rule

**Baseline merge: add missing keys, never replace existing.**

WC_HQ provides the baseline structure. User customizations always win.

| Field | Merge behavior |
|-------|---------------|
| `config` | Deep merge — HQ fills gaps, user's existing keys preserved |
| `metadata` | Deep merge — same |
| `refs` | Deep merge — same |
| `prefs` | Never touched — user's space |
| `explanation` | Only if user's is empty |
| `paths` | Only if user's is empty |
| Scalar fields (name, scope, purpose, parent_model) | Only if currently empty |

This handles the divergence problem: WC_HQ settings evolve independently from each installation's customizations. New keys from HQ appear silently. Existing keys are never overwritten.

## Pack (WC_HQ side)

```bash
# Export DB → git snapshot
python manage.py pack_settings_bundle --validate

# Options
--output /path/to/file.json    # custom path (default: settings-bundle.json)
--dry-run                       # show what would be exported
--validate                      # run health check after packing
```

The bundle contains all active Setting records with UUIDs for merge control:

```json
{
  "version": "1.0",
  "source": "pack_settings_bundle",
  "dt_exported": "2026-08-15T18:07:18+00:00",
  "record_count": 87,
  "settings": [
    {
      "uuid": "...",
      "ida": "wc-model-contact",
      "purpose": "wc:model",
      "parent_model": "contact",
      "config": { ... },
      "metadata": { ... },
      "prefs": { ... },
      "refs": { ... },
      "explanation": "Model definition for contact — governs field access...",
      "paths": {"schema": "common/schemas/contact.py", "model": "apps/core/models/contact.py"}
    }
  ]
}
```

## Unpack (user side)

```bash
# Import from file
python manage.py unpack_settings_bundle --validate

# Options
--input /path/to/file.json     # custom path (default: settings-bundle.json)
--dry-run                       # show what would change
--validate                      # run health check after unpacking
```

## API Endpoints

| Method | Path | Auth | Body | Purpose |
|--------|------|------|------|---------|
| GET | `/wcapi/settings-health/` | None | — | Health check report |
| POST | `/wcapi/settings-bootstrap/` | None | Settings bundle JSON | Import from file |
| POST | `/wcapi/settings-fetch-hq/` | None* | `{"athena_token": "..."}` | Fetch from WC_HQ |

*The endpoint itself doesn't require auth (database may be empty). The Athena token is passed in the body and used server-side to authenticate with webclerk.com.

## Health Check

`check_settings_health()` validates:

1. **System Settings exist** — company_profile, admin, system, dd_card
2. **Model Settings exist** — one `wc:model` per registered model
3. **Structural health** — every Setting has required metadata keys (history, flags, userdefined, images), prefs keys (userdefined, tags, pinned, search), refs keys (keywords, tags, links), and purpose-specific config keys

Returns `{healthy, total, missing, corrupt, summary}`.

## Files

| File | What it does |
|------|-------------|
| `apps/core/services/settings_health.py` | Health check function |
| `apps/core/services/settings_bootstrap.py` | Import bundle + WC_HQ fetch |
| `apps/core/views/settings_bootstrap_view.py` | Three API endpoints |
| `apps/core/management/commands/pack_settings_bundle.py` | DB → git snapshot |
| `apps/core/management/commands/unpack_settings_bundle.py` | Git snapshot → DB |
| `React2025/src/components/SettingsBootstrap.tsx` | Blocking startup dialog |
| `settings-bundle.json` | The canonical bundle (git-tracked) |

## Setting Protection Wall

Settings represent days of careful refinement — layouts, behaviors, selectlists, schema maps. They are protected against accidental or automated modification.

### Three Layers

1. **Model-level guard** — `Setting.save()` blocks any `config` change on existing records unless `_setting_update_authorized = True` is set on the instance. Unauthorized attempts raise `ValidationError` and log a WARNING.

2. **Enforcement exclusion** — `audit_schema_compliance --enforce` skips the `setting` model entirely. Schema enforcement never touches Settings.

3. **Bundle confirmation** — `unpack_settings_bundle --replace` requires double confirmation:
   - First: "Are you sure?" (yes/no)
   - Second: Type "REPLACE" to confirm

### Approved Paths Through the Wall

| Path | Authorization | Use Case |
|------|--------------|----------|
| `unpack_settings_bundle` | Auto-authorized (approved bootstrap) | Restore from bundle |
| `unpack_settings_bundle --replace` | Double confirmation + auto-authorized | Full restore from known-good state |
| `settings-bootstrap` API | Auto-authorized (startup recovery) | React health-check dialog |
| `fetch_from_wchq` | Auto-authorized (WC_HQ source) | Fetch from headquarters |
| `seed_model_definitions` | Auto-authorized (initial setup) | First-time dev setup |
| Direct ORM with flag | `record._setting_update_authorized = True` | Code that knows what it's doing |

### What Triggers the Wall

```python
# This FAILS with ValidationError:
setting.config['layout']['list']['default'] = new_columns
setting.save(update_fields=['config', 'dt_modified'])

# This WORKS — explicit authorization:
setting._setting_update_authorized = True
setting.config['layout']['list']['default'] = new_columns
setting.save(update_fields=['config', 'dt_modified'])
# Flag auto-resets after save
```

### Recovery from Corruption

If Settings are corrupted or missing:

```bash
# Option 1: Baseline merge (adds missing, preserves existing)
python manage.py unpack_settings_bundle

# Option 2: Full replace (double confirmation required)
python manage.py unpack_settings_bundle --replace

# Option 3: React startup dialog (blocks app, offers fix)
# Browser shows health check results + fix buttons
```

The bundle file (`settings-bundle.json`) is git-tracked. After any successful Setting refinement session, re-pack:

```bash
python manage.py pack_settings_bundle --validate
```

## Design Decisions

- **webclerk.com IS the path** — hardcoded, not configurable. No token, no fetch.
- **No "continue anyway"** — fix it or don't run.
- **UUID merge control** — every Setting has a UUID. Pack includes it. Unpack matches by UUID.
- **Prefs never touched** — user's space is sovereign.
- **Baseline merge** — HQ adds structure, never removes or replaces user data.
- **Server-to-server** — WC3 backend calls webclerk.com. React never touches webclerk.com directly. Athena token stays server-side.
