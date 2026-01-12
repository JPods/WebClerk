# Web Clerk API Gateway (wcapi)

> **Reading order**: [← 02-dev-setup](02-dev-setup.md) | [04-wcapi-usage →](04-wcapi-usage.md)

---

## Overview

The **wcapi** (WebClerk API) is a unified gateway that routes all CRUD operations through a single, centralized set of endpoints. This design concentrates security surface area and simplifies both backend maintenance and frontend integration.

## Why a Unified Gateway?

Traditional REST APIs create endpoints per model (`/api/invoices/`, `/api/contacts/`, etc.). WebClerk3 takes a different approach:

| Traditional REST | wcapi Gateway |
|------------------|---------------|
| `/api/invoices/` | `/wcapi/get/?model_name=invoice` |
| `/api/contacts/` | `/wcapi/get/?model_name=contact` |
| `/api/invoices/123/` | `/wcapi/get/?model_name=invoice&id=123` |

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

## Next Steps

- [04-wcapi-usage.md](04-wcapi-usage.md) - Practical examples and patterns
- [06-api-conventions.md](06-api-conventions.md) - Naming conventions and related data