# Transaction Flow Calculation Plan

## Objective

Identify useful business logic in WebClerk2 and create a plan to implement in WebClerk3 and React2025. Focus on Orders, include Proposals, Invoices, POs. Step by step, table by table. Include schema alignments, jsonb recommendations, function summaries, additional recommendations. Stub notices for commissions and special discounts. Ensure the plan is comprehensive and actionable.

## Overview

This plan salvages practical business logic from WebClerk2 for transaction management in WebClerk3, with frontend implementation in React2025. The focus is on the core transaction flow: Proposals → Sales Orders → Purchase Orders → Invoices → Payments. Each table is analyzed step-by-step, incorporating schema alignments from WebClerk2 to WebClerk3, recommendations for jsonb field usage (.refs, .prefs, .metadata), summaries of relevant WebClerk2 functions, and additional implementation recommendations. Commissions and special discounts are stubbed for future implementation.

## React2025 Scope

React2025 is limited to features in WC_Core.4dm (basic order management, payments, reservations, proposals) and should expand with modern transaction processing (real-time calculations, multi-currency, audit trails, API interactions) while avoiding non-transaction features.

## Schema Alignments

The following alignments map WebClerk2 tables to WebClerk3 models:

- Proposal and ProposalLine → proposal and proposal_line
- Order and OrderLine → sales_order and sales_order_line
- PO and POLine → purchase_order and purchase_order_line
- Invoice and InvoiceLine → invoice and invoice_line
- Payment → Payment
- QA → question_answer
- PurchaseJournal, SalesJournal, CashJournal → gl_journal
- DCash, DInventory → pending (via `apps.core.models.Pending`)

## DInventory → Pending Implementation

**Status**: ✅ Implemented (2026-01-16)

The WebClerk2 `DInventory` table functionality has been implemented in WebClerk3 using the `Pending` model and the `LineItemService`. When transaction lines are added, modified, or deleted, pending records are created for deferred inventory updates.

**Key Components**:
- `apps/transactions/services/line_item_service.py` - Creates pending records on line changes
- `apps/transactions/services/pending_inventory_processor.py` - Processes pending records
- `apps/transactions/management/commands/process_line_item_pending.py` - Management command

**Type Code Mapping**:
| WebClerk2 | WebClerk3 | Transaction Type |
|-----------|-----------|------------------|
| `SO` | `SO` | Sales Order |
| `PO` | `PO` | Purchase Order |
| `WO` | `WO` | Work Order |
| `IV` | `IV` | Invoice |
| (n/a) | `PP` | Proposal (no inventory) |

**Usage**:
```python
# LineItemService automatically creates pending records
from apps.transactions.services import LineItemService
service = LineItemService(create_pending=True)  # default
line = service.add_item_to_transaction(order, item_id=123, quantity=5)

# Process pending records
python manage.py process_line_item_pending --limit 200
```

See: [transaction-services.md](../../../React2025/readmes/topics/transaction-services.md) for full API documentation.

## Jsonb Recommendations

WebClerk3 models include jsonb fields: .refs, .prefs, and .metadata (except in pending). Recommendations for transaction needs:

- **.refs**: Store lineage and relationship data, e.g., proposal_id in sales_order, order_id in invoice, vendor groupings in purchase_order.
- **.prefs**: User or system preferences, e.g., default tax rates, currency settings, or workflow preferences.
- **.metadata**: Additional calculated or custom data, e.g., margin percentages, extended totals, notes, or flags for special processing.
- For pricing: Use cost and sell jsonb fields for structured price data (e.g., {"base": 100, "tax": 10}).
- For finance: Store finance-related calculations in finance jsonb (e.g., {"commission_rate": 0.05}).
- Ensure jsonb fields are indexed for performance on frequently queried keys.

## Table-by-Table Analysis

### Proposals

**Step 1: Schema Alignment**  
WebClerk2: Proposal, ProposalLine  
WebClerk3: proposal, proposal_line  

**Step 2: Jsonb Recommendations**  

- .refs: Store customer_id, vendor_id, and related contact references.  
- .prefs: Default proposal settings, e.g., {"auto_accept_threshold": 1000}.  
- .metadata: Custom fields like proposal_version, approval_notes.  
- cost/sell: Pricing structures for estimates.  

**Step 3: Function Summaries**  

- NxPvProposals: Loads proposal records, including header and line data. Useful for initializing proposal views in React2025.  
- (Additional functions: Similar to order functions for line management, e.g., listItemsFill for PpLnAdd.)  

**Step 4: Additional Recommendations**  

- Implement proposal-to-order conversion logic based on createOrderProp (initialize sales_order from proposal).  
- Calculate totals automatically using proposal_totals service.  
- Validate proposal completeness before conversion (e.g., all lines have pricing).  
- In React2025, use WC_apiServer functions for proposal CRUD and conversion endpoints.

### Sales Orders

**Step 1: Schema Alignment**  
WebClerk2: Order, OrderLine  
WebClerk3: sales_order, sales_order_line  

**Step 2: Jsonb Recommendations**  

- .refs: Link to proposal_id, customer denormalized data, vendor references.  
- .prefs: Order preferences, e.g., {"shipping_method": "express"}.  
- .metadata: Calculated fields like total_margin, fulfillment_status.  
- cost/sell: Structured pricing per line.  

**Step 3: Function Summaries**  

- NxPvOrders: Loads order records.  
- createOrderProp: Initializes sales_order from proposal.  
- OrdersCreateNew: Initializes new sales_order.  
- LoadCustOrder: Denormalizes customer data into order; leverage related records in WebClerk3.  
- OrdLnRays: Manages line data in arrays.  
- Ord2InvComm: Invoices for commissions.  
- Ord2InvProduct: Invoices for products.  
- Ord2MfgOrd: Creates manufacturing orders.  
- Ord2POByVendor: Creates POs grouped by vendor.  
- rptOrd2Inv: Converts multiple orders to invoices.  
- Order2POForceVendor: Forces lines into PO for specific vendor.  
- listItemsFill: Implements OrdLnAdd.  
- OrdLnExtend: Extends values on line changes (e.g., recalculate totals).  
- CloneRecord: Creates work orders from sales orders.  

**Step 4: Additional Recommendations**  

- Denormalize customer data for performance, but use foreign keys for integrity.  
- Manage lines as arrays/lists in services.  
- Implement automatic extensions on line updates.  
- Support multiple conversions (to invoices, POs, manufacturing).  
- In React2025, integrate with WC_apiServer for order loading and transfers.

### Purchase Orders

**Step 1: Schema Alignment**  
WebClerk2: PO, POLine  
WebClerk3: purchase_order, purchase_order_line  

**Step 2: Jsonb Recommendations**  

- .refs: Link to sales_order_id, vendor_id, grouped by vendor logic.  
- .prefs: Procurement preferences, e.g., {"lead_time_days": 7}.  
- .metadata: Vendor-specific notes, expected_delivery.  
- cost/sell: Vendor pricing structures.  

**Step 3: Function Summaries**  

- NxPvPOs: Loads PO records.  
- (Similar to orders: POLine management via listItemsFill for POLnAdd, line extensions.)  
- Ord2POByVendor: Creates POs from sales orders by vendor.  
- Order2POForceVendor: Forces vendor-specific POs.  

**Step 4: Additional Recommendations**  

- Automate PO creation from sales orders based on vendor requirements.  
- Track procurement status and integrate with inventory receiving.  
- Use refs for multi-vendor grouping.  
- In React2025, provide PO creation wizards from order views.

### Invoices

**Step 1: Schema Alignment**  
WebClerk2: Invoice, InvoiceLine  
WebClerk3: invoice, invoice_line  

**Step 2: Jsonb Recommendations**  

- .refs: Link to order_id, payment references.  
- .prefs: Billing preferences, e.g., {"due_days": 30}.  
- .metadata: Invoice totals, overdue flags, payment history.  
- cost/sell: Billed amounts with tax breakdowns.  

**Step 3: Function Summaries**  

- NxPvInvoices: Loads invoice records.  
- NxPvInvAccess: Additional access details.  
- IvcLnDetails: Line item details dialog.  
- IvcLnLoadRec: Loads line records.  
- IvcLnFillRays: Manages line data in arrays.  
- IvcLnExtend: Calculates invoice lines (e.g., extended prices).  
- Ord2InvComm: Invoices commissions separately.  
- Ord2InvProduct: Invoices products.  
- rptOrd2Inv: Bulk order-to-invoice conversion.  

**Step 4: Additional Recommendations**  

- Separate logic for commission vs. product invoicing.  
- Implement line extensions for automatic calculations.  
- Integrate with payment application.  
- In React2025, use WC_apiServer for invoice generation and viewing.

### Payments

**Step 1: Schema Alignment**  
WebClerk2: Payment  
WebClerk3: Payment  

**Step 2: Jsonb Recommendations**  

- .refs: Link to invoice_id, gateway references.  
- .prefs: Payment method preferences.  
- .metadata: Reconciliation data, transaction IDs.  
- finance: Payment amounts and fees.  

**Step 3: Function Summaries**  

- (Limited specific functions; integrate with invoice and gateway logic.)  

**Step 4: Additional Recommendations**  

- Implement payment application to invoices.  
- Support gateway integrations (Stripe/PayPal).  
- Track payment status and balances.  
- In React2025, provide payment processing UI.

## Commissions and Special Discounts

**Stub Notice**: Commissions and special discounts will be implemented in a future phase. For now, store commission-related data (e.g., rates, calculations) in the finance jsonb field or metadata. Special discounts can be handled via discount_amount in line models or stored in sell jsonb as {"discount": 10}. Avoid complex calculations until business rules are finalized. Flag records requiring commission processing in metadata.

## Additional Recommendations

- Leverage WC_apiServer functions from WebClerk2 for React2025 API endpoints.  
- Implement totals calculations using existing services (e.g., *_totals.py).  
- Ensure status workflows match WebClerk2 patterns (planned → released → complete).  
- Add validation services for conversions (e.g., proposal to order).  
- Integrate inventory updates on transfers (reserve on order, reduce on invoice).  
- Test step-by-step: Start with proposal/order conversions, then expand to full flow.  
- Document any schema discrepancies or missing functions for further analysis.

## Migration Steps

There is zero legacy data to migrate. Once WebClerk3 is functioning, if data migration is needed, build a tool for that.
