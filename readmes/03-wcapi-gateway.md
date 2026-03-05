# Web Clerk API Gateway (wcapi)

> **Reading order**: [← 02-dev-setup](02-dev-setup.md) | [04-wcapi-usage →](04-wcapi-usage.md) | [08-transaction-save](08-transaction-save.md)

---

## Overview

The **wcapi** (WebClerk API) is a unified gateway that routes all CRUD operations through a single, centralized set of endpoints. This design concentrates security surface area and simplifies both backend maintenance and frontend integration.

## Why a Unified Gateway?

Traditional REST APIs create endpoints per model (`/api/invoices/`, `/api/contacts/`, etc.). WebClerk3 takes a different approach:

| Traditional REST | wcapi Gateway |
|------------------|---------------|
| `/api/invoices/` | `/wcapi/get/?model_name=invoice` |
| `/api/contacts/` | `/wcapi/get/?model_name=contact` |
| `/api/core/contacts/list` | `/wcapi/get/?model_name=contact` |
| `/api/invoices/123/` | `/wcapi/get/?model_name=invoice&id=123` |
| `/api/transactions/invoices/123/` | `/wcapi/get/?model_name=invoice&id=123` |


**Benefits:**
- **Security**: Single entry point for all write operations - easier to audit and protect
- **Consistency**: Same request/response envelope for every model
- **Flexibility**: Add new models without creating new endpoints
- **Permissions**: Centralized field-level access control

## Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/get/` | GET | Fetch records (list or single by ID) |
| `/wcapi/save/` | POST | Create or update records |
| `/wcapi/query/` | POST | Complex queries with filters |
| `/wcapi/manage/` | POST | Administrative operations |

## Model Registry

Models must be explicitly registered in `apps/core/services/wcapi_registry.py` to be accessible via wcapi. This "allow-list" approach prevents accidental exposure of internal models.

See [05-model-registry.md](05-model-registry.md) for the full list of available models.

## Access Control

- **Staff-only features**: The `q` parameter on list endpoints (e.g., `GET /wcapi/get/?model_name=contact&q=...`) returns 403 for non-staff users
- **Rate limiting**: 1000 requests/day authenticated, 100/day anonymous
- **Field permissions**: Controlled via settings matrices per model

## Response Envelope

All responses follow a standard envelope structure:

```json
{
  "status": "success",
  "data": { ... },
  "error": null,
  "meta": {
    "count": 1,
    "total": 100,
    "limit": 20,
    "offset": 0
  }
}
```

See [api_response_envelope.md](api_response_envelope.md) for detailed documentation.

## Related Files

### Backend (webClerk3)

| File | Purpose |
|------|---------|
| `common/middleware/rest_redirect.py` | Server-side middleware — intercepts `/api/…` REST calls and 301-redirects to `/wcapi/` |
| `tests/test_rest_redirect.py` | 46 tests covering path parsing, URL construction, and redirect behaviour |
| `apps/core/services/wcapi_registry.py` | Runtime model registry used by wcapi views |
| `apps/core/views/wcapi.py` | `WCAPIGetView`, `WCAPIDeleteView` |
| `apps/core/views/save_view.py` | `SaveWcapiView` (create / update) |
| `webclerk3_api/urls.py` | URL routing — mounts `/api/` REST endpoints and `/wcapi/` gateway |

### Frontend (React2025)

| File | Purpose |
|------|---------|
| `src/api/restToWcapi.ts` | Client-side REST→wcapi converter (mirrors the server middleware) |
| `src/api/modelNameResolver.ts` | Canonical model-name resolution for wcapi calls |
| `src/pages/tools/WhitelistTester.tsx` | Interactive API tester with REST + wcapi presets |
| `readmes/api-migration-rest-to-wcapi.md` | Migration tracker — REST→wcapi file audit and status |

### Swagger / OpenAPI

| URL | Description |
|-----|-------------|
| `/wcapi/swagger/` | wcapi schema (Swagger UI) |
| `/wcapi/redoc/` | wcapi schema (ReDoc) |
| `/admin/swagger/` | Admin / DRF REST schema |

## Next Steps

- [04-wcapi-usage.md](04-wcapi-usage.md) - Practical examples and patterns
- [06-api-conventions.md](06-api-conventions.md) - Naming conventions and related data
- [08-transaction-save.md](08-transaction-save.md) - Transaction save patterns (header + lines)
- [celery-redis-pending.md](celery-redis-pending.md) - Background pending processing