# WCAPI /get Endpoint - Enhanced Implementation

**Date:** December 10, 2025  
**Status:** ✅ Fully Enhanced with Filtering, Search, and Pagination

---

## Overview

The `/wcapi/get` endpoint has been enhanced to provide robust, universal query capabilities across all models with:

- ✅ **Advanced Filtering** - Field-based filters with multiple lookup operators
- ✅ **Full-Text Search** - Cross-field search using model configurations
- ✅ **Flexible Pagination** - Both limit/offset and page-based pagination
- ✅ **Smart Ordering** - Field ordering with validation
- ✅ **Query Echo** - Returns applied filters for debugging

---

## API Endpoint

```aaa
GET /api/wcapi/get/?model_name=<model>&[filters]&[pagination]&[search]&[ordering]
```

---

## Query Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | Model key from registry (proposal, order, invoice, contact, etc.) |

### Single Record Retrieval

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Specific record ID - returns single record |

### Filtering Parameters

**Equality & Field Filters:**

```aaa
?field_name=value
?status=active
?priority=high
?customer_id=123
```

**Comparison Operators:**

```aaa
?amount__gte=1000        # Greater than or equal
?amount__lte=5000        # Less than or equal
?amount__gt=1000         # Greater than
?amount__lt=5000         # Less than
?created_date__gte=2025-01-01
?created_date__lte=2025-12-31
```

**String Matching:**

```aaa
?name__icontains=john           # Case-insensitive contains
?email__startswith=admin        # Starts with
?code__endswith=_FINAL          # Ends with
?reference__exact=REF-2025-001  # Exact match (case-sensitive)
?reference__iexact=ref-2025-001 # Exact match (case-insensitive)
```

**Advanced:**

```aaa
?status__ne=canceled     # Not equal
?tags__in=urgent,high    # In list
?is_active__isnull=true  # IS NULL / IS NOT NULL
```

### Search Parameters

**Full-Text Search:**

```aaa
?q=search_term               # Search across searchable fields
?search=search_term          # Alternative parameter name
?q=john+doe                  # Multi-word search (space-separated)
?q=customer%20invoice        # URL-encoded spaces
```

Search uses model's configured searchable fields from registry. Falls back to common fields like:

- name, title, description
- email, phone, code
- reference, number, identifier
- Any CharField, TextField, EmailField, URLField, SlugField

### Pagination Parameters

**Limit/Offset Style (Default):**

```aaa
?limit=50&offset=100         # Get 50 records starting at position 100
?limit=25                    # Get 25 records (default offset=0)
```

**Page-Based Style:**

```aaa
?page=1&page_size=25         # Page 1 with 25 items per page
?page=2&page_size=50         # Page 2 with 50 items per page
```

**Constraints:**

- Minimum limit: 1
- Maximum limit: 1000 (enforced, higher values capped)
- Default limit: 500
- Minimum offset: 0
- Page numbers: 1-indexed

### Ordering Parameters

```aaa
?ordering=field_name         # Ascending order
?ordering=-field_name        # Descending order
?order_by=dt_created         # Alternative parameter name
?order_by=-dt_created        # Alternative with descending

# Common mappings:
?ordering=created_at         # Maps to dt_created
?ordering=-updated_at        # Maps to -dt_modified
?ordering=name               # Alphabetical
?ordering=-id                # Reverse by ID
```

### Optional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated field list (not yet fully implemented) |

---

## Usage Examples

### Example 1: Get All Invoices (Default)

```bash
GET /api/wcapi/get/?model_name=invoice

Response:
{
  "results": [...],
  "count": 25,
  "total": 245,
  "limit": 500,
  "offset": 0,
  "page": 1,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false
}
```

### Example 2: Get Single Record by ID

```bash
GET /api/wcapi/get/?model_name=invoice&id=42

Response:
{
  "record": {
    "id": 42,
    "status": "sent",
    "total": 1500.00,
    ...
  }
}
```

### Example 3: Filter Invoices by Status and Amount Range

```bash
GET /api/wcapi/get/?model_name=invoice&status=sent&total__gte=1000&total__lte=5000

Response:
{
  "results": [...],
  "count": 12,
  "total": 45,
  "query": {
    "search": null,
    "filters": {
      "status": "sent",
      "total__gte": "1000",
      "total__lte": "5000"
    },
    "ordering": null,
    "pagination": {"limit": 500, "offset": 0}
  }
}
```

### Example 4: Search with Pagination

```bash
GET /api/wcapi/get/?model_name=proposal&q=customer%20john&page=1&page_size=10&ordering=-dt_created

Response:
{
  "results": [...],
  "count": 10,
  "total": 87,
  "page": 1,
  "total_pages": 9,
  "has_next": true,
  "has_previous": false,
  "query": {
    "search": "customer john",
    "filters": {},
    "ordering": "-dt_created"
  }
}
```

### Example 5: Complex Filter with Multiple Conditions

```bash
GET /api/wcapi/get/?model_name=order&status=in_progress&priority__ne=low&customer_id=5&created_date__gte=2025-01-01&q=shipment

Response:
{
  "results": [...],
  "count": 3,
  "total": 3,
  "query": {
    "search": "shipment",
    "filters": {
      "status": "in_progress",
      "priority__ne": "low",
      "customer_id": "5",
      "created_date__gte": "2025-01-01"
    },
    "ordering": null
  }
}
```

### Example 6: Transaction Model with Lines (Auto-Included)

```bash
GET /api/wcapi/get/?model_name=order&id=10

Response:
{
  "record": {
    "id": 10,
    "status": "complete",
    "customer_id": 5,
    "lines": [
      {
        "id": 101,
        "item_id": 1,
        "quantity": 5,
        "price": {"sell": 100.00, "cost": 75.00}
      },
      ...
    ]
  }
}
```

---

## Response Format

### Success Response (200 OK)

**List Endpoint:**

```json
{
  "results": [
    {
      "id": 1,
      "field1": "value1",
      "field2": "value2",
      ...
    }
  ],
  "count": 25,
  "total": 245,
  "limit": 500,
  "offset": 0,
  "page": 1,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false,
  "query": {
    "search": "search_term",
    "filters": {
      "status": "active",
      "amount__gte": "1000"
    },
    "ordering": "-dt_created",
    "pagination": {
      "limit": 500,
      "offset": 0
    }
  }
}
```

**Single Record Endpoint:**

```json
{
  "record": {
    "id": 42,
    "field1": "value1",
    "field2": "value2",
    ...
  }
}
```

### Error Responses

**Invalid Model (400):**

```json
{
  "detail": "invalid model"
}
```

**Missing Required Parameter (400):**

```json
{
  "detail": "model_name parameter is required"
}
```

**Unauthorized (401):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Technical Details

### Filter Validation

- Filters are validated against model fields
- Unknown fields are silently ignored
- Invalid lookup operators are skipped
- SQL injection prevented via Django ORM parameterization

### Search Implementation

1. Uses registry configuration (`ModelConfig.search_fields`)
2. Falls back to auto-detect common searchable fields
3. Case-insensitive substring matching (`icontains`)
4. Multiple fields combined with OR logic
5. Graceful fallback if search fails

### Pagination Logic

- **Limit/offset:** Direct slice application: `qs[offset:offset+limit]`
- **Page-based:** Converted to offset: `offset = (page - 1) * page_size`
- **Total count:** Computed before pagination (single query)
- **Page calculation:** `total_pages = ceil(total_count / page_size)`

### Performance Considerations

1. **Search before filters** - Uses database indexes better
2. **Count before pagination** - Single efficient query
3. **Prefetch relations** - Lines prefetched for transaction models
4. **Field allowlist** - Respects permissions via policy layer
5. **Maximum limits** - Prevents resource exhaustion (max 1000 records/query)

---

## Implementation Details

### New Methods in WCAPIGetView

1. **`_parse_filters(request, model_key, ModelCls)`**
   - Extracts and validates filter parameters
   - Supports Django ORM lookups (gte, lte, icontains, etc.)
   - Handles 'ne' (not equal) via Q object negation
   - Returns safe filter dictionary

2. **`_parse_search(request, model_key, ModelCls)`**
   - Extracts search query from 'q' or 'search' param
   - Returns search string or None

3. **`_apply_search(qs, search_query, model_key, ModelCls)`**
   - Applies full-text search using Q objects
   - Uses registry config for searchable fields
   - Auto-detects common fields as fallback
   - Handles search failures gracefully

4. **`_apply_filters(qs, filters)`**
   - Applies filters to queryset
   - Handles 'ne' filters via exclude()
   - Returns filtered queryset

5. **`_parse_pagination(request)`**
   - Supports both limit/offset and page-based pagination
   - Returns (limit, offset) tuple
   - Enforces min/max constraints

6. **`_parse_ordering(request, model_key, ModelCls)`**
   - Validates field name exists
   - Maps common names (created_at→dt_created)
   - Returns safe ordering string or None

7. **`_handle(model_key, record_id, fields, request)`**
   - Main orchestrator
   - Coordinates all parsing and filtering
   - Returns properly formatted response

### Registry Integration

The enhancement works with existing registry configuration:

```python
# In registry or model policies:
ModelConfig(
    key='invoice',
    model=Invoice,
    search_fields=['number', 'customer_name', 'description'],  # Used for search
)
```

If `search_fields` not configured, auto-detection finds searchable fields.

---

## Backward Compatibility

✅ **Fully backward compatible**

- Old requests still work unchanged
- New features are opt-in via parameters
- Filter syntax is additive (doesn't break existing params)
- Response format extended with new pagination fields

**Example: Old style still works:**

```bash
# Old style (still works)
GET /api/wcapi/get/?model_name=invoice&limit=100&offset=0

# New style
GET /api/wcapi/get/?model_name=invoice&status=sent&q=customer&page=1&page_size=25&ordering=-dt_created
```

---

## API Quality Improvements

### What Was Fixed/Improved

| Issue | Before | After |
|-------|--------|-------|
| Filter support | Basic only | Advanced with operators |
| Search capability | None | Full-text search |
| Pagination | limit/offset only | Both limit/offset and page-based |
| Ordering | Basic only | Validated with fallback |
| Error handling | Minimal | Comprehensive with graceful degradation |
| Response metadata | Limited | Complete with query echo |
| Documentation | Sparse | Comprehensive with examples |
| Field validation | None | Database field validation |
| SQL injection | Potential | Prevented via ORM |
| Resource limits | None | Max 1000 records enforced |

### Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Clear method separation of concerns
- ✅ Error handling with graceful fallbacks
- ✅ Database field validation
- ✅ SQL injection prevention
- ✅ Rate limiting via max_page_size
- ✅ Comprehensive OpenAPI schema

---

## Testing the Enhancement

### Test Cases Recommended

```python
# Basic filtering
GET /api/wcapi/get/?model_name=invoice&status=sent

# Multiple filters
GET /api/wcapi/get/?model_name=invoice&status=sent&priority=high

# Comparison operators
GET /api/wcapi/get/?model_name=invoice&total__gte=1000&total__lte=5000

# Search
GET /api/wcapi/get/?model_name=invoice&q=customer%20name

# Pagination - offset style
GET /api/wcapi/get/?model_name=invoice&limit=50&offset=100

# Pagination - page style
GET /api/wcapi/get/?model_name=invoice&page=2&page_size=25

# Ordering
GET /api/wcapi/get/?model_name=invoice&ordering=-dt_created

# Combined
GET /api/wcapi/get/?model_name=invoice&status=sent&q=search&page=1&page_size=10&ordering=-dt_created

# Not equal filter
GET /api/wcapi/get/?model_name=invoice&status__ne=canceled

# String matching
GET /api/wcapi/get/?model_name=contact&email__icontains=gmail
```

---

## Summary

The enhanced `/wcapi/get` endpoint is now:

✅ **Robust** - Handles complex queries with validation  
✅ **Universal** - Works with any model in the registry  
✅ **Safe** - Prevents SQL injection and resource abuse  
✅ **Flexible** - Multiple filter/search/pagination styles  
✅ **Well-Documented** - Comprehensive OpenAPI schema  
✅ **Performant** - Optimized query ordering and prefetching  
✅ **Backward Compatible** - No breaking changes  

**Ready for production use as the primary data query interface.**
