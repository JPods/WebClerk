# API Integration

> **Reading order**: [← 02-env-setup](02-env-setup.md) | [api-migration-rest-to-wcapi →](api-migration-rest-to-wcapi.md)

---

## Architecture Overview

React2025 communicates with the webClerk3 Django backend via the **WCAPI Gateway** — a unified REST interface that replaces legacy per-entity endpoints.

```
React2025 (Vite)        webClerk3 (Django)
    │                        │
    ├─────/wcapi/get/────────┤
    ├─────/wcapi/save/───────┤
    ├─────/wcapi/delete/─────┤
    ├─────/wcapi/query/──────┤
    └─/wcapi/transaction/save/┘
```

---

## Axios Client

Axios instance configured in [src/api/axios.ts](../src/api/axios.ts):

| Env Variable | Purpose | Example |
|-------------|---------|---------|
| `VITE_API_URL` | Backend root (no trailing `/wcapi`) | `http://localhost:8000` |
| `VITE_AUTH_API_URL` | Auth origin if different | `http://localhost:8000` |

Interceptors handle:
- Auth token injection (`Authorization: Bearer <token>`)
- Error normalization (consistent error shape)
- Request/response logging in development

---

## WCAPI SDK

Primary SDK located at [src/api/wcapi.ts](../src/api/wcapi.ts).

### Core Functions

| Function | Endpoint | Purpose |
|----------|----------|---------|
| `getModelNames()` | `GET /wcapi/models/` | List available models |
| `getModelDetail(model)` | `GET /wcapi/models/<model>/` | Schema, fields, config |
| `getRecords(model, params?)` | `GET /wcapi/get/<model>/` | List records with pagination |
| `getRecord(model, id)` | `GET /wcapi/get/<model>/<id>/` | Single record by ID |
| `saveRecord(model, payload)` | `POST /wcapi/save/` | Create or update record |
| `deleteRecord(model, id)` | `POST /wcapi/delete/` | Soft-delete record |
| `queryRecords(params)` | `POST /wcapi/query/` | Complex queries |
| `saveTransactionWithLines(model, payload)` | `POST /wcapi/transaction/save/` | Transaction + lines |

### Usage Examples

```typescript
import { getRecords, getRecord, saveRecord, deleteRecord, saveTransactionWithLines } from '@/api/wcapi';

// List customers with pagination
const customers = await getRecords('customer', { page: 1, page_size: 100 });

// Get single order with lines
const order = await getRecord('order', 42);

// Update a customer
await saveRecord('customer', { id: 123, name: 'Updated Name' });

// Create new order with lines
const result = await saveTransactionWithLines('order', {
  header: { id_customer: 123, status: 'open' },
  lines: [
    { item_id: 456, quantity: 10, price: { sell: 99.99 } }
  ]
});

// Delete a record
await deleteRecord('address', 789);
```

---

## Response Envelope

All WCAPI responses follow a standard envelope:

### Success Response

```json
{
  "status": "success",
  "data": { ... },        // Single record or array
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 100
  }
}
```

### Error Response

```json
{
  "status": "fail",
  "error": {
    "code": "validation_error",
    "message": "Validation failed",
    "details": {
      "name": ["This field is required"]
    }
  }
}
```

---

## Transaction Saves

For transactions with lines (orders, invoices, purchases, etc.), use `saveTransactionWithLines()`:

```typescript
// Create invoice from order (transfer)
const invoice = await saveTransactionWithLines('invoice', {
  header: {
    parent_id: orderId,
    parent_model: 'order',
    id_customer: customerId
  },
  lines: orderLines.map(line => ({
    item_id: line.item_id,
    quantity: line.quantity,
    price: line.price,
    refs: { source: { order_line_id: line.id } }
  }))
});

// Deactivate source order after transfer
await saveRecord('order', { id: orderId, is_active: false });
```

See [webClerk3/readmes/08-transaction-save.md](../../webClerk3/readmes/08-transaction-save.md) for backend details.

---

## Data Source Layer

For components using `AdvancedDataTable`, the WCAPI data source handles pagination and filtering:

```typescript
import { createWcapiDataSource } from '@/api/wcapiDataSource';

const dataSource = createWcapiDataSource('customer', {
  defaultPageSize: 100,
  defaultSort: { field: 'name', order: 'asc' }
});
```

---

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| Double `/wcapi` prefix | `VITE_API_URL` includes `/wcapi` | Remove `/wcapi` from env var |
| CORS errors | Origin not allowed | Add `http://localhost:5173` to Django CORS settings |
| 401 Unauthorized | Missing auth token | Ensure login or use dev bypass |
| Empty response | Wrong model key | Check model registry via `getModelNames()` |
| Validation errors | Missing required fields | Check model schema via `getModelDetail()` |

---

## Related Documentation

- [api-migration-rest-to-wcapi.md](api-migration-rest-to-wcapi.md) — Migration tracker and patterns
- [webClerk3/readmes/03-wcapi-gateway.md](../../webClerk3/readmes/03-wcapi-gateway.md) — Backend gateway overview
- [webClerk3/readmes/04-wcapi-usage.md](../../webClerk3/readmes/04-wcapi-usage.md) — Detailed usage examples
- [webClerk3/readmes/08-transaction-save.md](../../webClerk3/readmes/08-transaction-save.md) — Transaction save patterns
