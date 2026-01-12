# API Integration

## Axios client

- Axios instance configured in `src/api/axios.ts`
- Uses Vite env vars:
  - `VITE_API_URL` (backend root, e.g., <http://localhost:8000>)
  - `VITE_AUTH_API_URL` (optional auth origin if different)
- Interceptors handle auth tokens and error normalization.

## WebClerk SDK helpers

- Located at `src/api/` and `integrations/webclerk/sdk/`.
- For admin workbench, use `src/api/wcapi.ts` methods:
  - `getModelNames()`, `getModelDetail(model)`, `getRecords(model)`, `getRecord(model, id)`, `saveRecord(model, payload)`

## Common pitfalls

- Double `/wcapi` prefix → ensure `VITE_API_URL` does NOT include `/wcapi`.
- CORS: run backend on 8000 and frontend on 5173; allow origin in backend settings.
- Auth: ensure tokens are present or use dev bypass depending on environment.
