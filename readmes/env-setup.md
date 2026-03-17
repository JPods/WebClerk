# Environment Setup — webClerk3 (Django Backend)

The backend reads its configuration from `webClerk3/.env`, which is
**git-ignored**.  Copy the template below into a new `.env` file when
setting up a fresh clone.

> The React frontend has its own `.env` — see `React2025/readmes/02-env-setup.md`.

---

## Quick start

```bash
cd webClerk3
cp .env-example .env          # start from the template
# edit DB_MODE if needed
source venv312/bin/activate
python manage.py runserver 0.0.0.0:8000
```

---

## Variable reference

### Core

| Variable | Default | Notes |
|---|---|---|
| `DEBUG` | `True` | Django debug mode. Set `False` in production. |
| `SECRET_KEY` | *(generated)* | Django secret key — keep private. |

### Data-set identification

| Variable | Default | Notes |
|---|---|---|
| `DATA_SET_ID` | `DEV` | Should mirror the frontend `VITE_DATA_SET_ID`. Options: `LOCAL`, `DEV`, `STAGING`, `PRODUCTION`. |
| `DATA_SET_NAME` | `Development Server` | Human-readable label shown in the UI. |

### Database

| Variable | Default | Notes |
|---|---|---|
| `DB_MODE` | `remote` | **The main switch.** `remote` · `local` · `bill` · `write-through` |
| `REMOTE_DATABASE_HOST` | `76.13.185.210` | VPS Postgres (team/production). |
| `REMOTE_DATABASE_PORT` | `5432` | |
| `REMOTE_DATABASE_NAME` | `commerce_expert` | |
| `REMOTE_DATABASE_USER` | `postgres` | |
| `REMOTE_DATABASE_PASS` | *(set in .env)* | |
| `LOCAL_DATABASE_HOST` | `localhost` | Local Postgres (offline/debugging). |
| `LOCAL_DATABASE_PORT` | `5432` | |
| `LOCAL_DATABASE_NAME` | `commerce_expert` | |
| `LOCAL_DATABASE_USER` | *(your OS user)* | |
| `LOCAL_DATABASE_PASS` | *(empty)* | |
| `BILL_DATABASE_HOST` | `localhost` | Second local Postgres database host (personal sandbox). |
| `BILL_DATABASE_PORT` | `5432` | |
| `BILL_DATABASE_NAME` | `commerce_expert_bill` | |
| `BILL_DATABASE_USER` | *(falls back to LOCAL_DATABASE_USER)* | |
| `BILL_DATABASE_PASS` | *(falls back to LOCAL_DATABASE_PASS)* | |

### Write-through mode

| Variable | Default | Notes |
|---|---|---|
| `WRITE_THROUGH_TIMEOUT` | `30` | Seconds before the remote forward times out. |

When `DB_MODE=write-through` the app reads from the **local** database but
forwards every save to the **remote** database, then stores the remote
response locally.  This is useful for developing against production data
without risking direct writes.

### Email (SMTP)

| Variable | Default | Notes |
|---|---|---|
| `EMAIL_HOST` | `smtp.mail.me.com` | iCloud SMTP relay |
| `EMAIL_PORT` | `587` | TLS |
| `EMAIL_HOST_USER` | *(set in .env)* | |
| `EMAIL_HOST_PASSWORD` | *(set in .env)* | App-specific password |

### Optional services

| Variable | Default | Notes |
|---|---|---|
| `SENTRY_DSN` | *(empty)* | Sentry error-tracking DSN. Leave blank to disable. |

---

## Switching databases

You only need to change **`DB_MODE`** — no frontend changes required.

```bash
# Shell script (updates .env for you)
cd tools && ./switch-dataset.sh remote   # team collaboration
cd tools && ./switch-dataset.sh local    # local debugging
cd tools && ./switch-dataset.sh bill     # personal second local DB

# Or edit .env directly
DB_MODE=local
```

Then restart Django.  The React app auto-detects the dataset through the
`/wcapi/me/` endpoint.

---

## Template

Copy-paste into a fresh `.env`:

```dotenv
DEBUG=True
SECRET_KEY=<generate-a-new-key>

DATA_SET_ID=DEV
DATA_SET_NAME=Development Server

DB_MODE=remote

REMOTE_DATABASE_HOST=76.13.185.210
REMOTE_DATABASE_PORT=5432
REMOTE_DATABASE_NAME=commerce_expert
REMOTE_DATABASE_USER=postgres
REMOTE_DATABASE_PASS=

LOCAL_DATABASE_HOST=localhost
LOCAL_DATABASE_PORT=5432
LOCAL_DATABASE_NAME=commerce_expert
LOCAL_DATABASE_USER=<your-os-user>
LOCAL_DATABASE_PASS=

BILL_DATABASE_HOST=localhost
BILL_DATABASE_PORT=5432
BILL_DATABASE_NAME=commerce_expert_bill
BILL_DATABASE_USER=<your-os-user>
BILL_DATABASE_PASS=

WRITE_THROUGH_TIMEOUT=30

EMAIL_HOST=smtp.mail.me.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

SENTRY_DSN=
```
