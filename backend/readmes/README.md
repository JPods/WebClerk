# WebClerk Documentation

System documentation organized by domain. Each folder tells the full story —
model, service, API, UI component, panel behavior. No backend/frontend split.

## Getting Started

| Document | What it covers |
|----------|---------------|
| [Architecture Overview](getting-started/01-architecture-overview.md) | Models, API patterns, key principles |
| [Dev Setup](getting-started/02-dev-setup.md) | Local development environment |
| [Environment](getting-started/env-setup.md) | .env configuration |
| [Bootstrap](getting-started/settings-bootstrap.md) | First-run settings import |
| [Onboarding](getting-started/onboarding.md) | New user setup |

## Architecture

Core patterns that apply across all domains.

| Document | What it covers |
|----------|---------------|
| [WCAPI Gateway](architecture/03-wcapi-gateway.md) | The single policy gate |
| [PJPV](architecture/pjpv-architecture.md) | Pydantic JSON Path Value — 4-layer discipline |
| [Data-Driven UI](architecture/data-driven-ui.md) | JSON-driven rendering, DynamicDetail |
| [JSON Envelope](architecture/json-envelope-policy.md) | JSON authoritative, scalars = indexes |
| [Layout Architecture](architecture/layout-architecture.md) | Settings → Pydantic → UI rendering |
| [Line Save Boundary](architecture/80-line-save-boundary.md) | Front end sends data, backend manages |
| [CodeMap](architecture/75-codemap.md) | Live architecture visualization |

## Transactions

The Big5 (Proposal, Order, Invoice, Purchase, Payment) + GL, ledger, pending records.

| Document | Flowchart |
|----------|-----------|
| [Transaction Save](transactions/08-transaction-save.md) | |
| [Transaction Calculations](transactions/08-transaction-calculations.md) | |
| [Payment Application](transactions/payment-application-design.md) | [![Payment GL](flowcharts/thumbnails/wc3-payment-gl.jpg)](flowcharts/wc3-06-finance-a-payment-gl.enriched.svg) |
| [Ledger System](transactions/ledger-financial-system.md) | |
| [Statement Harvester](transactions/statement-harvester.md) | [![Statement Sorter](flowcharts/thumbnails/wc3-statement-sorter.jpg)](flowcharts/wc3-06-finance-c-statement-sorter.enriched.svg) |
| [Pending Records](transactions/72-pending-records-intelligence.md) | [![Pending Records](flowcharts/thumbnails/wc3-pending-records.jpg)](flowcharts/wc3-06-finance-d-pending-records.enriched.svg) |

## Contacts

People, organizations, roles, communications.

| Flowchart | |
|-----------|--|
| [![Contact](flowcharts/thumbnails/wc3-contact.jpg)](flowcharts/wc3-03-contacts-a-contact.enriched.svg) | [![OrgBase](flowcharts/thumbnails/wc3-contact.jpg)](flowcharts/wc3-03-contacts-b-orgbase.enriched.svg) |

## Products

Items, inventory, serial tracking, BOM.

| Document | Flowchart |
|----------|-----------|
| [Products & Item Support](products/71-products-item-support.md) | [![Products](flowcharts/thumbnails/wc3-products-item-support.jpg)](flowcharts/wc3-04-products-a-products-item-support.enriched.svg) |
| [Inventory Flow](products/inventory_flow_testing.md) | [![Inventory](flowcharts/thumbnails/wc3-inventory-buckets.jpg)](flowcharts/wc3-04-products-b-inventory-buckets.enriched.svg) |
| | [![Serial Tracking](flowcharts/thumbnails/wc3-serial-tracking.jpg)](flowcharts/wc3-04-products-c-serial-tracking.enriched.svg) |

## Operations

DataBrowser, actions, projects, documents, reports, training.

| Document | Flowchart |
|----------|-----------|
| [DataBrowser Guide](operations/databrowser-guide.md) | |
| [Touch Model](operations/68-touch-model.md) | [![Action Touches](flowcharts/thumbnails/wc3-action-touches.jpg)](flowcharts/wc3-07-actions-c-action-touches.enriched.svg) |
| [Document Library](operations/68-document-library.md) | [![Documents](flowcharts/thumbnails/wc3-document-library.jpg)](flowcharts/wc3-08-content-a-document-library.enriched.svg) |
| [Flight Simulator](operations/77-flight-simulator-plan.md) | [![Flight Sim](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-10-infra-a-celery-pipeline.enriched.svg) |

## Alice

AI assistant — coaching, patterns, observations, LLM, daily stack.

| Document | Flowchart |
|----------|-----------|
| [AI Agreement](alice/00-ai-agreement.md) | [![Alice](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-12-alice-a-architecture.enriched.svg) |
| [Daily Stack](alice/85-alice-daily-stack.md) | |
| [Data Conversion](alice/70-data-conversion-pipeline.md) | [![Conversion](flowcharts/thumbnails/wc3-data-conversion-pipeline.jpg)](flowcharts/wc3-10-infra-b-data-conversion-pipeline.enriched.svg) |

## Security

Authentication, authorization, upload quarantine, Athena.

| Document | Flowchart |
|----------|-----------|
| [Request Security](security/73-request-security-pipeline.md) | [![Security](flowcharts/thumbnails/wc3-request-security.jpg)](flowcharts/wc3-02-security-b-request-security.enriched.svg) |
| [Upload Auth](security/upload-auth-architecture.md) | [Upload Security](flowcharts/upload-security.svg) |
| | [![Sign In](flowcharts/thumbnails/wc3-signin-register.jpg)](flowcharts/wc3-02-security-a-signin-register.enriched.svg) |
| | [![Athena](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-02-security-c-athena.enriched.svg) |

## Sync

Connections, bundles, WCHQ, data exchange.

| Flowchart | |
|-----------|--|
| [![PO-SO Bundle](flowcharts/thumbnails/wc3-po-so-bundle.jpg)](flowcharts/wc3-05-sales-c-po-so-bundle.enriched.svg) | [![Refs Linkage](flowcharts/thumbnails/wc3-refs-linkage.jpg)](flowcharts/wc3-08-content-c-refs-linkage.enriched.svg) |

## Infrastructure

Celery, deployment, backup, migrations.

| Document | Flowchart |
|----------|-----------|
| [Celery Architecture](infrastructure/69-celery-architecture.md) | [![Celery](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-10-infra-a-celery-pipeline.enriched.svg) |
| [Maintenance](infrastructure/maintenance.md) | |

## Master Flow

[![Master Flow](flowcharts/thumbnails/wc3-master-flow.jpg)](flowcharts/wc3-01-overview-a-master-flow.enriched.svg)

[Combined PDF — all flowcharts](flowcharts/wc3-all-flowcharts.pdf) | [Flowchart Index](flowcharts/INDEX.md)
