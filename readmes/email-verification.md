# Email verification via sync connections

This project supports a provider-agnostic email verification flow that uses the `sync` app for configuration and exchange logging.

What you get:

- Store provider settings and secrets in `sync.Connection` (type `email_verification`).
- Each verification attempt logs a `sync.Exchange` with masked config, payload, normalized response, and duration.
- Communications tasks update `Email.metadata.versioning.validation` and set `Email.is_verified` based on the normalized result.

Quick start (stub mode, no external calls):

1) Create a connection (via admin/API/fixtures):

   - type: `email_verification`
   - name: `default`
   - config: `{ "provider": "stub", "mode": "stub" }`

2) Trigger validation:

   - Call the Celery task `validate_email_format(email_id)` after creating an Email, or from the admin.

Result schema (normalized):

```json
{"provider": "stub", "status": "stubbed", "deliverability": "unknown", "reason": "stub_mode"}
```

How it works:
- The task calls `apps.sync.services.email_verification.verify_email_via_connection(email)`, which:

   - picks a `Connection` with `type='email_verification'` (by name if specified),
   - performs a stubbed provider call (no network),
   - creates an `Exchange` row with masked config and response,
   - returns a normalized result for the task to persist on `Email`.

Going beyond stub mode:
Additional steps for live providers:

- Add real provider calls inside `email_verification.verify_email_via_connection()`.
- Normalize provider responses to `{provider, status, deliverability, reason}`.
- Keep secrets in `Connection.config` and they will be masked when logged to `Exchange.config`.

Notes:
Notes:

- This flow does not make external requests by default. It is safe to enable in local/dev and can be toggled to live providers later.
- Exchanges are lightweight audit logs; they do not store raw provider payloads unless added explicitly.
