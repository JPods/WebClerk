# Submission and Verification (Communications)

<!-- TOC START -->

## Table of Contents

- [Submission and Verification (Communications)](#submission-and-verification-communications)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Submission Snapshot](#submission-snapshot)
  - [Verification Stubs](#verification-stubs)
  - [Applying Results](#applying-results)
  - [Clearing the Snapshot](#clearing-the-snapshot)
  - [Next Steps](#next-steps)

<!-- TOC END -->

## Overview

Communications models (Location, Email, Phone) support a submission/verification flow. On create, we capture the original client payload in `prefs.submission.as_submitted` for traceability. Background tasks (Celery) can verify records (e.g., addresses via OpenStreetMap/Nominatim) and update model fields and metadata.

## Submission Snapshot

- A generic helper `BaseModel.record_submission_snapshot(data, actor_id)` stores a bounded snapshot under:
  - `prefs.submission.as_submitted = { data, dt, by }`
- This is added during create in: EmailView, PhoneView, LocationView.

## Verification Stubs

- Celery tasks exist but are stubbed (no external calls yet):
  - `validate_location_osm(location_id)` — marks provider `osm`, status `stubbed`.
  - `validate_email_format(email_id)` — marks provider `local`, status `stubbed`.
  - `validate_phone_basic(phone_id)` — marks provider `local`, status `stubbed`.
- Trigger address verification: `location.queue_verification('osm')`.

## Applying Results

- `Location.apply_validation_result(result)` updates:
  - `metadata.versioning.validation = { provider, status, match_score? }`
  - `metadata.history.verified.dt` (epoch ms)
  - Lat/long and normalized fields if provided.

## Clearing the Snapshot

- After successful validation, call `Location.clear_submission_snapshot(keep_copy_in_versioning=False)`.
  - Optionally archives a copy into `metadata.versioning.submission_archived`.

## Next Steps

- Implement real OSM/Nominatim lookups with rate limiting and retries.
- Add nightly re-verification for stale records via Celery beat.
- Add post_save signals to auto-queue verification when relevant fields change.
- Extend similar queue/apply patterns to Email and Phone if deeper checks are needed.
