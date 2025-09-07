# Connections: providers, keys, and auditing

<!-- TOC START -->

## Table of Contents

- [Connections: providers, keys, and auditing](#connections-providers-keys-and-auditing)
  - [Table of Contents](#table-of-contents)
  - [What is a Connection?](#what-is-a-connection)
  - [Security and operations](#security-and-operations)
  - [Common connection types](#common-connection-types)
  - [Field reference](#field-reference)
  - [Examples](#examples)
  - [Admin/API usage](#adminapi-usage)
  - [Related docs](#related-docs)

<!-- TOC END -->

Connections store provider configuration, credentials, and intent for any external integration. Each request/response made via a Connection is logged as an Exchange for traceability.

## What is a Connection?

A `sync.Connection` represents one integration endpoint or provider definition. Typical uses:

- Email verification providers (e.g., ZeroBounce, Kickbox) with API keys and mode (stub/live).
- Safety alert channel (seeded) used to signal assaults/incidents to webclerk.com.
- Future connectors (payments, messaging, K/V storage) without changing the API surface.

## Security and operations

- Secrets: Prefer environment/secret store. If kept in DB, encrypt at rest and always mask in logs.
- Masking: Exchanges store masked copies of `Connection.config` (api_key/token/secret/password/key are redacted).
- Access: Restrict who can view/edit connections; avoid exposing full config over list views.
- Toggle: Consider adding an `enabled` flag and rate limits per connection.
- Review: Foreign data isn’t auto-applied—Exchanges start in `response.review.status=pending` and must be accepted.

## Common connection types

- `email_verification`
  - config: `{ "provider": "stub|zerobounce|...", "api_key": "...", "mode": "stub|live" }`
  - Used by `apps.sync.services.email_verification.verify_email_via_connection()`.
- `safety_alert` (seeded by `reseed --full`)
  - name: `alert`, purpose: `webclerk.com`, status: `safe`, config.mode=`stub`.
  - Used by `apps.sync.services.incidents.trigger_safety_alert()` to create an Exchange for review/ack.

## Field reference

- `name`: Friendly identifier (e.g., `default`, `alert`).
- `type`: Integration category (e.g., `email_verification`, `safety_alert`).
- `purpose`: Human/context label (e.g., `webclerk.com`).
- `status`: Operational note (e.g., `safe`, `disabled`).
- `config` (JSON): Provider settings; secrets are masked when copied to an Exchange.
- `maps`, `rules`, `encryption`, `relationships`, `scripts`: Optional JSON for transforms and governance.
- `comment`: Freeform notes.

## Examples

Email verification (stub):

```json
{
  "provider": "stub",
  "mode": "stub"
}
```

Email verification (live):

```json
{
  "provider": "zerobounce",
  "api_key": "<secret>",
  "mode": "live"
}
```

Safety alert (seeded default):

```json
{
  "mode": "stub",
  "description": "Default safety alert connection for incident signaling to webclerk.com"
}
```

## Admin/API usage

- Admin: Create/edit in Django admin under Sync → Connections.
- API: Use the Sync connections endpoints (CRUD) to manage records programmatically.
- Smoke test: `python manage.py test_alert_connection --event assault_detected` should create an Exchange.

## Related docs

- `readmes/exchange-review.md`: Review/acknowledgement workflow for Exchanges.
- `readmes/email-verification.md`: Provider-agnostic email verification with Connections.
- `readmes/standards.md`: Severity categories, dedupe windows, and email status normalization.
