# Location verification via sync connections

<!-- TOC START -->

## Table of Contents

- [Location verification via sync connections](#location-verification-via-sync-connections)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Connection](#connection)
  - [Flow](#flow)
  - [Review and apply](#review-and-apply)
  - [Next steps](#next-steps)

<!-- TOC END -->

## Overview

Locations are verified via `sync.Connection` with type `location_verification`. By default we stub an OSM-like result, creating an auditable `sync.Exchange` with `review.status=pending`.

## Connection

- type: `location_verification`
- config example:

```json
{ "provider": "stub", "mode": "stub" }
```

## Flow

- `location.queue_verification('osm')` enqueues `validate_location_osm`.
- Task uses `apps.sync.services.location_verification.verify_location_via_connection({address1,...})`.
- Exchange captures masked `config`, normalized `result` (status/match_score), and `payload.location`.

## Review and apply

- On acceptance, update `Location.metadata.versioning.validation` fields and optionally set normalized address/lat/long.

## Next steps

- Integrate Nominatim/Google Maps provider calls with proper mapping.
- Add acceptance admin actions (similar to email) if required.
