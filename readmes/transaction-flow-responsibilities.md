# Transaction Flow Responsibilities: Frontend (React) vs Backend

<!-- TOC START -->

## Table of Contents

- [Transaction Flow Responsibilities: Frontend (React) vs Backend](#transaction-flow-responsibilities-frontend-react-vs-backend)
  - [Table of Contents](#table-of-contents)
  - [Scope & Flows Covered](#scope-flows-covered)
  - [Core Principles](#core-principles)
  - [Responsibility Matrix (TL;DR)](#responsibility-matrix-tldr)
  - [By Flow](#by-flow)
    - [Proposals](#proposals)
    - [Sales Orders](#sales-orders)
    - [Invoices](#invoices)
    - [Purchase Orders (Receiving)](#purchase-orders-receiving)
  - [Crosscutting Concerns](#crosscutting-concerns)
    - [Validation & Errors](#validation-errors)
    - [Permissions & Field Access](#permissions-field-access)
    - [Concurrency, Idempotency, Versioning](#concurrency-idempotency-versioning)
    - [Observability](#observability)
  - [API Endpoints (Cheat Sheet)](#api-endpoints-cheat-sheet)
  - [UI Patterns (React)](#ui-patterns-react)
  - [Future Enhancements](#future-enhancements)
  - [Summary](#summary)

<!-- TOC END -->

## Scope & Flows Covered

Covers the transactional flows implemented in the transactions app:

- Proposal -> Sales Order -> Invoice
- Purchase Order receiving into inventory

This doc defines which responsibilities live in React (frontend) vs backend (Django/DRF).

## Core Principles

- Canonical model_name everywhere; collections use plural table keys.
- Single source of truth: backend owns state transitions, invariants, and persistence.
- Frontend focuses on UX, local input shaping, and nonauthoritative calculations.
- All responses use the standard envelope (status, code, message, error, data).

## Responsibility Matrix (TL;DR)

Frontend (React):

- Form UX, inline hints, optimistic UI where safe.
- Local-only validations (shape, required fields, obvious constraints).
- Client-side helpers: totals preview, tax preview, quantity entry UI, scan/selection.
- Drive actions by calling explicit endpoints; never fabricate state transitions.

Backend (Django/DRF):

- Create/update headers/lines; enforce invariants (pricing, taxes, states).
- Flow transitions (proposal->SO, SO->invoice) with idempotency and audit.
- Purchase order receiving: inventory updates, receipts, integrity, and locking.
- Permissions (role-based view/edit), concurrency/versioning, error semantics.

## By Flow

### Proposals

Frontend:

- Build/edit proposal + lines UI; local totals preview.
- Validate obvious fields (qty > 0, price non-negative) prior to submit.

Backend:

- Persist headers/lines; compute authoritative totals/discounts/taxes.
- Enforce field-level permissions and required business fields.

### Sales Orders

Frontend:

- Display SO details; allow permitted edits before fulfillment/invoice.
- Trigger conversion from a Proposal via action endpoint.

Backend:

- Enforce status transitions; copy/normalize fields from Proposal.
- Lock down edits once committed; emit audit trail.

### Invoices

Frontend:

- Render invoice details; show balances/totals; allow print/export.

Backend:

- Create from Sales Order; finalize amounts; enforce immutability rules.
- Produce journal-ready values; emit events/hooks for downstream systems.

### Purchase Orders (Receiving)

Frontend:

- Capture received quantities (scan or manual entry); per-line UX.
- Local guardrails (cannot receive negative, cannot exceed obvious caps).

Backend:

- Validate per-line receipts; apply inventory updates atomically.
- Generate receipt records; maintain stock ledger and audit.

## Crosscutting Concerns

### Validation & Errors

- Frontend: basic input checks and user feedback.
- Backend: authoritative validation; return structured error envelope with codes and details.

### Permissions & Field Access

- Backend enforces role-based view/edit via Settings view_edit matrices.
- Frontend respects exposed allowed fields; hides/locks disallowed controls.

### Concurrency, Idempotency, Versioning

- Backend uses optimistic concurrency (HTTP 412 on conflicts) and idempotent action endpoints.
- Frontend retries with conflict dialogs and refresh.

### Observability

- Backend: logs, metrics, audit trails for transitions and receiving.
- Frontend: minimal analytics for UX flows (optional).

## API Endpoints (Cheat Sheet)

Headers/Lines (CRUD):

- Proposals: `/tx/proposals/`, `/tx/proposals/<id>/`, `/tx/proposal-lines/`, `/tx/proposal-lines/<id>/`
- Sales Orders: `/tx/sales-orders/`, `/tx/sales-orders/<id>/`, `/tx/sales-order-lines/`, `/tx/sales-order-lines/<id>/`
- Invoices: `/tx/invoices/`, `/tx/invoices/<id>/`, `/tx/invoice-lines/`, `/tx/invoice-lines/<id>/`
- Purchase Orders: `/tx/purchase-orders/`, `/tx/purchase-orders/<id>/`, `/tx/purchase-order-lines/`, `/tx/purchase-order-lines/<id>/`

Flow Actions:

- Proposal -> Sales Order: `/tx/proposals/<id>/convert-to-sales-order/` (POST)
- Sales Order -> Invoice: `/tx/sales-orders/<id>/convert-to-invoice/` (POST)
- PO Receiving: `/tx/purchase-orders/<id>/receive/` (POST)
- Preview Totals: `/tx/<kind>/<id>/preview-totals/` (GET)

Notes:

- All endpoints return the standard envelope.
- Use singular `model_name` in payloads where required; collections use plural table keys.

## UI Patterns (React)

- Use form state with local validation; only submit valid shapes.
- On action POST success, refresh the authoritative record from backend.
- Handle 400 (fail) with field-level messages; handle 412 with refresh/retry.
- Paginate/filter lists; avoid N+1 calls for related where provided by API.

## Future Enhancements

- Background tasks for heavy recalcs and notifications (Celery hooks).
- WebSocket/ServerSent events for longrunning receiving/imports.
- Draft workflows for partial shipments and backorders.

## Summary

- React owns UX, input shaping, and previews; never source of truth.
- Backend owns transitions, validation, inventory, and audit.
- Call explicit action endpoints for state changes; rely on the envelope for errors and data.
