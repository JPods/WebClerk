# Copilot Instructions for AI Coding Agents

## Project Overview
- **webClerk3** is a multi-app Python backend, likely Django-based, with custom modules under `apps/` and shared logic in `common/` and `core/`.
- **React2025** is a separate frontend project using React 19, TypeScript, and Tailwind CSS. It integrates with webClerk3 via API calls (see `src/api/` and `integrations/webclerk/sdk/`).

## Architecture & Key Patterns
- **Apps Structure:** Each subfolder in `apps/` is a distinct domain (e.g., `accounts`, `products`, `support`). Shared code lives in `common/` and `core/`.
- **API:** OpenAPI spec in `openapi.json` defines backend endpoints. Use this for API contract reference.
- **Celery:** Background tasks are managed via `celery_app.py`.
- **Testing:** Pytest is configured (`pytest.ini`, `conftest.py`). Tests are in `tests/` and possibly within each app's folder.
- **Dev Scripts:** Use `run.sh` to start the backend, `reset_dev.sh` to reset dev data. Activate the Python venv with `bin/activate`.
- **Data:** Database dumps (`backup_pre_reset.dump`, `dump.rdb`) are for local dev resets.

## Developer Workflows
- **Backend:**
  - Activate venv: `source bin/activate`
  - Run server: `./run.sh`
  - Reset dev DB: `./reset_dev.sh`
  - Run tests: `pytest`
- **Frontend:**
  - Install deps: `npm install`
  - Start dev server: `npm run dev`

## Conventions & Integration
- **Docs:** Most module docs are centralized in `readmes/` (see `readmes/support.md`).
- **External APIs:** Currency conversion uses Frankfurter API for demos (see `readmes/support.md`).
- **API Testing:** Postman collections in `api_tests/` for smoke and local environment tests.
- **Frontend-Backend Integration:** API calls from React2025 use endpoints defined in webClerk3's OpenAPI spec.

## Examples
- To add a new domain, create a folder in `apps/`, add models/views, and update `openapi.json`.
- For background jobs, register tasks in `celery_app.py`.
- For support module details, see `readmes/support.md` and linked Google Doc.

## References
- Backend API: `openapi.json`
- Centralized docs: `readmes/`
- Frontend API usage: `src/api/` in React2025
- Postman tests: `api_tests/`

---

**Feedback:** Please review and suggest additions for any unclear or missing sections, especially around custom workflows or integration points.