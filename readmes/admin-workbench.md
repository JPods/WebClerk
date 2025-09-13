# Admin Workbench (React)

Route: `/admin-wb`

Three-pane layout:

- 20% Models (left)
- 30% Records (middle)
- 50% Detail editor (right)

## Data flow

- Loads model list from backend `/wcapi/model_name/list/` via `getModelNames()`
- When a model is selected:
  - Loads model detail/fields via `getModelDetail(model_name)`
  - Loads records list via `getRecords(model_name)`
  - Selecting a record loads detail via `getRecord(model_name, id)`

## Field selectors (bottom of middle/right panes)

- Buttons represent fields and highlight when visible in the pane above.
- Click to add/remove a field.
- List pane default columns: `id`, `ida`, `name`, `email` (used only until you toggle; then your prefs are used).
- Detail pane defaults to all fields until you toggle.
- Preferences persist per model in localStorage via `loadFieldSelections`/`saveFieldSelections`.

## Save

- Edits are saved with `saveRecord(model, payload)`. Objects are stringified in the editor.

## Notes

- Ensure Vite env `VITE_API_URL` points to backend ROOT (no trailing `/wcapi`). The SDK adds `/wcapi/...` paths. A double prefix causes 404s.
