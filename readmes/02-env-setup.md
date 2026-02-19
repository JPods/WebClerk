# Environment Setup

Both the React frontend and Django backend use `.env` files that are
**git-ignored**.  This document is the committed reference for every variable.

---

## React2025 (Vite frontend)

> File: `React2025/.env`

All variables exposed to client code **must** start with `VITE_`.
Restart the dev server after any change — Vite caches env at startup.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_ENV` | `DEV` | `DEV` or `PROD` — controls feature flags & logging |
| `VITE_URL` | `http://localhost:5173` | The URL Vite serves on |
| `VITE_DEBUG_BADGES` | `true` | Show/hide component-name badges (DevBadge) on detail pages, panels, and cards |
| `VITE_DATA_SET_ID` | `DEV` | Should mirror backend `DATA_SET_ID` |
| `VITE_DATA_SET_NAME` | `Development Server` | Human-readable dataset label |
| `VITE_API_URL` | `http://localhost:8000` | Backend root — do **not** include `/wcapi` (the SDK appends it) |
| `VITE_AUTH_API_URL` | `http://localhost:8000` | Auth origin (same as API in dev) |
| `VITE_API_URL_PROD` | `http://85.31.234.194:8000/` | Production API URL |
| `VITE_NOTION_API_URL` | `https://api.notion.com/v1/` | Notion integration endpoint |

---

## webClerk3 (Django backend)

> File: `webClerk3/.env`
> Full reference: `webClerk3/readmes/env-setup.md`

| Variable | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | *(generated)* | Django secret key |
| `DATA_SET_ID` | `DEV` | Mirrors frontend `VITE_DATA_SET_ID` |
| `DATA_SET_NAME` | `Development Server` | Human-readable label |
| `DB_MODE` | `remote` | `remote` · `local` · `write-through` |
| `REMOTE_DATABASE_HOST` | `76.13.185.210` | VPS Postgres host |
| `LOCAL_DATABASE_HOST` | `localhost` | Local Postgres host |
| `WRITE_THROUGH_TIMEOUT` | `30` | Seconds before remote forward times out |
| `EMAIL_HOST` | `smtp.mail.me.com` | SMTP server for outbound email |
| `SENTRY_DSN` | *(empty)* | Sentry error-tracking DSN |

---

## Switching databases

You only change the **backend** `DB_MODE` — the frontend config stays the same.

```bash
# Option 1 — shell script
cd webClerk3/tools && ./switch-dataset.sh remote   # team collaboration
cd webClerk3/tools && ./switch-dataset.sh local    # local debugging

# Option 2 — edit webClerk3/.env directly
DB_MODE=local    # or remote, write-through
```

In the running app you can also click the colour badge in the bottom-left
corner: 🟢 Green = REMOTE (team) | 🔵 Blue = LOCAL (debug).

---

## Tips

- Do not include `/wcapi` in `VITE_API_URL`; the SDK appends it in request
  paths.
- Use `.env.local` for machine-specific overrides (also git-ignored by Vite).
- After changing backend env vars, restart Django (`manage.py runserver`).
- After changing frontend env vars, restart Vite (`npm run dev`).