# Phone verification via sync connections

<!-- TOC START -->

## Table of Contents

- [Phone verification via sync connections](#phone-verification-via-sync-connections)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Connection](#connection)
  - [Flow](#flow)
  - [Review and apply](#review-and-apply)
  - [Next steps](#next-steps)

<!-- TOC END -->

## Overview

Phone numbers are verified through provider-agnostic `sync.Connection` records. Each attempt creates a `sync.Bundle` with masked config and a normalized `response`, initially `response.review.status=pending`.

## Connection

- type: `phone_verification`
- config example:

```json
{ "provider": "stub", "mode": "stub" }
```

## Flow

- Model helper: `phone.queue_verification()` enqueues `validate_phone_basic`.
- Task calls `apps.sync.services.phone_verification.verify_phone_via_connection(number)`.
- An Bundle is created with `payload.phone`, masked `config`, and normalized `result` (status/valid/reason).

## Review and apply

- Use Bundles admin to inspect and accept/reject.
- A future decision service can set metadata flags or derived fields (e.g., normalized E.164) upon acceptance.

## Next steps

- Add real providers and E.164 normalization.
- Add admin actions mirroring email decisions for phone.
