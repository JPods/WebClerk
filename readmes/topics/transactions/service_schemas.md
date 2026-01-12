Service JSON Schemas Overview
=============================

Billing Envelope
----------------
Keys:
  currency: 3-letter ISO code
  tiers: chronological list of {unit, rate, cost, min_minutes, dt_effective}
  travel: {per_mile, per_hour, included_miles, dt_updated}
  rounding: {strategy: HALF_UP|BANKERS?, places:int}
  min_charge / max_charge: Optional absolute bounds after computation
  schema_version: integer (current = 1)
  extensions: reserved dict for namespaced future keys

Process Envelope
----------------
Keys:
  steps: [{name, minutes} ... unique name (case-insensitive)]
  dt_updated: epoch ms
  version / schema_version
  extensions: reserved future structure

Travel Envelope
---------------
Keys:
  miles_included, lodging_required, meal_per_diem, notes, dt_updated
  schema_version, extensions

Actions Envelope
----------------
Keys:
  records: list of action dicts created when service added to a transaction
  schema_version, extensions

Audit Log
---------
billing_audit: append-only [{dt, summary, row_version}] capped to last 100 entries.

Concurrency
-----------
row_version: incremented per save; stale writes raise ValidationError.

Charging Flow
-------------
1. Select current tier by unit
2. Enforce min_minutes
3. Compute base (rate * hours)
4. Add travel surcharge (extra miles * per_mile)
5. Apply rounding strategy / places
6. Enforce min_charge / max_charge

Validation Rules
----------------
* Currency must be 3-letter alpha
* Tiers strictly chronological; no duplicate dt_effective
* Units must be one of hour|minute|day|flat
* Non-negative rates/cost/min_minutes/travel fields
* Unique process step names (case-insensitive)

CLI Scan
--------
python manage.py scan_service_billing [--fix] [--limit N]

Future Extensions
-----------------
* Consider separate ServiceRate table for heavy querying
* Additional rounding strategies
* Usage-based / volume tiers (quantity brackets)
