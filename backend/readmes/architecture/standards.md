# Standards: alerts and email normalization


<!-- TOC START -->

## Table of Contents

- [Standards: alerts and email normalization](#standards-alerts-and-email-normalization)
  - [Table of Contents](#table-of-contents)

<!-- TOC END -->

This project defines small, stable dictionaries to reduce noise and keep semantics consistent across providers:

Contents

- ALERT_SEVERITY_ORDER: info < notice < warning < critical < emergency
- ALERT_CATEGORY_SETTINGS: per-category dedupe windows (ms)
- EMAIL_STATUS_MAP: maps provider statuses to {valid, invalid, risky, unknown}

Usage

- Incidents: `trigger_safety_alert(event, details, severity)` normalizes severity and event to a category and includes a `dedupe_ms` hint in the payload.
- Email verification: results are normalized to `{provider, status, deliverability, reason}` using the status map.

Notes

- These are small on purpose. Extend cautiously to avoid overfitting to one vendor.
- Keep defaults conservative; noisy channels should raise dedupe_ms rather than flooding Exchanges.
