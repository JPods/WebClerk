# Environment Setup (Vite)

## Required variables

- `VITE_API_URL` → Backend root, e.g., <http://localhost:8000>
- `VITE_AUTH_API_URL` → Optional, if auth lives on a different origin

## Tips

- Do not include `/wcapi` in `VITE_API_URL`; the SDK appends it in request paths.
- Restart dev server after changing env vars.
- Use `.env.local` for machine-specific values.
