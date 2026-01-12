# Admin Window

An overview/admin landing experience that links to common management pages and tools.

Common routes:

- Dashboard: `/dashboard`
- Admin Workbench: `/admin-wb`
- Whitelist Tester: `/whitelist`

## Requirements

- Frontend dev server (default): `http://localhost:5173` (or next available port)
- Backend: `http://localhost:8000`
- Vite env:
  - `VITE_ENV=DEV`
  - `VITE_API_URL=http://localhost:8000`
  - `VITE_AUTH_API_URL=http://localhost:8000`

## Authentication

- Most admin pages require login. Use the Sign In form on `/`.
- On success, tokens are stored and `Authorization: Bearer <access>` is attached automatically.
- If your session expires, the app tries a refresh; failing that, you’ll be logged out.

## Troubleshooting

- If you see 401s on admin pages, verify you’re logged in and that the backend URL is correct.
- After changing `.env`, restart the dev server.
