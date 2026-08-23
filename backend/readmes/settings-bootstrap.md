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

## Design Decisions

- **webclerk.com IS the path** — hardcoded, not configurable. No token, no fetch.
- **No "continue anyway"** — fix it or don't run.
- **UUID merge control** — every Setting has a UUID. Pack includes it. Unpack matches by UUID.
- **Prefs never touched** — user's space is sovereign.
- **Baseline merge** — HQ adds structure, never removes or replaces user data.
- **Server-to-server** — WC3 backend calls webclerk.com. React never touches webclerk.com directly. Athena token stays server-side.
