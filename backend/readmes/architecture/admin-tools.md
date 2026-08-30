# Admin Tools — Report-Driven Utility Runner

## What This Is

Admin utility tools (audits, seeds, system checks) are **Report records** with `category='utility'`, `model_name='setting'`. Each Report maps to a management command. The frontend runs them via `/wcapi/manage/` action `run_admin_tool`. No custom admin pages — the existing Report model handles discovery, sync, Alice tracking, and configuration.

## Architecture

```
Report record (category=utility, model_name=setting)
    ↓ config.command + config.parameters
AdminTools page (/admin-tools)
    ↓ POST /wcapi/manage/ {action: run_admin_tool, params: {command, args}}
manage_view.py → _run_admin_tool()
    ↓ allowlist check → call_command()
Management command (--json output)
    ↓ captured stdout
JSON result → AdminTools result viewer
```

## Why Reports

- **Discoverable** — show up in Reports list filtered by category
- **Syncable** — new installations get the tools via Bundle
- **Alice-trackable** — she sees which tools are run, how often, by whom
- **Configurable** — parameters in `config` (model, force, detail flags)
- **No new UI pattern** — the AdminTools page is a generic runner for any Report with category=utility

## Security

- `run_admin_tool` is in `_STAFF_ONLY_ACTIONS` — requires `is_staff` or `is_superuser`
- Commands must be in `_ADMIN_TOOL_COMMANDS` allowlist (manage_view.py) — prevents arbitrary command execution
- AdminTools page checks `user.is_superuser` before rendering
- Report records have `role_required='admin'`

## Current Tools

| Report ida | Command | What it does |
|-----------|---------|-------------|
| `admin-tool-audit-field-behaviors` | `audit_field_behaviors` | Flag misdetected field types across all models |
| `admin-tool-audit-select-lists` | `audit_select_lists` | Export/review all select lists by model and source |
| `admin-tool-seed-model-definitions` | `seed_model_definitions` | Regenerate wc:model Settings from model metadata |
| `admin-tool-seed-company-settings` | `seed_company_settings` | Create/update company profile Setting |

## Adding a New Tool

1. **Write the management command** with `--json` output support
2. **Add to allowlist** in `manage_view.py` → `_ADMIN_TOOL_COMMANDS`
3. **Add a Report record** to `seed_admin_tool_reports.py` with:
   - `ida`: `admin-tool-{command-name}`
   - `config.command`: the management command name
   - `config.default_args`: default CLI arguments (usually `['--json']`)
   - `config.parameters`: UI parameter definitions (name, type, label, default)
4. **Run** `python manage.py seed_admin_tool_reports`

The tool appears automatically in the AdminTools page.

## Report.config Structure

```json
{
  "command": "audit_field_behaviors",
  "default_args": ["--json"],
  "parameters": [
    {"name": "model", "type": "text", "label": "Model (blank=all)", "required": false},
    {"name": "detail", "type": "boolean", "label": "Show detail", "default": false}
  ]
}
```

Parameter types: `text` (adds `--name value` to args), `boolean` (adds `--name` flag when checked).

## Key Files

| File | What |
|------|------|
| `apps/core/management/commands/seed_admin_tool_reports.py` | Seeds Report records |
| `apps/core/views/manage_view.py` | `_run_admin_tool` handler + allowlist |
| `React2025/src/pages/admin/AdminTools.tsx` | UI: card selector + parameter inputs + result viewer |
| `React2025/src/pages/admin/AdminTools.css` | Styling |
| `React2025/src/routes/Router.tsx` | Route: `/admin-tools` |
| `React2025/src/routes/protectedRoutesConfig.tsx` | WindowManager route |

## Connection to Field Behaviors

The admin tools page is the primary UI for the field behaviors correction loop:

1. Run **Audit Field Behaviors** → see flagged fields
2. Go to DataBrowser → **Cmd+Shift+click** on a flagged field label → override dialog
3. Save override → behaviors reload automatically
4. Run audit again to verify

The **Audit Select Lists** tool complements this by showing which select options exist, where they come from (service hardcoded vs Setting override), and whether the same field name has different options on different models (DRIFT flag).

## Flight Simulator Integration

The admin tools appear as a simulation type in the Flight Simulator. The flight sim card walks the user through:
1. Opening the AdminTools page
2. Running an audit
3. Reviewing the results
4. Cmd+Shift+clicking a field to fix it
5. Running the audit again to verify the fix
