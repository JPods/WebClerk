"""
API Response Envelope Implementation Guide

This document explains the response envelope metadata system for transaction endpoints.

## Envelope Structure

All transaction API responses are wrapped in a standardized envelope with metadata:

```json
{
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-12-08T10:30:45.123Z",
    "api_version": "1.0",
    "status": "success",
    "code": 200,
    "http_method": "GET",
    "path": "/tx/proposals/",
    "item_count": 25,
    "pagination": {
      "page": 1,
      "page_size": 25,
      "total_items": 1000,
      "total_pages": 40,
      "has_next": true,
      "has_previous": false,
      "next_page": 2,
      "prev_page": null
    }
  },
  "data": [
    { "id": 1, "name": "PROP-001", ... },
    { "id": 2, "name": "PROP-002", ... }
  ]
}
```

## Metadata Fields

- **request_id**: Unique request tracking ID (UUID), propagated via X-Request-ID header
- **timestamp**: ISO 8601 response timestamp (server time)
- **api_version**: API version string (e.g., "1.0")
- **status**: Normalized status category
  - "success" for 2xx HTTP codes
  - "fail" for 4xx HTTP codes
  - "error" for 5xx HTTP codes
  - "redirect" for 3xx HTTP codes
- **code**: HTTP status code (mirror of HTTP response)
- **http_method**: Request HTTP method (GET, POST, etc.)
- **path**: Request path (e.g., "/tx/proposals/")
- **item_count**: Count of items in current page (for list responses)
- **pagination**: Pagination metadata (only for list responses)
  - page: Current page number
  - page_size: Items per page
  - total_items: Total count of all items
  - total_pages: Total number of pages
  - has_next: Whether next page exists
  - has_previous: Whether previous page exists
  - next_page: Next page number (if has_next)
  - prev_page: Previous page number (if has_previous)

## Implementation

### Using EnvelopeResponseMixin

Add the mixin to any ViewSet to automatically wrap all responses:

```python
from apps.transactions.response_envelope import EnvelopeResponseMixin

class MyViewSet(EnvelopeResponseMixin, viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
```

### Using TransactionPagination

For list endpoints with pagination metadata:

```python
from apps.transactions.pagination import TransactionPagination

class MyListView(generics.ListAPIView):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
    pagination_class = TransactionPagination
```

### Response Examples

#### List with Pagination
```
GET /tx/proposals/?page=1&page_size=10

Response:
{
  "meta": {
    "request_id": "...",
    "timestamp": "2025-12-08T10:30:45Z",
    "status": "success",
    "code": 200,
    "item_count": 10,
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_items": 157,
      "total_pages": 16,
      "has_next": true,
      "next_page": 2
    }
  },
  "data": [...]
}
```

#### Single Item Retrieve
```
GET /tx/proposals/1/

Response:
{
  "meta": {
    "request_id": "...",
    "timestamp": "2025-12-08T10:30:45Z",
    "status": "success",
    "code": 200,
    "http_method": "GET",
    "path": "/tx/proposals/1/"
  },
  "data": { "id": 1, "name": "PROP-001", ... }
}
```

#### Error Response
```
POST /tx/proposals/ (with invalid data)

Response:
{
  "meta": {
    "request_id": "...",
    "timestamp": "2025-12-08T10:30:45Z",
    "status": "fail",
    "code": 400
  },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid proposal data",
    "details": { "name": ["This field is required."] }
  },
  "data": null
}
```

## Integration Points

### Response Headers

All responses include tracking headers:
- `X-Request-ID`: Unique request identifier (can be provided via request header)
- `X-Response-Timestamp`: ISO 8601 response timestamp

### Query Parameters

- `page`: Current page number (default: 1)
- `page_size`: Items per page (default: 25, max: 500)

### Client Usage Example (JavaScript/React)

```javascript
// Fetch list with pagination metadata
const response = await fetch('/tx/proposals/?page=1&page_size=25');
const { meta, data } = await response.json();

console.log(meta.pagination); // { page: 1, total_pages: 10, ... }
console.log(meta.request_id); // Track in logs
console.log(data); // Array of proposals

// Handle pagination
if (meta.pagination.has_next) {
  // Fetch next page
}
```

## Status Codes and Meanings

- **200**: Success - GET, list, or retrieve completed
- **201**: Created - POST created new resource
- **204**: No Content - DELETE successful
- **400**: Fail - Validation error or bad request
- **401**: Fail - Unauthorized
- **403**: Fail - Forbidden
- **404**: Fail - Not found
- **409**: Fail - Conflict (e.g., duplicate)
- **500**: Error - Server error
- **503**: Error - Service unavailable
"""
