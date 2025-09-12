Google Calendar OAuth: keep secrets on your machine (not in git)

Overview
- We support two local-only ways to supply Google OAuth client credentials without committing secrets:
  1) Environment variables with a prefix (e.g., GCAL_PRIMARY_CLIENT_ID/SECRET/REDIRECT_URI)
  2) A local JSON file containing { client_id, client_secret, redirect_uri }

- Tokens returned by Google can be stored on disk under .local/ instead of the database, so they never end up in git.

What’s already in place
- .gitignore excludes .env, .local/**, google-credentials*.json, and google_tokens_*.json.
- The Google Calendar service resolves credentials in this order:
  1) Environment variables using Connection.config.env_prefix
  2) Connection.config.credentials_file (relative paths resolved from BASE_DIR)
  3) Inline values in Connection.config (not recommended for secrets)
- Tokens can be stored to a file if Connection.config.token_storage = "file" (recommended for local-only).

Quick setup
1) Copy .env.example to .env and fill in your Google OAuth values for a prefix (e.g., GCAL_PRIMARY_*).

2) Create a Connection configured to use env or a credentials file and file-based token storage:
   - Using management command:
     ./bin/python manage.py setup_gcal_connection \
       --name "Google Calendar - Primary" \
       --env-prefix GCAL_PRIMARY \
       --token-storage file \
       --token-path .local/google_tokens_primary.json

   - Or via API/UI, set Connection fields:
     type: google_calendar
     config: {
       "env_prefix": "GCAL_PRIMARY",            # or provide "credentials_file": "google-credentials.primary.json"
       "token_storage": "file",
       "token_path": ".local/google_tokens_primary.json"
     }

3) Start OAuth (as a staff/admin user):
   GET /sync/google/calendar/start?connection_id=<ID>
   - Redirect user to the provided authorization_url.

4) After consent, Google redirects to your redirect_uri (e.g., http://localhost:8000/sync/google/calendar/callback).
   - The app exchanges code for tokens and stores them according to token_storage.

5) List events:
   GET /sync/google/calendar/events?connection_id=<ID>&calendar_id=primary

Local credentials file format
{
  "client_id": "xxxxx.apps.googleusercontent.com",
  "client_secret": "your-secret",
  "redirect_uri": "http://localhost:8000/sync/google/calendar/callback"
}

Notes
- Do not commit .env or any credential/token files.
- For production, use a secure secret manager or env vars on the server; avoid storing secrets in the database when not necessary.
- The callback response masks sensitive fields and does not include id_token.
