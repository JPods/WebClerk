# Exchanges Architecture: Sync Logs vs FX Rates vs Transactions

<!-- TOC START -->

## Table of Contents

- [Exchanges Architecture: Sync Logs vs FX Rates vs Transactions](#exchanges-architecture-sync-logs-vs-fx-rates-vs-transactions)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Models and Responsibilities](#models-and-responsibilities)
  - [Update and Logging Flows](#update-and-logging-flows)
  - [Notes and Future Work](#notes-and-future-work)

<!-- TOC END -->

## Overview

We explicitly separate three concerns:

- Synchronization exchanges with external systems (what we did/received).
- Foreign-exchange rate history (reference data used for conversions).
- Monetary exchange transactions (settlements with amounts/fees), future.

## Models and Responsibilities

- `sync.Connection` and `sync.Exchange`
  - Purpose: integration/sync. `Connection` defines an external provider or partner; `Exchange` logs each exchange (direction, payload, mappings, responses).
  - Table: `connections`, `exchanges` (sync app).
  - Usage: Tracks exchanges for Items, Currencies, etc.; not FX rates.

- `accounts.Currency` and `accounts.ExchangeRate`
  - Purpose: currency catalog and time-windowed FX rates.
  - `Currency.connection` optionally points to `sync.Connection` to source updates.
  - `ExchangeRate` stores base→target, `rate`, `dt_start`/`dt_end`, and `connection` provenance.
  - Table: `acct_currencies`, `acct_exchange_rates` (accounts app).

- `accounts.Exchange` (planned future shape)
  - Purpose: monetary exchange/settlement transaction (amounts_in/out, fees, references, currencies).
  - Note: rate history lives in `ExchangeRate` and should not be conflated with transactions.

## Update and Logging Flows

- FX updates: `python manage.py update_currencies` creates/updates `accounts.ExchangeRate` records using provider behind `Currency.connection`.
- Sync logging: calls through `sync.Connection` create `sync.Exchange` rows for operational audit, independent of FX rates.

## Notes and Future Work

- Consider renaming `accounts.Exchange` to `ExchangeTransaction` to avoid ambiguity.
- Add admin/serializers for `ExchangeRate` and later for `Exchange` transactions.
- Introduce periodic tasks to refresh FX rates for active currencies.
