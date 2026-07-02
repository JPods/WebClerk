# Production Cutover — Local to Hosted PostgreSQL

> Everything that must happen before switching from `DB_MODE=local` to `DB_MODE=remote`.
> Do not skip steps. Do them in order. Each has a verify step.

---

## Current State (as of 2026-06-27)

- All development runs on `DB_MODE=local` → `localhost:5432/commerce_expert`
- `./runserver.sh` defaults to `local`; pass `remote` explicitly for production
- No SQLite in use — PostgreSQL only
- Agent accounts (Allie, Alice, Athena) exist in local DB with correct permissions
- Remote VPS: `76.13.185.210` (ssh: `root@76.13.185.210`)

---

## Phase 1: Before You Touch the Remote DB

### 1.1 Credentials and secrets

| Item | What to do | Where |
|------|-----------|-------|
| `SECRET_KEY` | Generate a new one — never reuse the dev key | `.env` |
| `REMOTE_DATABASE_PASS` | Set a strong password, not the dev default | `.env` |
| Agent passwords | Change `pass1111` / `1111pass` to real passwords | DB + `~/Allie/config/wc_credentials.json` |
| API keys | Encrypt `wc_credentials.json` before any cloud deployment | `~/Allie/config/` |
| Email credentials | Verify SMTP host/password are production-ready | `.env` |

```bash
# Generate a new SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Verify:** `grep SECRET_KEY .env` shows a unique, non-default value.

### 1.2 Agent accounts in remote DB

The agents need to exist in the remote database with correct permissions. In local DB:

| Agent | Email | Role | is_superuser | is_staff |
|-------|-------|------|-------------|----------|
| Allie | allie@jpods.com | admin | True | True |
| Athena | athena@jpods.com | admin | — | — |
| Alice | alice@jpods.com | admin | — | — |

Allie **must** be `is_superuser=True` — without it, the RBAC layer (`inject_role_filters` in `role_filter.py`) denies all queries because she has no `UserProfile`. This applies to any agent that queries the wcapi.

**Option A — migrate data from local to remote:**
```bash
# Dump local, restore to remote
pg_dump -h localhost -U williamjames -d commerce_expert -Fc > /tmp/wc3_local.dump
pg_restore -h 76.13.185.210 -U postgres -d commerce_expert --clean --if-exists /tmp/wc3_local.dump
```

**Option B — create agents manually in remote:**
```bash
DB_MODE=remote ./bin/python manage.py shell -c "
from apps.core.models import Contact
for email, name in [('allie@jpods.com','Allie'), ('athena@jpods.com','Athena'), ('alice@jpods.com','Alice')]:
    u, created = Contact.objects.get_or_create(email=email, defaults={
        'name_first': name, 'name_last': 'JPods', 'role': 'admin',
        'is_staff': True, 'is_superuser': True, 'is_active': True,
        'company': 'JPods',
    })
    if created:
        u.set_password('CHANGE_ME')
        u.save()
        print(f'Created {email} id={u.id}')
    else:
        print(f'Exists {email} id={u.id}')
"
```

**Verify:** Login works via wcapi:
```bash
curl -s -X POST http://REMOTE_HOST:8000/wcapi/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "allie@jpods.com", "password": "NEW_PASSWORD"}' | python3 -m json.tool
```

### 1.3 Update wc_credentials.json

After creating agents in the remote DB, update `~/Allie/config/wc_credentials.json`:
- `user_id` must match the remote DB IDs (they will differ from local)
- `password` must match what you set in the remote DB
- `endpoint` stays `http://localhost:8000` if the app runs locally against the remote DB, or changes to the production URL if the app itself is hosted

### 1.4 Migrations

```bash
# Check migration state on remote
DB_MODE=remote ./bin/python manage.py showmigrations | grep '\[ \]'

# Apply any pending
DB_MODE=remote ./bin/python manage.py migrate
```

**Verify:** No `[ ]` entries in `showmigrations`.

### 1.5 Seed data

```bash
DB_MODE=remote ./bin/python manage.py seed_search_presets
DB_MODE=remote ./bin/python manage.py org_financial_maintenance --mode daily
```

---

## Phase 2: The Switch

### 2.1 Update .env

```dotenv
DB_MODE=remote
DEBUG=False
SECRET_KEY=<your-new-key>
REMOTE_DATABASE_PASS=<your-new-password>
```

### 2.2 Start with remote

```bash
./runserver.sh remote
```

### 2.3 Verify the connection

The startup banner should show:
```
[webClerk3] Database: REMOTE @ 76.13.185.210:5432/commerce_expert
```

Test from Claude Code:
```
wc_search Contact → should return contacts from remote DB
wc_add_note "production test" → should succeed (code 201)
```

---

## Phase 3: Production Hosting (App on VPS)

When the Django app itself moves to the VPS (not just the database):

### 3.1 Server setup

| Component | Tool | Config |
|-----------|------|--------|
| WSGI | gunicorn | `webclerk3_api.wsgi` — systemd unit |
| Async tasks | Celery worker + beat | systemd units |
| Reverse proxy | nginx | SSL termination, static files |
| SSL | Let's Encrypt / certbot | Auto-renew cron |
| Process manager | systemd | `webclerk3-gunicorn.service`, `webclerk3-celery.service` |

### 3.2 Django production settings

```python
DEBUG = False
ALLOWED_HOSTS = ['webclerk.com', 'www.webclerk.com', '76.13.185.210']
CORS_ALLOWED_ORIGINS = ['https://webclerk.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 3.3 Static files

```bash
./bin/python manage.py collectstatic --noinput
# nginx serves /staticfiles/ directly
```

### 3.4 Firewall

- Port 443 (HTTPS): open
- Port 80 (HTTP): redirect to 443
- Port 5432 (Postgres): **localhost only** — not exposed
- Port 8000 (Django): **localhost only** — nginx proxies

### 3.5 Allie endpoint update

When the app is hosted, `wc_credentials.json` endpoint changes:
```json
"endpoint": "https://webclerk.com"
```

MCP server (`wc_mcp_server.py`) — update `WC_BASE`:
```python
WC_BASE = "https://webclerk.com"
```

---

## Phase 4: Post-Cutover

### 4.1 Backups

Confirm daily pg_dump cron is running on VPS (see [production-db.md](production-db.md#backup-strategy)).

### 4.2 Monitoring

- Grafana or similar for query latency
- Celery flower or log monitoring for task failures
- Alice `alice_log` entries for application-level health

### 4.3 Rollback plan

If something breaks after cutover:
1. Change `.env` back to `DB_MODE=local`
2. Restart: `./runserver.sh`
3. Local DB is untouched — all local data is still there

---

## Checklist Summary

```
[ ] New SECRET_KEY generated and in .env
[ ] Strong REMOTE_DATABASE_PASS set
[ ] Agent passwords changed from dev defaults
[ ] Agent accounts exist in remote DB with correct permissions
[ ] wc_credentials.json updated (user_ids, passwords, endpoint)
[ ] Migrations applied on remote (showmigrations clean)
[ ] Seed data loaded (search presets, org maintenance)
[ ] .env set to DB_MODE=remote, DEBUG=False
[ ] runserver.sh remote — startup banner shows REMOTE
[ ] wc_search and wc_add_note work against remote
[ ] pg_dump backup cron installed and first backup verified
[ ] Port 5432 not publicly exposed (nmap verify)
[ ] ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS include production domain
```
