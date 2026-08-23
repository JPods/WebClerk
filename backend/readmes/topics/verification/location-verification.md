# Address verification via sync connections

<!-- TOC START -->

## Table of Contents

- [Address verification via sync connections](#address-verification-via-sync-connections)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Connection](#connection)
  - [Flow](#flow)
  - [Review and apply](#review-and-apply)
  - [Next steps](#next-steps)

<!-- TOC END -->

## Overview

Addresses are verified via `sync.Connection` with type `address_verification`. By default we stub an OSM-like result, creating an auditable `sync.Bundle` with `review.status=pending`.

## Connection

- type: `address_verification`
- config example:

```json
{ "provider": "stub", "mode": "stub" }
```

## Flow

- `address.queue_verification('osm')` enqueues `validate_address_osm`.
- Task uses `apps.sync.services.address_verification.verify_address_via_connection({address1,...})`.
- Bundle captures masked `config`, normalized `result` (status/match_score), and `payload.address`.

## Review and apply

- On acceptance, update `Address.metadata.versioning.validation` fields and optionally set normalized address/lat/long.

## Next steps

- Integrate Nominatim/Google Maps provider calls with proper mapping.
- Add acceptance admin actions (similar to email) if required.
