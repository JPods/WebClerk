# WCAPI /get Endpoint - Quick Reference

**Last Updated:** December 10, 2025  
**Status:** ✅ Enhanced and Validated

---

## Quick Start

### Basic Usage
```bash
# Get all records
GET /api/wcapi/get/?model_name=invoice

# Get single record
GET /api/wcapi/get/?model_name=invoice&id=42

# Filter records
GET /api/wcapi/get/?model_name=invoice&status=sent
```

---

## Filter Syntax (All Supported)

### Equality (Basic)
```
?field=value
?status=active
?priority=high
```

### Comparison Operators
```
?amount__gte=1000        # ≥
?amount__lte=5000        # ≤
?amount__gt=1000         # >
?amount__lt=5000         # <
?created__gte=2025-01-01
?created__lte=2025-12-31
```

### String Matching
```
?name__icontains=john          # Contains (case-insensitive)
?email__startswith=admin       # Starts with
?code__endswith=_FINAL         # Ends with
?reference__exact=REF-001      # Exact (case-sensitive)
?reference__iexact=ref-001     # Exact (case-insensitive)
```

### Special Operators
```
?status__ne=canceled          # Not equal
?tags__in=urgent,high         # In list (comma-separated)
?is_active__isnull=true       # IS NULL / IS NOT NULL
```

---

## Search Syntax

```
?q=search_term                # Full-text search
?search=search_term           # Alternative parameter
?q=john+doe                   # Multi-word search
```

---

## Pagination Syntax

### Limit/Offset (Default)
```
?limit=50&offset=100          # 50 records starting at position 100
?limit=25                     # 25 records from start (offset=0)
```

### Page-Based
```
?page=1&page_size=25          # Page 1, 25 per page
?page=2&page_size=50          # Page 2, 50 per page
```

**Limits:**
- Max page_size/limit: 1000
- Min: 1
- Default: 500

---

## Ordering Syntax

```
?ordering=field_name          # Ascending
?ordering=-field_name         # Descending
?order_by=created_at          # Alternative param
?order_by=-created_at         # Alternative descending
```

**Auto-mapped fields:**
- `created_at` → `dt_created`
- `updated_at` → `dt_modified`

---

## Complete Examples

### Example 1: Search + Filter + Pagination
```
GET /api/wcapi/get/?model_name=proposal&q=urgent&status=sent&page=1&page_size=20
```

### Example 2: Date Range + Ordering
```
GET /api/wcapi/get/?model_name=invoice&created__gte=2025-01-01&created__lte=2025-12-31&ordering=-total
```

### Example 3: Multiple Filters + Search
```
GET /api/wcapi/get/?model_name=order&status=in_progress&priority__ne=low&customer_id=5&q=shipment&limit=50
```

### Example 4: Not Equal + Pagination
```
GET /api/wcapi/get/?model_name=contact&status__ne=inactive&email__icontains=gmail.com&limit=25&offset=50
```

---

## Response Format

### List Response (200 OK)
```json
{
  "results": [
    {"id": 1, "name": "...", "status": "...", ...},
    {"id": 2, "name": "...", "status": "...", ...}
  ],
  "count": 2,
  "total": 45,
  "limit": 500,
  "offset": 0,
  "page": 1,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false,
  "query": {
    "search": "term",
    "filters": {"status": "sent"},
    "ordering": "-dt_created",
    "pagination": {"limit": 500, "offset": 0}
  }
}
```

### Single Record Response (200 OK)
```json
{
  "record": {
    "id": 42,
    "name": "...",
    "status": "...",
    ...
  }
}
```

### Error Response (400/401)
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Key Facts

✅ **Safe** - SQL injection prevented via Django ORM  
✅ **Flexible** - Multiple filter, pagination, and search options  
✅ **Universal** - Works with any registered model  
✅ **Backward Compatible** - Old queries still work  
✅ **Debuggable** - Query echo shows what was applied  
✅ **Performant** - Optimized query ordering and prefetching  

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Field not found" | Check model has that field; use correct field name |
| No results for valid query | Check field values match exactly (except with __icontains) |
| Ordering not working | Ensure field exists; invalid fields silently ignored |
| Search returns nothing | Check search_fields configured in registry; fallback detects text fields |
| Pagination limit too high | Max 1000; values over 1000 are capped |

---

## Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful query |
| 400 | Bad Request | Invalid model, missing params |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | User lacks permission |
| 404 | Not Found | Single record doesn't exist |
| 500 | Server Error | Unexpected error |

---

## Testing the Endpoint

```bash
# Using curl
curl "http://localhost:8000/api/wcapi/get/?model_name=invoice&status=sent&limit=10"

# Using Python requests
import requests
response = requests.get(
    'http://localhost:8000/api/wcapi/get/',
    params={
        'model_name': 'invoice',
        'status': 'sent',
        'amount__gte': 1000,
        'page': 1,
        'page_size': 25
    }
)
print(response.json())

# Using browser (with authentication)
http://localhost:8000/api/wcapi/get/?model_name=invoice&status=sent&limit=10
```

---

## Advanced Usage

### Combined Complex Query
```
GET /api/wcapi/get/?model_name=proposal
    &status__ne=rejected
    &amount__gte=1000
    &amount__lte=10000
    &created__gte=2025-01-01
    &customer_name__icontains=acme
    &q=urgent
    &ordering=-amount
    &page=1
    &page_size=50
```

This request:
1. Excludes rejected proposals
2. Filters for amounts $1,000-$10,000
3. Only recent (2025+)
4. Customer name contains "acme" (case-insensitive)
5. Contains "urgent" in searchable fields
6. Orders by amount descending
7. Returns page 1, 50 per page

---

## Performance Notes

- **Searches are efficient** - Uses database indexes
- **Counts are fast** - Single query
- **Pagination is optimal** - Doesn't count all when possible
- **Large limits are capped** - Max 1000 to prevent resource exhaustion
- **Field validation is automatic** - No invalid queries reach database

---

## Integration Points

- **Used by:** Frontend React application
- **Replaces:** Multiple model-specific list endpoints
- **Complementary:** /wcapi/detail for single record details
- **Authentication:** Standard DRF auth (token, session, etc.)
- **Permissions:** Uses policy-based field access control

---

## Support

For issues or questions about the enhanced WCAPI endpoint:

1. Check `WCAPI_GET_ENHANCEMENT.md` for detailed documentation
2. Review test cases in `apps/core/tests/test_wcapi_enhanced.py`
3. Verify filter syntax matches examples above
4. Check response "query" field to see what was actually applied

