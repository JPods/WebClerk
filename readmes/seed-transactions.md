# Stable Transaction Seed (Deterministic)

This command creates a small, predictable set of transactional data for development and demos.

## What it seeds

- Proposals: Stable Proposal 1..N with 2 lines each
- Sales Orders: SOST-1001.. with 3 lines each
- Invoices: INVST-2001.. with 2 lines each
- Purchase Orders: POST-3001.. with 2 lines each
- Ensures a few Items exist with stable SKUs (STABLE-001, etc.) if missing

## Usage

- Activate venv, then run:
  - python manage.py seed_transactions_stable --count 2 --reset
  - Omit --reset to make it idempotent (won't duplicate existing rows with the same identifiers)

## Verify via API

- After running, check via wcapi endpoints (requires auth):
  - GET /wcapi/get/?model_name=sales_order&query={"order_no":"SOST-1001"}
  - GET /wcapi/get/?model_name=invoice&query={"ida":"2001"}
  - GET /wcapi/get/?model_name=purchase_order&query={"po_no":"POST-3001"}

## Notes

- The seed is deterministic: re-running with the same parameters will update lines but not create duplicates.
- Use --count N to adjust how many of each header are created.
