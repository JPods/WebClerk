# Domain verification via sync connections

<!-- TOC START -->

## Table of Contents

- [Domain verification via sync connections](#domain-verification-via-sync-connections)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Connection](#connection)
  - [Flow](#flow)
  - [Review and apply](#review-and-apply)
  - [Next steps](#next-steps)

<!-- TOC END -->

## Overview

Domains/handles (e.g., websites, social) are verified with `sync.Connection` type `domain_verification`. Attempts record a `sync.Exchange` with a normalized result and pending review.

## Connection

- type: `domain_verification`
- config example:

```json
{ "provider": "stub", "mode": "stub" }
```

## Flow

- `domain.queue_verification()` enqueues `validate_domain_basic`.
- Task calls `apps.sync.services.domain_verification.verify_domain_via_connection(path)`.
- Exchange contains masked `config`, normalized `result` (status/reachable/reason).

## Review and apply

- Accept/reject via Exchanges admin. On acceptance, a decision service could update metadata or set status.

## Next steps

- Add real reachability checks and social API verifications.
- Provide admin accept/reject actions specific to Domain when needed.
