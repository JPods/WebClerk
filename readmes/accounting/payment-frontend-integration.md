# Payments Module

> **Version**: 1.0  
> **Created**: 2026-03  
> **Scope**: Payment lifecycle — list, detail, panel, dialog, and apply-payments  
> **Related**: [transaction-services.md](./transaction-services.md), [refs-links.md](./refs-links.md)

---

## Overview

The payment module provides full CRUD for Payment records and a bulk A/R reconciliation workflow (Apply Payments). Payment is **not** a `TransactionBaseModel` — it has its own model, serializer, and standalone detail page.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Payment Module                        │
│                                                         │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ PaymentList   │  │ PaymentDetail │  │ ApplyPayments│ │
│  │ (table/CRUD)  │  │ (view/edit)   │  │ (bulk A/R)   │ │
│  └──────┬───────┘  └───────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│  ┌──────┴──────────────────┴──────────────────┴───────┐ │
│  │              paymentApi.ts (wcapi SDK)              │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                             │
│  ┌────────────┐  ┌────────┴───────┐  ┌──────────────┐  │
│  │PaymentPanel│  │ PaymentDialog  │  │usePayment    │  │
│  │ (embedded) │  │ (create modal) │  │Application   │  │
│  └────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                    wc3 REST API
                    /api/transactions/payments/
```

---

## File Map

### Types & Services

| File | Purpose |
|------|---------|
| [types/Payment.ts](../../src/apps/transactions/models/payment/types/Payment.ts) | `Payment`, `PaymentStatus`, `PaymentRefs`, `PaymentMetadata`, request types |
| [services/paymentApi.ts](../../src/apps/transactions/models/payment/services/paymentApi.ts) | wcapi SDK calls + direct REST for `apply_to_invoice` |

### Pages

| File | Route | Purpose |
|------|-------|---------|
| [PaymentListPage.tsx](../../src/apps/transactions/models/payment/pages/PaymentListPage.tsx) | `/transactions/payment/list` | AdvancedDataTable with filters, bulk delete, database search |
| [PaymentDetailPage.tsx](../../src/apps/transactions/models/payment/pages/PaymentDetailPage.tsx) | `/transactions/payment/detail/:id?` | Standalone view/edit/add — two-column layout |
| [ApplyPayments.tsx](../../src/apps/transactions/pages/ApplyPayments.tsx) | `/transactions/apply-payments` | Bulk A/R reconciliation (invoice ↔ payment matching) |

### Components

| File | Purpose |
|------|---------|
| [PaymentPanel.tsx](../../src/apps/common/components/panels/PaymentPanel.tsx) | Embedded panel for OrderDetail / InvoiceDetail — column-header rows with setup dialog |
| [PaymentDialog.tsx](../../src/apps/transactions/components/PaymentDialog.tsx) | Rich payment creation modal — CC/check/address metadata, auto-calc |

### Hooks

| File | Purpose |
|------|---------|
| [usePaymentApplication.ts](../../src/apps/transactions/hooks/usePaymentApplication.ts) | Apply-payment business logic — balance calcs, application API calls |

---

## Data Model

### Payment (wc3)

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | PK |
| `invoice` | FK → Invoice | Nullable — null for order-level deposits |
| `contact` | FK → Contact | Required |
| `amount` | decimal | Original payment amount |
| `amount_available` | decimal | Remaining unapplied balance |
| `status` | string | `pending` · `completed` · `processing` · `failed` · `cancelled` · `refunded` · `partially_refunded` |
| `gateway` | string | `manual` · `spreedly` |
| `payment_method` | FK → PaymentMethod | Nullable |
| `reference_number` | string | Check #, approval code, transaction ID |
| `dt_payment` | datetime | When payment was received |
| `fee` | decimal | Processing fee |
| `is_reconciled` | bool | Whether reconciled in accounting |
| `refs` | JSONB | `{ customer_id, order_ids, invoice_ids, ... }` |
| `metadata` | JSONB | CC details, check details, billing address (see below) |
| `notes` | text | Free-form |

### PaymentApplication (wc3)

Many-to-many join table linking a Payment to one or more Invoices.

| Field | Type | Notes |
|-------|------|-------|
| `payment` | FK → Payment | |
| `invoice` | FK → Invoice | |
| `amount_applied` | decimal | Portion of payment applied to this invoice |
| `unique_together` | | `['payment', 'invoice']` — one application per pair |

### Card Data — Token-in-a-Token (established 2026-08-05)

**WC3 NEVER stores card numbers, CVVs, or replayable tokens.**

Card data is collected by Spreedly's client-side SDK (secure iframe). WC3 JS never touches it. After payment, WC3 stores only a reference in `payment.refs.card`:

```jsonc
{
  "card": {
    "pm_token": "AbC123...",       // Spreedly payment method token (reference to a reference)
    "last4": "4242",               // display only
    "brand": "visa",               // display only
    "exp_month": "12",             // display only
    "exp_year": "2028",            // display only
    "fingerprint": "xyz..."        // detects same card across contacts
  }
}
```

**What is NOT stored:** card number, CVV, full PAN, Spreedly access secret, anything replayable. The `pm_token` is a reference to Spreedly's vault entry, which is itself a tokenized reference to the card. Token in a token.

**Manual payment metadata** (check, cash, wire):

```jsonc
{
  // Check
  "check_number": "5678",
  "check_bank": "First National",
  
  // Billing Address (AVS — manual entry only)
  "billing_company": "Acme Corp",
  "billing_zip": "90210"
}
```

---

## Key Behaviors

### Payment ≠ Transaction

Payment does **not** extend `TransactionBaseModel`. It has no line items, no tax calculation, no shipping. PaymentDetailPage is a standalone component — it does not use `TransactionDetailBase`.

### Customer Tracking

Customer is tracked via `refs.customer_id` (JSONB), not a direct FK. The `contact` FK stores the billing contact. To find all payments for a customer, query by `refs__customer_id` or by `contact__org_id`.

### Apply Payments Workflow

The Apply Payments page mirrors the legacy wc2 `ApplyPayments` form:

1. **Search customer** → loads their unpaid invoices + available payments
2. **Select invoice(s)** from top table, **select payment** from bottom table
3. **Enter amount** → auto-calculates difference
4. **Apply** → creates `PaymentApplication` records, decrements `amount_available`
5. **Auto-apply** → applies payment to oldest invoices first (FIFO)

### PaymentDialog Metadata

PaymentDialog collects CC/check/address fields and stores them in `payment.metadata` (not separate columns). This matches the legacy wc2 pattern where Table 28 stored these in dedicated fields — the JSONB approach is the wc3 equivalent.

Card type is returned by Spreedly after tokenization — no client-side detection needed.

### PaymentPanel Column Setup

PaymentPanel follows the ContactPanel pattern for configurable columns:

```
useColumnSetups("panel:payments")
  → defaultConfig (all visible)
  → activeConfig (from saved setup)
  → visibleCols Set<string>
  → ColumnSetupDialog (open/title/columnMetas/config/onSave)
```

Available columns: `status`, `amount`, `amount_available`, `payment_method`, `reference`, `invoice`, `dt_payment`, `notes`.

---

## Legacy Crosswalk

### wc2 Table 28 (Payments) → R25

| wc2 Form | R25 Equivalent | Notes |
|----------|----------------|-------|
| **Output** (list) | `PaymentListPage` | Table columns mapped: CustomerID → customer_name, TypePay → payment_method_name, Amount/AmountAvailable preserved |
| **Input** (detail) | `PaymentDetailPage` | Page 1 (customer/refs) + Page 2 (payment fields/CC/check/address) collapsed into single two-column layout |
| **Included** (panel) | `PaymentPanel` | Embedded in parent detail pages, same columns: Ref Inv, Amt Avail, Orig Amt, Paid date, Type, Comment |
| **diaMakePay** (dialog) | `PaymentDialog` | Total/Payment/Difference calc, credit toggle, CC fields with card-type detection, check fields, billing address |
| **ApplyPayments** (form) | `ApplyPayments` page | Two-listbox layout preserved: invoices top, payments bottom. Search-by-account, apply, auto-apply-oldest |

### ApplyPayments Form Buttons → R25 Actions

| wc2 Button | Variable | R25 Feature |
|------------|----------|-------------|
| Show All Invoices | `b23` | "Show All" toggle on invoices panel |
| Show All Payments | `b25` | "Show All" toggle on payments panel |
| Search by Account (Inv) | `b24` | Customer search → loads invoices |
| Search by Account (Pay) | `b26` | Customer search → loads payments |
| Offset Invoice | `b12` | Not yet implemented |
| Create Payment | `bPayment` | "Make Payment" button → PaymentDialog |
| Apply (Debit) | `b11` | "Apply to Selected" button |
| Apply (Credit) | `b13` | Credit toggle in PaymentDialog |
| Auto-fill amounts | `b31`/`b32` | Auto-calc in apply amount field |
| Alt Payer toggle | `bpayAlt` | Not yet implemented |
| Alt search fields | `sAltCo`/`sAltPhone`/`sAltZip`/`sAltAcct` | Not yet implemented |
| View Cash Detail | `bdCash`/`bdCash2` | Not yet implemented (DCash table) |

### Currency / Exchange Rate

The legacy form includes currency display and `[Invoice:26]exchangeRate` field. R25 does not yet handle multi-currency payments — this is a future enhancement.

---

## Routes

| Route constant | Path | Component |
|----------------|------|-----------|
| `transactionsPaymentList` | `/transactions/payment/list` | `PaymentListPage` |
| `transactionsPaymentDetail` | `/transactions/payment/detail/:id?` | `PaymentDetailPage` |
| `transactionsApplyPayments` | `/transactions/apply-payments` | `ApplyPayments` |

Sidebar entries under **Transactions**: "Payments" and "Apply Payments".

---

## Gateway Architecture — Spreedly (established 2026-08-05)

### Why Spreedly

Universal payment aggregator. One backend integration → 100+ gateways. User picks their gateway (Stripe, PayPal, Braintree, Authorize.Net, etc.) in Settings. WC3 talks to Spreedly; Spreedly talks to the gateway.

Square is not supported by Spreedly. Direct integration can be added later if needed.

### Flow

```
Browser                          Spreedly SDK (iframe)         Spreedly API           Gateway
  │                                    │                          │                     │
  │  Card entry in secure iframe ───►  │                          │                     │
  │  (WC3 JS never touches card)       │                          │                     │
  │  ◄── payment_method_token ───────  │                          │                     │
  │                                    │                          │                     │
  │  POST /payments/process/           │                          │                     │
  │  { pm_token, invoice_id, amt } ──────────────────────────►    │                     │
  │                                    │            purchase() ──────────────────────►   │
  │                                    │            ◄── result ──────────────────────    │
  │  ◄── { status, message } ─────────────────────────────────    │                     │
```

### Backend

| File | What it does |
|------|-------------|
| `services/payment_gateways.py` | `SpreedlyService` — purchase, authorize, capture, void, credit, refund |
| `services/payment_gateways.py` | `process_payment()` — wires Payment record to Spreedly |
| `services/payment_gateways.py` | `refund_payment()` — void-then-credit pattern |
| `views/payment_views.py` | `POST /payments/process/`, `POST /payments/refund/`, `POST /payments/webhooks/spreedly/` |
| Setting #625 | `purpose=payment_gateway` — Spreedly credentials, active gateway token |

### Configuration

Setting `payment_gateway` (purpose=payment_gateway):
```jsonc
{
  "spreedly": {
    "environment_key": "",       // public — client-side SDK
    "access_secret": "",         // server-only
    "webhook_signing_key": ""
  },
  "active_gateway_token": "",    // from Spreedly after adding gateway
  "active_gateway_type": "",     // stripe, paypal, braintree, etc.
  "test_mode": true,
  "currency": "USD"
}
```

### Frontend (pending)

Needs: Spreedly Web SDK script, hosted fields iframe for card number + CVV, token callback that POSTs to `/payments/process/`. All checkout experiences (card, Apple Pay, Google Pay, PayPal button) produce the same `payment_method_token`.

---

## Not Yet Implemented

Features from legacy that are documented but not yet built:

- **Offset Invoice** — creating a credit memo to offset an invoice balance
- **Alt Payer** — searching for an alternate payer by company/phone/zip/account
- **DCash Detail** — viewing cash drawer detail records linked to payments
- **Multi-currency** — exchange rate display and currency conversion
- **Payment Terms** — term-based discount calculation on apply
- **Batch reconciliation** — marking multiple payments as reconciled
