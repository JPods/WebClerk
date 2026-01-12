author: antor ahmed
time: 2025-12-22 8:42 UTC+6
purpose: refs link issue 

# Add-to-refs changelog

## Summary ✅
This note records the change that automatically appends newly created communication records (email, phone, address/location, domain) to a contact's `refs.links` when created via the universal save endpoint (`/wcapi/save`). The change is defensive and non-blocking if linking fails.

## Key changes 🔧
- **Behavior**: When a communication record is created via the save flow, the system will:
  - Prefer an explicit `contact_id` in the payload; fallback to the authenticated `request.user` when it's a `Contact`.
  - Append a denormalized object (fields chosen from `LINK_DENORMALIZE_FIELDS`) into `contact.refs.links.<bucket>` (note: `address` maps to the `location` bucket for backward compatibility).
  - Persist the contact with minimal update fields (`refs`, `dt_modified`, `version`).
  - Ensure a lightweight bidirectional link using `common.refs.links.ensure_bidirectional()` for quick reverse lookups.

- **Files changed / added**:
  - `apps/core/services/wcapi.py` — implemented auto-linking logic inside `save_item` after creates and return a `linked` flag
  - `apps/transactions/views/wcapi.py` — delegates save to `apps.core.services.wcapi.save_item` to centralize behavior and surface `linked` in responses
  - `apps/communications/tests/test_wcapi_linking.py` — added tests verifying email auto-linking and explicit `contact_id` linking (test file present but not executed)

## Notes & Caveats ⚠️
- Deduplication of denormalized objects in a contact's `refs.links` bucket is **not** implemented (the `ensure_bidirectional` function prevents duplicate link *entries* but not duplicate denormalized objects). Consider adding de-dup logic to avoid repeated denorm objects.
- Linking errors are defensive and will **not** block the creation of the original communication record.
- Tests were added; you can run them with the project's test runner when you're ready.
## Test API example 🧪

Quick curl example (authenticated as a Contact or include `contact_id`):

```bash
curl -X POST "http://localhost:8000/api/wcapi/save/" \
  -H "Content-Type: application/json" \
  -d '{"model_name":"email","data":{"email":"auto+test@example.com","name":"Auto Test"}}'
```

Behavior:
- If the request is authenticated as a `Contact`, the created email will be appended to that contact's `refs.links.email` as a denormalized object.
- Alternatively include `"contact_id": <CONTACT_ID>` in the `data` payload to target a specific contact.

Sample response JSON (successful create):

```json
{"id": 17, "action": "created", "linked": true}
```

Minimal pytest example (already added as `apps/communications/tests/test_wcapi_linking.py`):

```python
def test_wcapi_save_email_auto_links(api_client, staff_user):
    payload = {"model_name": "email", "data": {"email": "auto+docs@test", "name": "doc"}}
    resp = api_client.post('/wcapi/save', payload, format='json')
    assert resp.status_code in (200, 201)
    created_id = resp.data.get('id') or (resp.data.get('data') or {}).get('id')

    staff_user.refresh_from_db()
    emails = (staff_user.refs or {}).get('links', {}).get('email', [])
    assert any(isinstance(e, dict) and e.get('id') == created_id for e in emails)
```