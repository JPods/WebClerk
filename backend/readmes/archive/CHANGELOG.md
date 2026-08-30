# Changelog


<!-- TOC START -->

## Table of Contents

- [Changelog](#changelog)
  - [Table of Contents](#table-of-contents)
  - [[Unreleased]](#unreleased)
  - [[0.1.0] - 2025-09-04](#010-2025-09-04)
    - [Added](#added)
    - [Changed](#changed)
    - [Fixed](#fixed)
    - [Documentation](#documentation)
    - [Tests](#tests)
    - [Internal / Future (Planned)](#internal-future-planned)
  - [Historical Context](#historical-context)

<!-- TOC END -->

All notable changes to this project will be documented in this file.

The format loosely follows Keep a Changelog, and versioning will begin once a formal release tag is created.

## [Unreleased]

_No changes yet._

## [0.1.0] - 2025-09-04

### Added

- Inventory metrics JSON endpoint (`inventory/metrics/`) exposing:
  - Reservation stats (counts, quantities, active, earliest expiration)
  - Reservation TTL histogram buckets
  - Pending adjustment stats (counts, conflict/insufficient breakdown)
  - Stack aggregates & protection percentage
  - Processor run info: latest global & per-stack runs, duration buckets
  - Cumulative processor run aggregates (runs, attempted, applied)
- Prometheus plaintext metrics endpoint (`inventory/metrics/prometheus`) with:
  - Gauges for high-level inventory and reservation metrics
  - Histogram-style bucket export for reservation TTL and processor run duration
  - Cumulative run gauges (global + stack) and attempt/apply counters
  - Auth requirement toggle via `INVENTORY_PROMETHEUS_REQUIRE_AUTH` and `?auth=0` bypass
- `InventoryAdjustmentProcessorRun` model for logging processor executions.
- Automatic logging for global and per-stack adjustment processor executions.
- OpenAPI example enhancements showing extended metrics & processor run structures.
- Grafana dashboard JSON and alert rule examples (documentation section) for operational monitoring.

### Changed

- `summarize_inventory_metrics` service expanded to compute TTL buckets, duration buckets, and cumulative run aggregates.
- Prometheus view refined for label formatting consistency and inclusion of cumulative metrics.

### Fixed

- Corrected premature return / indentation issues in adjustment processor ensuring run logs persist.
- Resolved Prometheus label formatting for histogram buckets.
- Ensured README markdown formatting (blank lines, fenced code blocks) passes basic lint expectations.

### Documentation

- `readmes/inventory.md` updated with: Metrics schema, Prometheus endpoint usage, sample outputs, dashboard & alert guidance.
- Added explanatory sections for histogram buckets, cumulative metrics, and processor run data.

### Tests

- Added tests for processor run logging (global & stack).
- Added tests validating presence & structure of processor run metrics in JSON and Prometheus endpoints.
- All existing tests passing (reference: 155 passed, 1 skipped at time of change).

### Internal / Future (Planned)

- Potential: per-item/warehouse labeled metrics (cardinality evaluation needed).
- Persisted multi-run duration histograms (time series) beyond last-run bucketing.
- Reservation queue latency metrics.
- Recording rules & scrape config automation templates.
- Movement ledger integration metrics & negative inventory prevention alerts.
- Reusable OpenAPI components for processor run schema.

---

## Historical Context

Prior functionality focused on inventory reservation & adjustment processing without rich operational metrics. This release introduces comprehensive observability (JSON + Prometheus) and foundational run logging for future analytical expansion.

