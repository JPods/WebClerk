# WCAPI Usage Guide

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
| `model_name` | string | Yes | Model identifier (e.g., 'invoice', 'salesorder', 'contact') |
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
GET /wcapi/get/?model_name=salesorder&customer_id=456&order_by=-dt_created
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
    "model_names": ["invoice", "salesorder", "contact", "product"],
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
  