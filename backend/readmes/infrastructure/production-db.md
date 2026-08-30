# Production Database — WebClerk3

<!-- TOC START -->

## Table of Contents

- [Overview](#overview)
- [Connection Details](#connection-details)
- [DB Modes (DB\_MODE)](#db-modes-db_mode)
- [Migrations in Production](#migrations-in-production)
- [Backup Strategy](#backup-strategy)
- [Restore](#restore)
- [Maintenance](#maintenance)
- [Latency & Performance Rules](#latency--performance-rules)
- [Security](#security)
- [Checklist: First Production Deploy](#checklist-first-production-deploy)

<!-- TOC END -->

---

## Overview

WebClerk3 uses **remote PostgreSQL** as its single source of truth. There is no ORM-level sharding or replication — one authoritative Postgres instance serves all `DB_MODE=remote` processes (gunicorn workers, Celery, Beat). Local and write-through modes exist for dev and debugging only and are never used on the production server.

---

## Connection Details

Configured entirely in `.env`. The app reads these at startup via `python-decouple`.

```dotenv
DB_MODE=remote

REMOTE_DATABASE_HOST=85.31.234.194   # VPS — change if host migrates
REMOTE_DATABASE_PORT=5432
REMOTE_DATABASE_NAME=commerce_expert
REMOTE_DATABASE_USER=postgres
REMOTE_DATABASE_PASS=<set in .env — never commit>
```

> The IP `85.31.234.194` is also hard-coded in `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` in `settings.py`. Update both if the server IP changes.

---

## DB Modes (DB_MODE)

| Mode | Reads from | Writes to | Production use |
|------|-----------|-----------|----------------|
| `local` *(dev default)* | local Postgres | local Postgres | ❌ Dev only |
| `remote` | remote Postgres | remote Postgres | ✅ Production |
| `write-through` | local Postgres | remote Postgres | ⚠️ Testing only |
| `local-sync` | local Postgres | local + async remote | ⚠️ Testing only |

On the production server, `.env` must have `DB_MODE=remote` and no `USE_SQLITE_TEST` or `PYTEST_FORCE_DB` variables set.

---

## Migrations in Production

**Always migrate before restarting gunicorn.** New code may depend on schema that doesn't exist yet.

```bash
cd /srv/webclerk3
source bin/activate

# 1. Review pending migrations (dry run)
python manage.py showmigrations | grep '\[ \]'

# 2. Apply
python manage.py migrate

# 3. Restart service
sudo systemctl restart webclerk3-gunicorn
sudo systemctl restart webclerk3-celery
sudo systemctl restart webclerk3-celerybeat
```

Never run `migrate --fake` in production unless you are certain the schema already matches the migration state (e.g. a squash that reflects existing columns only).

---

## Backup Strategy

Postgres has no managed backup configured out of the box. Set this up before taking the first live customer data.

### pg_dump (manual / cron)

```bash
# Full dump — run as postgres user or with PGPASSWORD set
pg_dump -h 85.31.234.194 -U postgres -d commerce_expert -Fc \
    > /backups/wc3_$(date +%Y%m%d_%H%M%S).dump

# Restore from dump
pg_restore -h 85.31.234.194 -U postgres -d commerce_expert \
    --clean --if-exists /backups/wc3_YYYYMMDD_HHMMSS.dump
```

### Recommended cron (on the VPS)

```cron
# /etc/cron.d/webclerk3-backup
0 2 * * * postgres pg_dump -Fc commerce_expert > /backups/wc3_$(date +\%Y\%m\%d).dump
# Keep 14 days
0 3 * * * find /backups -name 'wc3_*.dump' -mtime +14 -delete
```

### Retention policy

| Backup type | Keep for |
|-------------|----------|
| Daily dumps | 14 days |
| Weekly (Sunday) | 8 weeks |
| Monthly (1st) | 12 months |

---

## Restore

1. Stop gunicorn and Celery to prevent writes during restore.
2. `pg_restore` the dump into a clean `commerce_expert` database.
3. Re-run `python manage.py migrate` to ensure migration state is consistent.
4. Restart services.

```bash
sudo systemctl stop webclerk3-gunicorn webclerk3-celery webclerk3-celerybeat

# Drop + recreate (destructive — confirm before running)
psql -h 85.31.234.194 -U postgres -c "DROP DATABASE commerce_expert;"
psql -h 85.31.234.194 -U postgres -c "CREATE DATABASE commerce_expert;"
pg_restore -h 85.31.234.194 -U postgres -d commerce_expert /backups/wc3_YYYYMMDD.dump

python manage.py migrate

sudo systemctl start webclerk3-gunicorn webclerk3-celery webclerk3-celerybeat
```

---

## Maintenance

### Daily financial maintenance (via Celery Beat or cron)

```bash
python manage.py org_financial_maintenance --mode daily
```

This runs: scrub → pending drain → Alice health_check log. Should complete well within nightly window.

### Keyword index rebuild (after bulk data imports)

```bash
python manage.py rebuild_keywords   # if available, else trigger via Alice note
```

### Seed standard search presets (one-time per fresh DB)

```bash
python manage.py seed_search_presets
```

### Index check (quarterly or after large data changes)

```sql
-- Run via psql; look for bloat or missing GIN indexes
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC
LIMIT 30;
```

See [db-maintenance.md](db-maintenance.md) for N+1 prevention and query performance guidance.

---

## Latency & Performance Rules

The production Postgres is remote — every unnecessary query adds real network round-trip latency (~10–50ms). These rules are **non-negotiable** for production ViewSets:

1. **Always use `select_related`** for FK fields accessed in serializers.
2. **Never access `f.name` on FK fields in `__init__`** — use `f.attname` (raw ID column). Already fixed in `BaseModel`.
3. **GIN indexes** on `refs` JSONB columns are critical — confirm they exist after schema changes:
   ```sql
   SELECT indexname, indexdef FROM pg_indexes
   WHERE tablename LIKE 'core_%' AND indexdef LIKE '%gin%';
   ```
4. Check query count with Django Debug Toolbar against the remote DB during staging before any release that touches list views.

---

## Security

- `DEBUG=False` — mandatory. Django will serve stack traces publicly if this is `True`.
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. Never reuse the dev default `insecure-dev-test-key`.
- Postgres `REMOTE_DATABASE_PASS` — set in `.env`, which is git-ignored. Never commit credentials.
- Restrict port 5432 — Postgres should not be open to the public internet. Use SSH tunnel or VPC-level firewall rules. The production server at `85.31.234.194` should accept 5432 only from its own loopback and known team IPs.
- Django admin (`/admin/`) — restrict to known IPs in the nginx config (see `tools/deploy/nginx/webclerk3.conf`).

---

## Checklist: First Production Deploy

- [ ] `.env` created with `DEBUG=False`, real `SECRET_KEY`, `DB_MODE=remote`, real `REMOTE_DATABASE_PASS`
- [ ] `python manage.py migrate` completed with exit 0
- [ ] `python manage.py collectstatic --noinput` completed; `/staticfiles/` served by nginx
- [ ] `python manage.py seed_search_presets` run
- [ ] `python manage.py org_financial_maintenance --mode daily` run (baseline)
- [ ] gunicorn, celery, and celerybeat systemd units enabled and started
- [ ] nginx config tested (`sudo nginx -t`), reloaded
- [ ] Port 5432 not exposed publicly (verify with `nmap 85.31.234.194`)
- [ ] Daily pg_dump cron installed
- [ ] First backup verified by restoring to a test database
- [ ] `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` in `settings.py` include the production domain/IP
