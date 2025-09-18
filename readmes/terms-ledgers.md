# Terms ➜ Ledgers

<!-- TOC START -->

## Table of Contents

- [Terms ➜ Ledgers](#terms--ledgers)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Examples](#examples)
  - [Implementation Notes](#implementation-notes)

<!-- TOC END -->

## Overview

- Terms drive how ledger entries are scheduled and discounted.
- Options for multi-installment terms:
  1) Record multiple due dates in invoice metadata, or
  2) Create separate Ledger records per installment (preferred, clearer accounting trail).

## Examples

- Net30
  - One Ledger, `dt_due = invoice_dt + 30 days`.

- Net20 with 2% discount in 10 days
  - One Ledger, `dt_due = invoice_dt + 20 days`.
  - Discount potential 2% if paid by `dt_discount_due = invoice_dt + 10 days`.

- 3 equal payments net 30
  - Create 3 Ledger records (preferred) with equal shares and due dates spaced by `days_in_period`.
  - Alternatively, store schedule in `invoice.metadata['terms']['schedule']` and keep a single Ledger (not preferred).

## Implementation Notes

- Service `accounts.services.terms_ledger`:
  - `compute_schedule(invoice_dt, total, term)` returns a schedule.
  - `create_ledger_records(invoice, total, term, strategy='records')` creates ledgers or writes schedule to metadata.
- Concurrency: when applying payments, ensure ledger, payment, and invoice are updated within a transaction.
