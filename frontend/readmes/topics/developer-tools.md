# Developer Tools

CommerceExpert ships several built-in tools for development, debugging, and API exploration. This page catalogues them all.

---

## Floating Widgets (React2025)

Two persistent floating widgets are mounted in `App.tsx` and available on every page during development:

### DevTools Panel

**Component:** `src/components/DevTools.tsx`
**Position:** Bottom-left (default)
**Visible when:** `VITE_ENV === 'DEV'`

A color-coded badge shows the current database mode:
- 🟢 **Green** — Remote (Team) database
- 🔵 **Blue** — Local (Debug) database

**Features:**
| Feature | Description |
|---------|-------------|
| DB Mode Switcher | Toggle between remote/local database sets |
| Data Sync (Download) | Pull remote data to local for offline work |
| Data Sync (Upload) | Push local changes back to remote |
| Server Restart | Restart the Django backend with health polling |
| Health Monitor | Auto-detects backend status (live / restarting / offline) |

**Backend endpoints used:**
- `GET /wcapi/dev/config/` — current mode & available modes
- `POST /wcapi/dev/switch/` — switch database mode
- `POST /wcapi/dev/sync/` — sync data between modes
- `POST /wcapi/dev/restart/` — restart backend server

---

### AI Help Widget

**Component:** `src/components/AiHelpWidget.tsx`
**Position:** Bottom-right (default)
**Visible:** Always (requires backend with Ollama running)

A floating chat panel with 6 specialized AI modes, powered by local DeepSeek via Ollama + ChromaDB RAG.

| Mode | Color | Best for |
|------|-------|----------|
| General | Blue | Quick help on any topic |
| Developer | Purple | Code-aware answers with file paths |
| Debugger | Red | Error analysis from tracebacks |
| User Support | Green | Plain-language end-user help |
| Code Review | Amber | Convention compliance checks |
| Test Writer | Teal | Generate tests with project patterns |

> Full setup: see `webClerk3/readmes/topics/ai/setup-guide-Alice.md`

---

## Whitelist Tester

**Component:** `src/pages/tools/WhitelistTester.tsx`
**Route:** `/whitelist`
**Documentation:** `readmes/topics/whitelist.md`

A Postman-like tool in the browser for testing whitelisted API endpoints. Pick a preset (login, model list, choice catalog, get/save/query), edit headers/body as raw JSON, click Send.

**Key features:**
- Auth header auto-injected for logged-in users
- Presets for all WCAPI gateway endpoints
- Raw JSON editing for headers and body
- REST-to-WCAPI redirect testing
- GET and POST methods supported

---

## Swagger / API Documentation (wc3)

**URL:** [http://localhost:8000/admin/swagger/](http://localhost:8000/admin/swagger/)
**Alternative URLs:**
| URL | Interface |
|-----|-----------|
| `http://localhost:8000/wcapi/swagger/` | Swagger UI (public) |
| `http://localhost:8000/admin/swagger/` | Swagger UI (admin context) |
| `http://localhost:8000/wcapi/redoc/` | ReDoc documentation |
| `http://localhost:8000/wcapi/schema/` | Raw OpenAPI 3.0.3 JSON schema |
| `http://localhost:8000/` | Redirects to `/wcapi/swagger/` |

**Powered by:** `drf-spectacular` + `drf-spectacular-sidecar` (bundled UI, no CDN)

**What it covers:**
- All WCAPI gateway endpoints (`/wcapi/get/`, `/wcapi/save/`, `/wcapi/query/`, `/wcapi/manage/`)
- AI assistant endpoints (`/wcapi/ai/*`)
- Auth endpoints
- Full request/response schemas
- JWT Bearer + Cookie authentication

**Usage tips:**
1. Click "Authorize" in Swagger UI to enter your JWT token
2. Expand any endpoint to see parameters, request body schema, and example responses
3. Use "Try it out" to execute requests directly from the browser
4. The schema endpoint (`/wcapi/schema/`) can be imported into Postman, Insomnia, or any OpenAPI client

---

## CLI Tools (webClerk3)

### AI Management Commands

```bash
# Full AI setup
./tools/setup_ai.sh --full

# Index documentation into vector store
python manage.py index_docs
python manage.py index_docs --source models --source readmes

# Health check
python manage.py ai_health

# Stats
python manage.py index_docs --stats
```

### Dev Utilities in `src/tools/`

| File | Purpose |
|------|---------|
| `src/tools/createBlankRecord.ts` | Create blank records matching CoreModel/BaseModel field structure |
| `src/tools/generate-list-migration.js` | Generate AdvancedDataTable list components from model configs |

---

## Quick Reference

| Tool | Access | Purpose |
|------|--------|---------|
| DevTools Panel | Bottom-left badge on any page | DB mode + sync + restart |
| AI Help Widget | Bottom-right bot icon on any page | AI chat with 6 modes |
| Whitelist Tester | `/whitelist` route | API endpoint testing |
| Swagger UI | `http://localhost:8000/admin/swagger/` | OpenAPI documentation |
| ReDoc | `http://localhost:8000/wcapi/redoc/` | Alternative API docs |
| Console Paste (debugger) | AI Widget → Debugger mode → paste | Browser error analysis |

---

## Adding New Tools

1. Create the component in `src/pages/tools/` or `src/components/`
2. Add a route in the router if it's a standalone page
3. Document it in this file
4. If it generates useful data, consider indexing it for the AI assistant
