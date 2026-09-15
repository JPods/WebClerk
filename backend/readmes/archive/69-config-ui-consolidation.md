# config.ui Consolidation — Contact Record UI Preferences

**Created:** 2026-08-16
**Status:** Complete — build passes, not yet deployed

## The Problem

User UI preferences were scattered across five locations:

| Where | What lived there |
|-------|-----------------|
| `Contact.prefs.wcui` | theme, font_size, button_style, phone_display, date_format |
| `Contact.prefs.staff.wcui` | view_mode, font_size (staff overlay) |
| `Contact.prefs.color_mode` / `prefs.staff.color_mode` | zone-specific themes (list/detail dark/light) |
| `Contact.prefs.badge` | bg_color, text_color, initials |
| `Contact.prefs.display` | layout (grid/list/card/table), theme |
| localStorage (`theme`, `wc3_wcui_prefs`, `db-theme`, `wc3_detail_view_pref`) | Client-side cache — sometimes treated as source of truth |
| **Not persisted at all** | navbar config, console position/height |

The `wcuiPrefs.ts` utility used flat keys (`font_size`, `theme`, `detail_view_pref`) stored in a flat localStorage object. The backend service (`wcui_prefs.py`) wrote to `Contact.prefs.staff.wcui`. Multiple files read directly from localStorage with their own parsing logic.

## The Solution

One namespace: `Contact.config.ui`. Hierarchical, clean, everything the user controls about their interface.

```json
{
  "config": {
    "ui": {
      "theme": {
        "active": "dark",
        "dark": {
          "colors": { "text": "#ececec", "surface": "#252526", "accent": "#9cdcfe" },
          "font": { "size": 14 }
        },
        "light": {
          "colors": { "text": "#212529", "surface": "#ffffff", "accent": "#1e40af" },
          "font": { "size": 14 }
        }
      },
      "navbar": {
        "models": ["proposal", "order", "invoice", "purchase", "action"],
        "dashboards": ["dashboard", "products", "transactions", "orgs",
                       "administration", "alice", "kanban", "gantt",
                       "databrowser", "json"]
      },
      "console": {
        "visible": true,
        "position": "bottom",
        "height": 200
      },
      "detail": {
        "auto_edit": true,
        "default_view": "app",
        "collapsed": {}
      },
      "list": {
        "page_size": 50,
        "default_sort": "dt_modified"
      },
      "badge": {
        "bg_color": "",
        "text_color": "",
        "initials": ""
      },
      "format": {
        "button_style": "glass",
        "phone_display": "local",
        "date_format": "MM/DD/YYYY",
        "currency_locale": "en-US"
      },
      "gantt": {
        "scale": "month",
        "font_scale": 0,
        "show_full_text": false,
        "show_all_levels": false
      },
      "dedup": {
        "font_size": 13
      }
    }
  }
}
```

### The Boundary

| Namespace | What lives there | Why |
|-----------|-----------------|-----|
| `config.ui.*` | Everything about how the interface looks and behaves | UI structure is configuration — how this thing works |
| `prefs.notifications` | email, sms, push, frequency | Communication channel choices — not UI |

`config` = how the system is configured for this user. `prefs` = choices the user makes that don't affect the interface (notifications, tags, pins).

## What Was Built

### Backend

**New file:** `apps/core/services/ui_config.py`
- `DEFAULT_UI_CONFIG` — seed structure for new contacts
- `save_ui_config(config_ui, contact_id)` — deep-merge partial updates into `Contact.config.ui`
- `get_ui_config(contact_id)` — return config.ui with defaults filled in
- `migrate_prefs_to_config_ui(contact_id)` — one-time migration from scattered prefs
- `_deep_merge(target, source)` — recursive merge, source wins on leaf conflicts

**Updated:** `apps/core/views/manage_view.py`
- `save_ui_config` — new manage action
- `get_ui_config` — new manage action
- `save_wcui_prefs` — legacy alias, routes through `save_ui_config`

### Frontend

**New file:** `src/utils/contactUI.ts` (replaces `wcuiPrefs.ts`)
- Dot-path deep get/set: `getUI('theme.active')`, `setUI('theme.active', 'light')`
- `setUIBatch({...})` — multiple changes, single debounced server save
- `getUISection(section)` — returns a section with defaults filled in
- `getFullUI()` — complete config.ui with all defaults
- `getActiveTheme()` — convenience for current theme colors + font
- `loadUIFromServer()` — called on login, server wins over localStorage
- `migrateFromWcuiPrefs()` — migrates old localStorage format on startup
- localStorage key: `wc3_config_ui` (was `wc3_wcui_prefs`)
- 1-second debounce on server saves (unchanged from old system)

**Updated files (11):**

| File | What changed |
|------|-------------|
| `context/ThemeContext.tsx` | Sources `theme.active` from `getUI()` instead of localStorage |
| `layout/MacTopBar.tsx` | All controls write via `setUI()`. Removed "Save Prefs" button (auto-saves). Theme selector simplified to dark/light (no zone splits). |
| `context/StaffBadgePrefsContext.tsx` | Reads `config.ui.badge` with `prefs.badge` fallback |
| `pages/admin/DataBrowser.tsx` | Theme, font size, collapsed groups all from `config.ui`. Zone themes unified under `theme.active`. |
| `pages/admin/JsonViewer.tsx` | Theme from `getUI('theme.active')` |
| `pages/admin/CommerceDashboard.tsx` | Theme from `getUI('theme.active')` |
| `pages/Dashboard/DDCardDashboard.tsx` | Theme from `getUI('theme.active')` |
| `apps/utils/gantt/UnifiedGantt.tsx` | Gantt prefs under `config.ui.gantt` |
| `apps/utils/gantt/GanttProjectSelector.tsx` | `show_all_levels` under `config.ui.gantt` |
| `components/common/DedupPanel.tsx` | Font size under `config.ui.dedup` |
| `hooks/useDataBrowser.ts` | Collapsed groups under `config.ui.detail.collapsed` |

## What Was Removed

- **"Save Prefs" button** in MacTopBar — all changes auto-save via debounced server sync. No manual save step.
- **Zone-specific themes** (`color_mode.list`, `color_mode.detail`) — replaced by single `theme.active`. Theme toggle applies everywhere.
- **Direct localStorage reads** — 6+ files had their own `JSON.parse(localStorage.getItem('wc3_wcui_prefs'))` blocks. All replaced by `getUI()`.

## Open Items

| Item | Status |
|------|--------|
| Delete `wcuiPrefs.ts` | Dead code — no imports remain. Delete when ready. |
| Run `migrate_prefs_to_config_ui()` on existing contacts | Backend function exists but not yet run against the database |
| Deploy built assets to Andi | Build passes locally |
| Wire navbar config to UI controls | `config.ui.navbar` defined but no UI to edit it yet |
| Wire console config to UI controls | `config.ui.console` defined but no UI to edit it yet |
| Clean old `wcui_prefs.py` | Kept for now (legacy alias routes through `ui_config.py`) |

## Design Decisions

| Decision | Why |
|----------|-----|
| `config.ui` not `prefs.ui` | Config is "how this thing works." Prefs is "what the user tagged/pinned." UI structure is configuration. |
| Badge in `config.ui` | It's visual interface configuration, not a preference. Other users see it too, but the owner configures it. |
| Format fields in `config.ui.format` | `button_style`, `date_format`, `currency_locale` define how the interface renders data — that's UI config. |
| Notifications stay in `prefs` | Communication channel choices don't affect the interface. Not UI. |
| Font size per-theme | Dark mode at 14px, light mode at 12px — different themes can have different font sizes. Stored in `theme.dark.font.size` and `theme.light.font.size`. |
| Deep-merge on save | Partial updates: `setUI('theme.active', 'light')` doesn't clobber the rest of `theme`. Backend mirrors this with `_deep_merge`. |
| Legacy alias kept | `save_wcui_prefs` still works, routes through `save_ui_config`. No breaking change for any code we missed. |

## Relationship to Other Work

- **Data-Driven UI** (readmes/data-driven-ui.md) — DynamicDetail reads layout JSON from Settings. `config.ui` is the user's side of the same coin: Settings define what's available, `config.ui` defines what the user chose.
- **UI Widget Consolidation** (readmes/68-ui-widget-consolidation.md) — `.db-*` CSS variables are the styling system. `config.ui.theme` provides the values those variables consume.
- **PrefsPanel** (apps/common/components/panels/PrefsPanel.tsx) — still handles `prefs.*` for notifications and user-defined fields. Does not touch `config.ui`.
