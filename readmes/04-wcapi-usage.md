# WCAPI Usage Guide

> **Reading order**: [← 03-wcapi-gateway](03-wcapi-gateway.md) | [05-model-registry →](05-model-registry.md)

---

The WebClerk API (WCAPI) provides RESTful access to all application models through a unified interface. This guide covers the GET endpoint for retrieving data.

## Base URL

All WCAPI endpoints are available under `/wcapi/`.

## GET Endpoint: `/wcapi/get/`

Retrieve records from any model using query parameters.

### Basic Usage

```bash
GET /wcapi/get/?model_name=invoice&limit=20
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model_name` | string | Yes | Model identifier (e.g., 'invoice', 'order', 'contact') |
| `id` | integer | No | Retrieve single record by ID |
| `fields` | string | No | Comma-separated list of fields to return |
| `limit` | integer | No | Maximum records to return (default: 500, max: 1000) |
| `offset` | integer | No | Number of records to skip for pagination |
| `order_by` | string | No | Field to sort by (prefix '-' for descending) |

### Additional Filters

Any other query parameter becomes a filter on the model:

```bash
GET /wcapi/get/?model_name=invoice&status=complete&customer_id=123
```

## Examples

### Get 20 invoices

```bash
GET /wcapi/get/?model_name=invoice&limit=20
```

### Get specific invoice

```bash
GET /wcapi/get/?model_name=invoice&id=123
```

### Get invoices with selected fields

```bash
GET /wcapi/get/?model_name=invoice&fields=id,amount,status,total&limit=10
```

### Get paginated results

```bash
GET /wcapi/get/?model_name=invoice&limit=50&offset=100&order_by=-dt_created
```

### Filter by status

```bash
GET /wcapi/get/?model_name=invoice&status=complete&limit=20
```

### Get sales orders for customer

```bash
GET /wcapi/get/?model_name=order&customer_id=456&order_by=-dt_created
```

## Response Format

### List Response

```json
{
  "results": [
    {
      "id": 1,
      "amount": "100.00",
      "status": "complete",
      "customer_id": 123
    }
  ],
  "count": 1,
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Single Record Response

```json
{
  "record": {
    "id": 123,
    "amount": "100.00",
    "status": "complete",
    "customer_id": 456
  }
}
```

### Error Response

```json
{
  "detail": "invalid model"
}
```

## Available Models

Use `/wcapi/model_name/list/` to get all available model names:

```bash
GET /wcapi/model_name/list/
```

Response:

```json
{
  "status": "success",
  "code": 200,
  "message": "OK",
  "data": {
    "model_names": ["invoice", "order", "contact", "product"],
    "count": 4
  }
}
```

## Model Details

Get field information for a specific model:

```bash
GET /wcapi/model_name/detail/?model_name=invoice
```

## Authentication

Include authentication headers as required by your Django REST framework configuration.

## Rate Limiting

- Default limit: 500 records
- Maximum limit: 1000 records
- Use pagination for large datasets

## Field Filtering

Use the `fields` parameter to reduce response size:

```bash
GET /wcapi/get/?model_name=invoice&fields=id,status,total&limit=100
```

## Ordering

Sort results by any field:

```bash
# Ascending
GET /wcapi/get/?model_name=invoice&order_by=dt_created

# Descending
GET /wcapi/get/?model_name=invoice&order_by=-amount
```

## Pagination

Use `limit` and `offset` for pagination:

```bash
# Page 1
GET /wcapi/get/?model_name=invoice&limit=50&offset=0

# Page 2
GET /wcapi/get/?model_name=invoice&limit=50&offset=50
```

## Error Handling

- `400 Bad Request`: Invalid model_name or parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Record not found (when using id parameter)

## Performance Tips

1. Use `fields` parameter to limit response size
2. Use appropriate `limit` values
3. Filter results to reduce database load
4. Use pagination for large datasets
5. Cache frequently accessed data

## Proposal API Endpoints

Proposals and proposal lines have dedicated REST API endpoints in addition to WCAPI access.

### Proposal Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/proposals/` | List all proposals |
| POST | `/api/transactions/proposals/` | Create a new proposal |
| GET | `/api/transactions/proposals/{id}/` | Get proposal details |
| PUT | `/api/transactions/proposals/{id}/` | Update proposal |
| PATCH | `/api/transactions/proposals/{id}/` | Partial update proposal |
| DELETE | `/api/transactions/proposals/{id}/` | Delete proposal |
| POST | `/api/transactions/proposals/{id}/convert_to_order/` | Convert proposal to sales order |
| GET | `/api/transactions/proposals/{id}/totals/` | Get proposal totals |

### Proposal Line Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/proposal-lines/` | List all proposal lines |
| POST | `/api/transactions/proposal-lines/` | Create a new proposal line |
| GET | `/api/transactions/proposal-lines/{id}/` | Get proposal line details |
| PUT | `/api/transactions/proposal-lines/{id}/` | Update proposal line |
| PATCH | `/api/transactions/proposal-lines/{id}/` | Partial update proposal line |
| DELETE | `/api/transactions/proposal-lines/{id}/` | Delete proposal line |

### WCAPI Access

Proposals are also accessible via WCAPI:

```bash
# Get proposals
GET /wcapi/get/?model_name=proposal&limit=20

# Get specific proposal with related data
GET /wcapi/get/?model_name=proposal&id=123

# Get proposal lines for a proposal
GET /wcapi/get/?model_name=proposal_line&parent=123
```

### Proposal Fields

Key proposal fields include:

- `id`: Unique identifier
- `uuid`: UUID identifier
- `ida`: Alternative ID
- `proposal_no`: Auto-generated proposal number
- `status`: Status (planned, sent, accepted, rejected, cancelled)
- `id_customer`: Customer contact ID
- `id_vendor`: Vendor contact ID
- `cost`: Cost data (JSON)
- `sell`: Sell data (JSON)
- `finance`: Finance data (JSON)
- `flow`: Flow data (JSON)
- `source`: Source data (JSON)
- `action`: Action data (JSON)
- `total_amount`: Calculated total amount
- `line_count`: Number of line items
- `margin_amount`: Calculated margin
- `margin_percentage`: Margin percentage
- `dt_created`: Creation timestamp
- `dt_modified`: Modification timestamp

### Proposal Line Fields

Key proposal line fields include:

- `id`: Unique identifier
- `parent`: Parent proposal ID
- `item_id`: Item ID
- `description`: Line description
- `quantity`: Quantity
- `price`: Price data (JSON with sell/cost)
- `discount_amount`: Discount amount
- `extended_price`: Calculated extended price
- `item_name`: Item name (read-only)
- `unit_cost`: Unit cost (read-only)
- `line_margin`: Line margin (read-only)

### Example: Create Proposal

```bash
POST /api/transactions/proposals/
Content-Type: application/json

{
  "ida": "PROP-001",
  "status": "planned",
  "id_customer": 123,
  "id_vendor": 456
}
```

### Example: Add Proposal Line

```bash
POST /api/transactions/proposal-lines/
Content-Type: application/json

{
  "parent": 1,
  "item_id": 789,
  "description": "Sample Item",
  "quantity": 10,
  "price": {
    "sell": 50.00,
    "cost": 30.00
  },
  "discount_amount": 5.00
}
```

### Example: Convert Proposal to Order

```bash
POST /api/transactions/proposals/1/convert_to_order/
```

Response:

```json
{
  "order_id": 123
}
```

## Integration Examples

### JavaScript/React

```javascript
const response = await fetch('/wcapi/get/?model_name=invoice&limit=20');
const data = await response.json();
console.log(data.results);
```

### Python

```python
import requests

response = requests.get('/wcapi/get/', params={
    'model_name': 'invoice',
    'limit': 20,
    'status': 'complete'
})
data = response.json()
print(data['results'])
```

### cURL

```bash
curl -X GET "http://localhost:8000/wcapi/get/?model_name=invoice&limit=20" \
  -H "Authorization: Bearer <token>"
  