# Startup

> Daily dev workflow: how to start, switch databases, and verify services.

---

## Table of Contents

- [Quick Start](#quick-start)
- [runserver.sh — the normal path](#runservershthe-normal-path)
  - [DB mode argument](#db-mode-argument)
  - [What it does](#what-it-does)
- [start_celery.sh — standalone Celery control](#start_celerysh--standalone-celery-control)
- [Ollama (LLM features)](#ollama-llm-features)
- [Switching DB mode while running](#switching-db-mode-while-running)
- [Logs](#logs)
- [Startup health checks](#startup-health-checks)
- [Stopping](#stopping)
- [Common problems](#common-problems)

---

## Quick Start

```bash
cd /Users/williamjames/Documents/CommerceExpert/webClerk3
./runserver.sh            # default: local postgres
# or
./runserver.sh remote     # remote VPS postgres (production)
```

That's it. Celery worker+beat and Ollama start automatically in the background.

---

## runserver.sh — the normal path

### DB mode argument

| Argument | Database | When to use |
|----------|----------|-------------|
| `local` *(default)* | `localhost / commerce_expert` | All development until production-ready |
| `remote` | VPS Postgres `76.13.185.210` | Production-ready deployment only |

```bash
./runserver.sh [local|remote]
```

### What it does

1. Sets `DB_MODE` in `.env` and `tools/dev-config.json` to the chosen mode.
2. Frees port 8000 (SIGTERM then SIGKILL if needed).
3. Starts Celery worker+beat in the background → `logs/celery.log`.
4. Starts Ollama if installed → `logs/ollama.log`.
5. Prints the **prime org snapshot** (primary_organization setting + OrgBase record).
6. Runs `python manage.py runserver` in a restart loop.

**Auto-restart:** if `tools/.restart_django` exists when Django exits, the loop removes the file and relaunches. The DB-switch API creates that file — no manual restart needed after switching modes from the UI.

**Clean exit:** Ctrl-C or a zero/130 exit code breaks the loop and stops Celery via trap.

---

## start_celery.sh — standalone Celery control

Use this only when you need to manage Celery independently (e.g. separate terminal, debugging).

```bash
./start_celery.sh             # worker + beat combined (default)
./start_celery.sh worker      # worker only
./start_celery.sh beat        # beat only
./start_celery.sh stop        # kill all celery processes for this project
```

App: `webclerk3_api`. Worker concurrency: 2, pool: solo (no forking). Beat schedule file: `/tmp/celerybeat-webclerk3-schedule`.

> `runserver.sh` already starts Celery. Only use `start_celery.sh` directly if you skipped `runserver.sh` or need to restart Celery without touching Django.

---

## Ollama (LLM features)

`runserver.sh` calls `ollama serve` if `ollama` is on PATH and the API at `localhost:11434` is not yet responding. Waits up to 10 seconds.

- Install: `brew install ollama`
- Log: `logs/ollama.log`
- Without Ollama, Django starts normally; LLM-powered features degrade gracefully.

---

## Switching DB mode while running

The React dev tools expose a DB switch. That API call:

1. Updates `.env` and `tools/dev-config.json`.
2. Writes `tools/.restart_django`.
3. Django's runserver loop detects the file, removes it, and relaunches on the new mode.

You can also switch manually:

```bash
# While runserver.sh is running in another terminal:
echo "DB_MODE=remote" >> .env   # or edit .env directly
touch tools/.restart_django     # triggers auto-restart
```

---

## Logs

| File | Contents |
|------|----------|
| `logs/celery.log` | Celery worker+beat output |
| `logs/ollama.log` | Ollama serve output |
| Django | stdout of the terminal running `runserver.sh` |

`logs/` is created automatically if absent.

---

## Startup health checks

`runserver.sh` prints a **prime org snapshot** on each (re)start:

```
[startup] setting_id=<n> model_name=customer id=<n> company=<name>
[startup] prime org id=<n> org_type=customer company=<name> phone=… email=…
```

If you see `MISSING` or `NOT FOUND`, the `primary_organization` Setting record is absent or points to a deleted org. Fix:

```bash
bin/python manage.py shell
>>> from apps.core.models import Setting
>>> s = Setting.objects.filter(purpose='db_defaults', name='primary_organization', is_active=True).first()
>>> s.data  # inspect — set id/org_id/company to a valid OrgBase pk
```

---

## Stopping

| What | How |
|------|-----|
| Django + Celery | Ctrl-C in the `runserver.sh` terminal (trap stops Celery) |
| Celery only | `./start_celery.sh stop` |
| Ollama | `pkill ollama` |
| Port 8000 stuck | `lsof -ti:8000 | xargs kill` (runserver.sh does this automatically) |

---

## Common problems

**Port 8000 in use at startup**
`runserver.sh` frees the port automatically. If it persists: `lsof -ti:8000 | xargs kill -9`.

**Celery not picking up tasks**
Check `logs/celery.log`. Common cause: stale beat schedule file. Delete `/tmp/celerybeat-webclerk3-schedule` and restart.

**Wrong database after restart**
Confirm `DB_MODE` in `.env` matches the argument passed to `runserver.sh`. The file is updated on each launch.

**Migrations out of date**
```bash
bin/python manage.py migrate
```
Then restart. For a full reset see [reset.md](reset.md).

**`bin/python` not found**
The venv must be initialised at the repo root:
```bash
python3 -m venv .
source bin/activate
pip install -r requirements.txt
```
See [02-dev-setup.md](02-dev-setup.md) for full setup.
