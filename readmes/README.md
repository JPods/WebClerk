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
| [Startup](getting-started/startup.md) | Daily dev startup |
| [Upgrade](getting-started/upgrade.md) | Version upgrade procedure |
| [Reset](getting-started/reset.md) | Database reset |
| [Config Unpack Training](getting-started/72-config-unpack-training.md) | Training video + reference |
| [App Bootstrap](getting-started/app-bootstrap.md) | First-run app bootstrap |

## Architecture

Core patterns that apply across all domains.

| Document | What it covers |
|----------|---------------|
| [WCAPI Gateway](architecture/03-wcapi-gateway.md) | The single policy gate |
| [WCAPI Usage](architecture/04-wcapi-usage.md) | GET patterns |
| [Model Registry](architecture/05-model-registry.md) | Auto-generated model reference |
| [API Conventions](architecture/06-api-conventions.md) | Naming and response conventions |
| [PJPV](architecture/pjpv-architecture.md) | Pydantic JSON Path Value — 4-layer discipline |
| [Data-Driven UI](architecture/data-driven-ui.md) | JSON-driven rendering, DynamicDetail |
| [JSON Envelope](architecture/json-envelope-policy.md) | JSON authoritative, scalars = indexes |
| [API Response Envelope](architecture/api-response-envelope.md) | Success/error response shape |
| [Layout Architecture](architecture/layout-architecture.md) | Settings -> Pydantic -> UI rendering |
| [Layout Schema](architecture/db-layout-schema.md) | Database layout schema detail |
| [Line Save Boundary](architecture/80-line-save-boundary.md) | Front end sends data, backend manages |
| [CodeMap](architecture/75-codemap.md) | Live architecture visualization |
| [Settings](architecture/settings.md) | Setting model fields and query patterns |
| [Setting Policy](architecture/setting-policy.md) | What gets a Setting |
| [Prefs Architecture](architecture/prefs-architecture.md) | Three-tier default resolution |
| [Refs Pattern](architecture/refs-pattern.md) | refs.links — denorm, policies, playbook |
| [Keyword Search](architecture/keyword-denormalization-and-search.md) | Keyword contract |
| [Pending Architecture](architecture/pending-architecture.md) | Pending records — model, flows, policy, offline |
| [Select Lists](architecture/selectlist-architecture.md) | Architecture, inheritance, management |
| [FK Discipline](architecture/fk-discipline.md) | FK vs BigInteger, naming, migration status |
| [Record Relationships](architecture/record-relationships.md) | FK + refs tiers, link lifecycle |
| [Currency Exchange](architecture/currency-exchange.md) | Exchange service + GL settlement |
| [Field Behaviors](architecture/field-behaviors.md) | BehaviorField widget reference |
| [Leaf Declarations](architecture/leaf-declarations.md) | JSONField type classification |
| [Competitive Position](architecture/competitive-position.md) | Honest market assessment |
| [Industry Comparison](architecture/industry-comparison.md) | Feature comparison |

## Transactions

The Big5 (Proposal, Order, Invoice, Purchase, Payment) + GL, ledger, pending records.

| Document | Flowchart |
|----------|-----------|
| [Master Reference](transactions/00_instructions.md) | |
| [Transaction Save](transactions/08-transaction-save.md) | |
| [Transaction Calculations](transactions/08-transaction-calculations.md) | |
| [Calc Status](transactions/09-transaction-calc-status.md) | |
| [Payment Lifecycle](transactions/payment-lifecycle.md) | [![Payment GL](flowcharts/thumbnails/wc3-payment-gl.jpg)](flowcharts/wc3-06-finance-a-payment-gl.enriched.svg) |
| [Payment Application](transactions/payment-application-design.md) | |
| [Ledger System](transactions/ledger-financial-system.md) | |
| [GL Accounts](transactions/gl-accounts-management.md) | |
| [Currency Exchange](transactions/currency-exchange.md) | |
| [Statement Harvester](transactions/statement-harvester.md) | [![Statement Sorter](flowcharts/thumbnails/wc3-statement-sorter.jpg)](flowcharts/wc3-06-finance-c-statement-sorter.enriched.svg) |
| [Pending Records](transactions/72-pending-records-intelligence.md) | [![Pending Records](flowcharts/thumbnails/wc3-pending-records.jpg)](flowcharts/wc3-06-finance-d-pending-records.enriched.svg) |
| [Pricing Architecture](transactions/pricing-architecture.md) | |
| [Transfer Flow](transactions/transaction_transfer.md) | |
| [Commission Operations](transactions/commission-operations.md) | |
| [Service Billing](transactions/service_billing.md) | |

## Contacts

People, organizations, roles, communications.

| Document | Flowchart |
|----------|-----------|
| [Email Operations](contacts/email-operations.md) | [![Contact](flowcharts/thumbnails/wc3-contact.jpg)](flowcharts/wc3-03-contacts-a-contact.enriched.svg) |
| [Email Validation](contacts/email-validation.md) | [![OrgBase](flowcharts/thumbnails/wc3-contact.jpg)](flowcharts/wc3-03-contacts-b-orgbase.enriched.svg) |
| [EDI Replaced by Sync](contacts/edi-replaced-by-sync.md) | |

## Products

Items, inventory, serial tracking, BOM.

| Document | Flowchart |
|----------|-----------|
| [Products & Item Support](products/71-products-item-support.md) | [![Products](flowcharts/thumbnails/wc3-products-item-support.jpg)](flowcharts/wc3-04-products-a-products-item-support.enriched.svg) |
| [Inventory](products/inventory.md) | [![Inventory](flowcharts/thumbnails/wc3-inventory-buckets.jpg)](flowcharts/wc3-04-products-b-inventory-buckets.enriched.svg) |
| [Delivery & Inventory Check](products/delivery-inventory.md) | [![Serial Tracking](flowcharts/thumbnails/wc3-serial-tracking.jpg)](flowcharts/wc3-04-products-c-serial-tracking.enriched.svg) |
| [Warehouse](products/warehouse.md) | |
| [Forecasting](products/forecasting.md) | |
| [Adaptive Clearing](products/adaptive-clearing-delay.md) | |

## Operations

DataBrowser, actions, projects, documents, reports, training.

| Document | Flowchart |
|----------|-----------|
| [DataBrowser Guide](operations/databrowser-guide.md) | |
| [DataBrowser Sovereignty](operations/databrowser-model-sovereignty.md) | |
| [Touch Model](operations/touch-model.md) | [![Action Touches](flowcharts/thumbnails/wc3-action-touches.jpg)](flowcharts/wc3-07-actions-c-action-touches.enriched.svg) |
| [Document Library](operations/document-library.md) | [![Documents](flowcharts/thumbnails/wc3-document-library.jpg)](flowcharts/wc3-08-content-a-document-library.enriched.svg) |
| [Report System](operations/report-system-overview.md) | |
| [Flight Simulators](operations/flight-simulators.md) | [![Flight Sim](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-10-infra-a-celery-pipeline.enriched.svg) |
| [Teaching Dashboards](operations/76-teaching-dashboards.md) | |
| [Agent Sprint](operations/84-agent-sprint-architecture.md) | |
| [Video Pages](operations/webclerk-video-pages.md) | |

## Alice

AI assistant — coaching, patterns, observations, LLM, daily stack.

| Document | Flowchart |
|----------|-----------|
| [AI Agreement](alice/00-ai-agreement.md) | [![Alice](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-12-alice-a-architecture.enriched.svg) |
| [Daily Stack](alice/85-alice-daily-stack.md) | |
| [Data Conversion](alice/70-data-conversion-pipeline.md) | [![Conversion](flowcharts/thumbnails/wc3-data-conversion-pipeline.jpg)](flowcharts/wc3-10-infra-b-data-conversion-pipeline.enriched.svg) |
| [Pattern Recognition](alice/pattern-recognition.md) | |
| [Learning](alice/learning.md) | |
| [Toolkit](alice/toolkit.md) | |
| [Escalation](alice/escalation.md) | |
| [Data Quality](alice/data-quality.md) | |
| [Dedup](alice/dedup.md) | |
| [Erosion Tracking](alice/erosion-tracking.md) | |

## Security

Authentication, authorization, upload quarantine, Athena.

| Document | Flowchart |
|----------|-----------|
| [Request Security](security/73-request-security-pipeline.md) | [![Security](flowcharts/thumbnails/wc3-request-security.jpg)](flowcharts/wc3-02-security-b-request-security.enriched.svg) |
| [Upload Auth](security/upload-auth-architecture.md) | [Upload Security](flowcharts/upload-security.svg) |
| [Contact Verification](security/contact-verification.md) | [![Sign In](flowcharts/thumbnails/wc3-signin-register.jpg)](flowcharts/wc3-02-security-a-signin-register.enriched.svg) |
| | [![Athena](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-02-security-c-athena.enriched.svg) |

## Sync

Connections, bundles, WCHQ, data exchange.

| Document | Flowchart |
|----------|-----------|
| [Collaborate](sync/collaborate-webclerk.md) | [![PO-SO Bundle](flowcharts/thumbnails/wc3-po-so-bundle.jpg)](flowcharts/wc3-05-sales-c-po-so-bundle.enriched.svg) |
| [Sync Test Protocol](sync/sync-test-protocol.md) | [![Refs Linkage](flowcharts/thumbnails/wc3-refs-linkage.jpg)](flowcharts/wc3-08-content-c-refs-linkage.enriched.svg) |
| [WCHQ IDA Convention](sync/wchq-ida-convention.md) | |
| [Community Contributions](sync/community-contributions.md) | |

## Infrastructure

Celery, deployment, backup, migrations.

| Document | Flowchart |
|----------|-----------|
| [Celery Architecture](infrastructure/celery-architecture.md) | [![Celery](flowcharts/thumbnails/wc3-celery-pipeline.jpg)](flowcharts/wc3-10-infra-a-celery-pipeline.enriched.svg) |
| [Primary Organization](infrastructure/primary-organization.md) | |
| [Maintenance](infrastructure/db-maintenance.md) | |
| [Production Deployment](infrastructure/production-deployment.md) | |
| [Production Cutover](infrastructure/production-cutover.md) | |
| [Read-Only Mode](infrastructure/read-only-mode.md) | |
| [Testing](infrastructure/testing.md) | |

## Master Flow

[![Master Flow](flowcharts/thumbnails/wc3-master-flow.jpg)](flowcharts/wc3-01-overview-a-master-flow.enriched.svg)

[Combined PDF — all flowcharts](flowcharts/wc3-all-flowcharts.pdf) | [Flowchart Index](flowcharts/INDEX.md)
