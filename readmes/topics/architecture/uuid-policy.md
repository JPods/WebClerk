# UUID Policy

## What UUID Is For

UUID is the inter-database sync identifier. It exists so that records created
in one database can be matched to the same record in another database when
syncing via the Connection + Bundle system.

UUID is **not** for React. It is **not** for the API consumer. It is **not**
a public identifier.

## Rules

| Context | UUID visible? | Why |
|---------|--------------|-----|
| Database (psql) | Yes | It's a column — query it directly |
| Django admin | Yes | Admin tool for database operators |
| wcapi GET response | Stripped | React doesn't need it |
| wcapi save payload | Stripped | Immutable — backend rejects changes |
| Sync (Connection/Bundle) | Yes | This is what it's for |
| React frontend | Never | Use `id` for routing, `ida` for display |

## Why React Strips It

The backend enforces UUID immutability. If React sends a UUID in a save
payload — even the same value — the backend rejects it as a mutation attempt.
React strips `uuid` from all save payloads (headers and lines) in
`saveTransactionWithLines()` in `wcapi.ts`.

## If Admins Need UUID

Use Django shell or psql directly:

```sql
SELECT id, ida, uuid FROM transactions_order WHERE id = 34;
```

```bash
python manage.py shell -c "
from apps.transactions.models import Order
o = Order.objects.get(id=34)
print(o.uuid)
"
```

If a future admin UI needs UUID access (e.g., for manual sync debugging),
add it to the databrowser detail view behind an admin-only flag — not to
the transaction detail form.
