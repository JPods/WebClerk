# Whitelist Tester

A Postman-like tool to try whitelisted backend endpoints from the browser.

Route: `/whitelist`

## Presets

- Login (POST): `/auth/login/` with username/password
- Models (GET): `/wcapi/model_name/list/`
- Model Detail (GET): `/wcapi/model_name/detail/?model_name=contact`
- Get (GET): `/wcapi/get/?model_name=contact&limit=10`
- Save (POST): `/wcapi/save/` with `{ model_name: 'contact', id: 1, ... }`

## Usage

1. Pick a preset to fill in method, URL, and a sample body.
2. (Optional) Edit Headers and Body as raw JSON.
3. Click Send to perform the request. The response body is shown below.

Notes:

- `VITE_API_URL` must point to your backend root (no `/wcapi`).
- Auth header is added automatically if you’re logged in; for login, you may need to adjust URL if auth origin differs.
- Only GET and POST are supported for now; add more as needed.
