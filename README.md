# WebClerk

Open source, free, bottom-up commerce platform.

**License:** Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE)

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | `brew install python@3.13` |
| Node.js | 20+ | `brew install node` |
| PostgreSQL | 16+ | `brew install postgresql@16 && brew services start postgresql@16` |
| Redis | 7+ | `brew install redis && brew services start redis` |
| Ollama | latest | `brew install ollama` (optional — enables AI features) |

## Quick Start

```bash
git clone https://github.com/JPods/WebClerk.git
cd WebClerk
./install.sh
./start.sh
```

The installer creates virtual environments, installs dependencies, sets up the database, and writes `.env` files. The launcher starts both backend and frontend.

## Manual Setup

If you prefer to set things up yourself:

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create database
createdb commerce_expert

# Configure environment
cp .env-example .env
# Edit .env — set LOCAL_DATABASE_USER to your postgres user

# Initialize
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend runs at http://localhost:8000

### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env-example .env

npm run dev
```

Frontend runs at http://localhost:5173

## Environment Files

Both `.env` files are gitignored. The installer creates them from templates. Key settings:

**Backend** (`backend/.env`):
- `DB_MODE` — `local` (default) or `remote`
- `LOCAL_DATABASE_NAME` — default `commerce_expert`
- `DEBUG` — `True` for development

**Frontend** (`frontend/.env`):
- `VITE_API_URL` — backend URL (default `http://localhost:8000`)
- `VITE_ENV` — `DEV` or `PROD`

## Project Structure

```
WebClerk/
  LICENSE              Apache 2.0
  NOTICE               Dependency attribution
  install.sh           One-time setup
  start.sh             Launch backend + frontend
  backend/             Django REST API
    apps/              Django applications
    requirements.txt   Python dependencies
    manage.py          Django management
    runserver.sh       Backend launcher (with Celery, Ollama)
  frontend/            React + TypeScript + Vite
    src/               Application source
    package.json       Node dependencies
```

## Development

After initial setup, daily workflow is:

```bash
cd WebClerk
./start.sh
```

This starts:
- Django on port 8000 (with auto-restart on code changes)
- Celery worker + beat (background tasks)
- Ollama (if installed — AI features)
- Vite dev server on port 5173 (with hot reload)

Press `Ctrl+C` to stop everything.

## Copyright

Copyright 2024-2026 JPods LLC
