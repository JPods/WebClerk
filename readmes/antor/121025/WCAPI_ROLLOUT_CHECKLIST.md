# WCAPI Enhancement - Integration & Rollout Checklist

**Date:** December 10, 2025  
**Version:** 1.0  
**Status:** Ready for Rollout

---

## Pre-Rollout Verification

### Code Quality
- [x] Code passes Django system check
- [x] No syntax errors
- [x] No import errors
- [x] Backward compatible (old queries still work)
- [x] Type hints present throughout
- [x] Docstrings complete
- [x] Error handling in place

### Security
- [x] SQL injection prevention (Django ORM)
- [x] Field access control integrated (policy layer)
- [x] Resource limits enforced (max 1000 records)
- [x] Input validation comprehensive
- [x] Query parameters safely parsed

### Documentation
- [x] Complete implementation guide (WCAPI_GET_ENHANCEMENT.md)
- [x] Quick reference (WCAPI_QUICK_REFERENCE.md)
- [x] Delivery summary (WCAPI_ENHANCEMENT_DELIVERY.md)
- [x] OpenAPI schema updated
- [x] Examples provided

### Testing
- [x] Test suite created (35+ tests)
- [x] Filter tests pass
- [x] Search tests pass
- [x] Pagination tests pass
- [x] Ordering tests pass
- [x] Combined query tests pass
- [x] Error handling tests pass

---

## Deployment Steps

### Step 1: Code Deployment
```bash
# 1. Pull the enhanced code
git pull

# 2. Run Django checks
python manage.py check

# 3. Run migrations (if any)
python manage.py migrate

# 4. Run test suite
python manage.py test apps.core.tests.test_wcapi_enhanced -v 2

# 5. Clear cache if used
python manage.py clear_cache  # If cache is configured
```

**Expected Result:** ✅ All tests pass, system check passes

### Step 2: Verify Endpoint

```bash
# Test basic request
curl "http://localhost:8000/api/wcapi/get/?model_name=proposal"

# Test with filters
curl "http://localhost:8000/api/wcapi/get/?model_name=proposal&status=sent"

# Test with search
curl "http://localhost:8000/api/wcapi/get/?model_name=proposal&q=customer"

# Test with pagination
curl "http://localhost:8000/api/wcapi/get/?model_name=proposal&page=1&page_size=25"
```

**Expected Result:** ✅ All requests return 200 with proper JSON

### Step 3: Frontend Testing

**Provided Documentation Link:** `readmes/WCAPI_QUICK_REFERENCE.md`

**Test Cases:**
- [ ] Basic filter works
- [ ] Multiple filters work
- [ ] Search works
- [ ] Pagination works (both modes)
- [ ] Ordering works
- [ ] Combined queries work
- [ ] Error responses are handled

### Step 4: Performance Validation

**Query Performance:**
```bash
# Monitor slow queries (if enabled)
# Check that queries use indexes properly
# Look for N+1 query issues

# Sample load test
for i in {1..10}; do
  curl "http://localhost:8000/api/wcapi/get/?model_name=invoice&page=$i&page_size=100" > /dev/null
done
```

**Expected Result:**
- Queries complete in < 500ms
- No N+1 query patterns
- Database indexes utilized

---

## Post-Deployment Monitoring

### Metrics to Track

**Response Times:**
- [ ] Baseline: Average response time documented
- [ ] Monitor: Track response times for first week
- [ ] Alert: Set threshold if > 1 second

**Error Rates:**
- [ ] Document: Current error rate baseline
- [ ] Monitor: Track 400/500 errors
- [ ] Alert: Spike in 5xx errors

**Usage Patterns:**
- [ ] Track: Which filters most commonly used
- [ ] Track: Pagination patterns (page vs limit/offset)
- [ ] Track: Search vs filter usage

**Resource Usage:**
- [ ] Database: Monitor query counts
- [ ] Memory: Check for leaks
- [ ] CPU: Monitor during peak usage

### Logging

**Add to application monitoring:**
```python
# Log slow queries (>500ms)
# Log failed searches
# Log invalid filter attempts
# Log resource limit hits (max 1000 records)
```

### Rollback Plan

If issues arise:

```bash
# Revert to previous version
git revert <commit-hash>

# Run migrations if needed
python manage.py migrate

# Clear cache
python manage.py clear_cache

# Restart application
systemctl restart webclerk3  # or docker-compose restart
```

---

## Frontend Integration

### React Component Usage Example

```javascript
// Using the enhanced /wcapi/get endpoint
const fetchProposals = async (filters) => {
  const params = new URLSearchParams();
  params.append('model_name', 'proposal');
  
  // Add filters
  if (filters.status) {
    params.append('status', filters.status);
  }
  
  // Add search
  if (filters.q) {
    params.append('q', filters.q);
  }
  
  // Add pagination
  params.append('page', filters.page || 1);
  params.append('page_size', filters.page_size || 25);
  
  // Add ordering
  if (filters.ordering) {
    params.append('ordering', filters.ordering);
  }
  
  const response = await fetch(
    `/api/wcapi/get/?${params.toString()}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  
  return response.json();
};

// Usage
const data = await fetchProposals({
  status: 'sent',
  q: 'urgent',
  page: 1,
  page_size: 25,
  ordering: '-dt_created'
});
```

### API Documentation Link

**Share with frontend team:**
- `readmes/WCAPI_QUICK_REFERENCE.md` (start here)
- `readmes/WCAPI_GET_ENHANCEMENT.md` (detailed reference)

---

## Configuration Recommendations

### Django Settings (Optional Enhancements)

```python
# settings.py

# WCAPI Configuration
WCAPI_MAX_LIMIT = 1000  # Enforce maximum records per query
WCAPI_DEFAULT_LIMIT = 500  # Default if not specified
WCAPI_MAX_SEARCH_FIELDS = 10  # Limit search across fields
WCAPI_TIMEOUT = 30  # Query timeout in seconds

# Logging for WCAPI
LOGGING = {
    'version': 1,
    'handlers': {
        'wcapi': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/wcapi.log',
        },
    },
    'loggers': {
        'apps.core.views.wcapi': {
            'handlers': ['wcapi'],
            'level': 'DEBUG',
        },
    },
}
```

### Registry Configuration

**Optional: Configure search fields per model**

```python
# In your registry configuration
from apps.core.utils.registry import ModelConfig

ModelConfig(
    key='proposal',
    model=Proposal,
    search_fields=['name', 'customer_name', 'description'],  # Explicitly configured
)

ModelConfig(
    key='invoice',
    model=Invoice,
    search_fields=['number', 'reference', 'customer_name'],  # Explicitly configured
)
```

If not configured, automatic detection finds text fields as fallback.

---

## Common Questions (FAQ)

### Q: Will old API requests break?
**A:** No, fully backward compatible. Old requests work exactly as before.

### Q: How many filters can I use at once?
**A:** No limit - combine as many as needed. All combined with AND logic.

### Q: Can I search across all fields?
**A:** No - uses configured search_fields or auto-detects text fields. Prevents search spam.

### Q: What's the maximum number of records I can get?
**A:** Maximum 1000 per request. Use pagination for more.

### Q: Does ordering work with filtering?
**A:** Yes, all features work together. Order the filtered results.

### Q: Can I use regex in search?
**A:** Not in this version. Uses substring matching (icontains). Regex can be added later.

### Q: What about field access control?
**A:** Respects existing policy layer. Users can only query fields they have access to.

### Q: Can I export results to CSV?
**A:** Not in this version. Can be added as future feature.

### Q: Is there a way to see exactly what query is running?
**A:** Yes! Response includes "query" object showing filters, search, ordering applied.

---

## Success Criteria

- [x] Code passes all validation (Django check)
- [x] 35+ tests pass
- [x] Backward compatible
- [x] Documentation complete
- [x] Security validated
- [x] Performance optimized
- [ ] Deployed to staging (TBD)
- [ ] Frontend testing complete (TBD)
- [ ] Production deployment (TBD)

---

## Sign-Off

| Role | Name | Date | Sign |
|------|------|------|------|
| Developer | | | |
| QA | | | |
| DevOps | | | |
| Product | | | |

---

## Related Documents

- **Implementation:** `/apps/core/views/wcapi.py`
- **Tests:** `/apps/core/tests/test_wcapi_enhanced.py`
- **Detailed Guide:** `readmes/WCAPI_GET_ENHANCEMENT.md`
- **Quick Reference:** `readmes/WCAPI_QUICK_REFERENCE.md`
- **Delivery Summary:** `readmes/WCAPI_ENHANCEMENT_DELIVERY.md`

---

## Support Contacts

**Technical Questions:**
- Backend: [Backend Team Contact]
- Frontend Integration: [Frontend Team Contact]

**Issues/Bugs:**
- Report in: [Issue Tracking System]
- Tag with: `wcapi-enhancement`

---

**Last Updated:** December 10, 2025  
**Status:** ✅ READY FOR DEPLOYMENT

