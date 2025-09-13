# Admin Workbench (React)

Route: `/admin-wb`

Three-pane layout:

- 20% Models (left)
- 30% Records (middle)
- 50% Detail editor (right)

## Requirements & environment

- Backend root (default): `http://localhost:8000`
- Vite env in the frontend:
  - `VITE_ENV=DEV`
  - `VITE_API_URL=http://localhost:8000` (no `/wcapi` suffix)
  - `VITE_AUTH_API_URL=http://localhost:8000` (optional; falls back to API URL)
- After editing env, restart the dev server.

## Authentication

- All `/wcapi/*` endpoints are protected by JWT (DRF SimpleJWT). You must log in first.
- Login endpoint (JSON): `POST /api/auth/login/` returns `{ data: { access, refresh, ... } }` in an envelope.
- The app stores tokens in `localStorage` and injects `Authorization: Bearer <access>` via `src/api/axios.ts`.
- If a 401 is returned, the client automatically refreshes using `POST /api/token/refresh/` and retries.
- If refresh fails (expired/invalid refresh), the app clears tokens and logs you out.

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

## Troubleshooting

- 401 Unauthorized on `/wcapi/...`:
  - Make sure you’re logged in (valid `accessToken` in localStorage).
  - Confirm `VITE_API_URL` points to backend ROOT (no `/wcapi`).
  - Check the request has `Authorization: Bearer <access>` header.
  - If still failing, clear tokens and log in again (the client will auto-logout on bad refresh).
- 404 Not Found on `/wcapi/...`:
  - Ensure you didn’t double-prefix `/api`. The client will fall back to `/api/wcapi/...` when the root path is missing; keep `VITE_API_URL` clean.

## Related tools

- Use the in-app Whitelist Tester at `/whitelist` to probe endpoints like `/wcapi/model_name/list/` and `/wcapi/get/?model_name=item&limit=10`.
