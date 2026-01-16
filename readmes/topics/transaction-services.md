# Transaction Services Architecture

> **Version**: 1.0  
> **Updated**: 2026-01-16  
> **Scope**: Single Point of Authority services for transaction behaviors  
> **Related**: [transaction-calculations.md](./transaction-calculations.md), [WC3 base_transaction_model.py](../../webClerk3/apps/transactions/models/base_transaction_model.py)

---

## Overview

All transaction types share common behaviors that must be implemented consistently. This document defines the **Single Point of Authority (SPA)** pattern for transaction services.

### Transaction Types

| Category | Models | Primary Value | Customer-Facing |
|----------|--------|---------------|-----------------|
| **Sales** | `sales_order`, `proposal`, `invoice` | Price | Yes |
| **Purchase** | `purchase_order`, `work_order` | Cost | No (internal/vendor) |

### Architecture Principle

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transaction Service Layer                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ LineItem │ │   Tax    │ │ Shipping │ │Commission│ │ Entity ││
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │ │ Service││
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘│
│       │            │            │            │           │      │
│       └────────────┴────────────┴────────────┴───────────┘      │
│                              │                                   │
│                    TransactionBaseModel                          │
└─────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────┴────┐           ┌─────┴─────┐          ┌─────┴─────┐
   │  Sales  │           │ Purchase  │          │   Work    │
   │  Order  │           │   Order   │          │   Order   │
   └─────────┘           └───────────┘          └───────────┘
```

---

## Core Services

### 1. Line Item Service

**Purpose**: Adding, updating, and managing transaction line items with deferred inventory tracking.

**Single Point of Authority**: 
- Backend: `apps/transactions/services/line_item_service.py`
- Backend Processor: `apps/transactions/services/pending_inventory_processor.py`
- Frontend: `src/apps/transactions/services/lineItemService.ts`

**Responsibilities**:
- Add items from catalog search
- Validate item availability
- Apply pricing rules (price levels, quantity breaks, promotions)
- Apply costing rules (vendor costs, landed cost)
- Calculate line extensions (qty × unit = extended)
- Handle bundles/kits component expansion
- Manage line-level discounts
- Track dirty state for optimized saves
- **Create pending inventory records for deferred Item updates**

**Pending Inventory Pattern**:

When line items change, instead of immediately updating the Item record (which could be locked), the service creates a `Pending` record. A background processor applies these changes when the Item is available.

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  LineItemService│     │    Pending       │     │  Item.record     │
│  add_item()     │────▶│    model_name=   │     │  .quantity{}     │
│  update_qty()   │     │    'item'        │────▶│  .on_sales_order │
│  delete_line()  │     │    dt_processed= │     │  .on_purchase_   │
└─────────────────┘     │    0             │     │  .on_work_order  │
                        └──────────────────┘     └──────────────────┘
                               ↑                        ↑
                               │  Celery Beat or        │
                               │  manage.py command     │
                        ┌──────┴──────────┐             │
                        │ process_line_   │─────────────┘
                        │ item_pending()  │  (batched updates)
                        └─────────────────┘
```

**Pending Record Purposes**:
| Purpose | When Created | Effect on Item |
|---------|--------------|----------------|
| `inventory_line_add` | New line added | Reserves qty in appropriate bucket |
| `inventory_qty_change` | Quantity updated | Delta (+/-) to reservation |
| `inventory_line_delete` | Line deleted | Releases reserved qty |
| `inventory_cost_change` | Cost updated | (Future: cost tracking) |

**Type Codes** (matches WebClerk2 DInventory):
| Code | Transaction Type | Affects |
|------|------------------|---------|
| `SO` | sales_order | `qty_on_so` |
| `PO` | purchase_order | `qty_on_po` |
| `WO` | work_order | `qty_on_wo` |
| `IV` | invoice | `qty_invoiced` (decreases on-hand) |
| `PP` | proposal | None (quotes don't affect inventory) |

**Sales vs Purchase Behavior**:
```typescript
interface LineItemServiceConfig {
  transactionType: 'sales' | 'purchase';
  useCost: boolean;  // false for sales, true for purchase
  priceField: 'price' | 'cost';
}

// Sales: price.unit drives calculations
// Purchase: cost.unit drives calculations
```

**API**:
```typescript
// Frontend
interface LineItemService {
  addItem(item: CatalogItem, quantity: number, config: LineItemServiceConfig): TransactionLine;
  updateQuantity(line: TransactionLine, quantity: number): TransactionLine;
  updatePrice(line: TransactionLine, unitPrice: number): TransactionLine;
  updateCost(line: TransactionLine, unitCost: number): TransactionLine;
  applyDiscount(line: TransactionLine, discountPct: number): TransactionLine;
  deleteLine(line: TransactionLine): TransactionLine; // soft delete
  duplicateLine(line: TransactionLine): TransactionLine;
}
```

```python
# Backend
class LineItemService:
    def __init__(self, create_pending: bool = True):
        """
        Args:
            create_pending: If True, creates Pending records for inventory changes.
                           Set False for imports/testing.
        """
    
    def add_item_to_transaction(self, transaction, item_id: int, quantity: Decimal, **kwargs) -> TransactionLine
    def add_item_from_search_result(self, transaction, search_result: dict, quantity: Decimal) -> TransactionLine
    def update_line(self, line, updates: dict) -> TransactionLine
    def update_quantity(self, line, quantity: Decimal) -> TransactionLine  # creates pending delta
    def update_price(self, line, unit_price: Decimal) -> TransactionLine
    def update_cost(self, line, unit_cost: Decimal) -> TransactionLine
    def apply_discount(self, line, discount_percent: float) -> TransactionLine
    def delete_line(self, line, soft: bool = True) -> None  # creates pending release
    def duplicate_line(self, line, quantity: Decimal = None) -> TransactionLine
    def calculate_line(self, line) -> TransactionLine
    def validate_item_change(self, line, new_item_id: int) -> None  # raises if invalid
```

**Pending Processor**:
```bash
# Process all pending line item changes
python manage.py process_line_item_pending --limit 200

# Dry run (no changes)
python manage.py process_line_item_pending --dry-run

# Process for specific item
python manage.py process_line_item_pending --item-id 123
```

```python
# Programmatic processing
from apps.transactions.services import process_line_item_pending, process_pending_for_item

# Process batch
summary = process_line_item_pending(limit=100, dry_run=False)

# Process single item
summary = process_pending_for_item(item_id=123)
```

**Pending Data Structure**:
```python
{
    'type_id': 'SO',                    # SO, PO, WO, IV
    'item_id': 123,
    'item_num': 'SKU-001',
    'doc_id': 'ORD-0001',
    'doc_pk': 456,
    'line_id': 789,
    'line_num': 1,
    
    # Quantity buckets (deltas, not absolutes)
    'qty_on_so': 5,                     # Sales order reservation
    'qty_on_po': 0,                     # Purchase order commitment
    'qty_on_wo': 0,                     # Work order reservation
    'qty_invoiced': 0,                  # Invoice reduces on-hand
    
    # Pricing snapshot
    'unit_cost': 10.00,
    'unit_price': 25.00,
    
    # Audit
    'reason': 'so line add',
    'take_action': 1,
    'transaction_type': 'sales_order',
}

---

### 2. Tax Service

**Purpose**: Communicate with tax databases and calculate taxes.

**Single Point of Authority**:
- Backend: `apps/transactions/services/tax_service.py`
- Frontend: `src/apps/transactions/services/taxService.ts`

**Responsibilities**:
- Look up tax jurisdiction from address
- Communicate with external tax engines (Avalara, TaxJar, Vertex)
- Calculate sales tax for sales transactions
- Calculate use tax for purchase transactions
- Handle tax exemptions and certificates
- Store tax breakdown by jurisdiction
- Support tax-inclusive pricing

**Configuration**:
```python
class TaxServiceConfig:
    engine: str  # 'avalara', 'taxjar', 'vertex', 'manual'
    api_key: str
    company_code: str
    commit_on_invoice: bool = True
    nexus_states: List[str]
```

**API**:
```typescript
// Frontend (calls backend)
interface TaxService {
  calculateTax(transaction: Transaction, lines: TransactionLine[]): Promise<TaxResult>;
  validateAddress(address: Address): Promise<AddressValidation>;
  checkExemption(customerId: number, state: string): Promise<ExemptionStatus>;
}

interface TaxResult {
  totalTax: number;
  taxableAmount: number;
  exemptAmount: number;
  jurisdictions: TaxJurisdiction[];
  lineItemTaxes: LineItemTax[];
}
```

```python
# Backend
class TaxService:
    def calculate_tax(self, transaction: Transaction) -> TaxResult
    def commit_tax(self, transaction: Transaction) -> str  # returns tax_service_id
    def void_tax(self, tax_service_id: str) -> None
    def get_tax_rates(self, address: dict) -> dict
    def validate_exemption(self, customer_id: int, certificate: str) -> bool
```

---

### 3. Shipping Service

**Purpose**: Communicate with shipping carriers and calculate shipping costs.

**Single Point of Authority**:
- Backend: `apps/transactions/services/shipping_service.py`
- Frontend: `src/apps/transactions/services/shippingService.ts`

**Responsibilities**:
- Get shipping rates from carriers (UPS, FedEx, USPS, LTL)
- Calculate dimensional weight
- Handle hazmat and special handling
- Generate shipping labels
- Track shipments
- Calculate landed cost for imports

**Configuration**:
```python
class ShippingServiceConfig:
    carriers: List[CarrierConfig]  # UPS, FedEx, etc.
    default_origin: Address
    dimensional_factor: int = 139  # DIM weight divisor
    handling_fee: Decimal = Decimal("0.00")
```

**API**:
```typescript
// Frontend (calls backend)
interface ShippingService {
  getRates(transaction: Transaction, destination: Address): Promise<ShippingRate[]>;
  selectRate(transaction: Transaction, rateId: string): Promise<void>;
  calculateWeight(lines: TransactionLine[]): WeightResult;
  validateAddress(address: Address): Promise<AddressValidation>;
}

interface ShippingRate {
  carrier: string;
  service: string;
  cost: number;
  estimatedDays: number;
  guaranteedDelivery?: string;
}
```

```python
# Backend
class ShippingService:
    def get_rates(self, transaction: Transaction, destination: dict) -> List[ShippingRate]
    def create_shipment(self, transaction: Transaction, rate_id: str) -> Shipment
    def get_label(self, shipment_id: int) -> bytes  # PDF label
    def track_shipment(self, tracking_number: str) -> TrackingResult
    def calculate_landed_cost(self, transaction: Transaction) -> LandedCost
```

---

### 4. Commission Service

**Purpose**: Calculate sales commissions and rep payouts.

**Single Point of Authority**:
- Backend: `apps/transactions/services/commission_service.py`
- Frontend: `src/apps/transactions/services/commissionService.ts`

**Responsibilities**:
- Calculate commissions based on rules (% of sale, % of margin, flat)
- Support split commissions (multiple reps)
- Handle commission adjustments
- Track commission status (pending, approved, paid)
- Generate commission reports

**Configuration**:
```python
class CommissionConfig:
    calculation_basis: str  # 'sale', 'margin', 'profit'
    default_rate: Decimal
    tier_rules: List[CommissionTier]
    split_rules: List[SplitRule]
    approval_required: bool = True
```

**API**:
```typescript
// Frontend (calls backend)
interface CommissionService {
  calculateCommission(transaction: Transaction): Promise<CommissionResult>;
  assignRep(transaction: Transaction, repId: number, splitPct?: number): Promise<void>;
  approveCommission(commissionId: number): Promise<void>;
}

interface CommissionResult {
  totalCommission: number;
  commissionRate: number;
  basis: 'sale' | 'margin' | 'profit';
  basisAmount: number;
  splits: CommissionSplit[];
}
```

```python
# Backend
class CommissionService:
    def calculate_commission(self, transaction: Transaction) -> CommissionResult
    def assign_rep(self, transaction: Transaction, rep_id: int, split_pct: Decimal = None) -> None
    def approve_commission(self, commission_id: int, approver_id: int) -> None
    def get_rep_commissions(self, rep_id: int, date_range: tuple) -> List[Commission]
```

---

### 5. Entity Assignment Service

**Purpose**: Assign and manage related entities (customer, vendor, manufacturer, rep, employee) with their contacts.

**Single Point of Authority**:
- Backend: `apps/transactions/services/entity_service.py`
- Frontend: `src/apps/transactions/services/entityService.ts`

**Responsibilities**:
- Assign customer/vendor/manufacturer to transaction
- Copy default addresses and contacts
- Apply entity-specific pricing/terms
- Validate entity status (active, credit hold, etc.)
- Manage entity-level preferences
- Link contacts to transactions

**Entity Types by Transaction**:
| Transaction Type | Primary Entity | Secondary Entities |
|-----------------|----------------|-------------------|
| Sales Order | Customer | Rep, Ship-To Contact |
| Proposal | Customer | Rep |
| Invoice | Customer | Rep |
| Purchase Order | Vendor | Buyer (Employee) |
| Work Order | Customer/Internal | Assigned Employee |

**API**:
```typescript
// Frontend (calls backend)
interface EntityService {
  assignCustomer(transaction: Transaction, customerId: number): Promise<EntityAssignment>;
  assignVendor(transaction: Transaction, vendorId: number): Promise<EntityAssignment>;
  assignRep(transaction: Transaction, repId: number): Promise<EntityAssignment>;
  assignContact(transaction: Transaction, contactId: number, role: ContactRole): Promise<void>;
  getEntityDefaults(entityType: string, entityId: number): Promise<EntityDefaults>;
}

interface EntityAssignment {
  entity: Entity;
  defaultAddress: Address;
  defaultContact: Contact;
  priceLevel: string;
  terms: string;
  creditStatus: CreditStatus;
}
```

```python
# Backend
class EntityService:
    def assign_customer(self, transaction: Transaction, customer_id: int) -> EntityAssignment
    def assign_vendor(self, transaction: Transaction, vendor_id: int) -> EntityAssignment
    def assign_rep(self, transaction: Transaction, rep_id: int) -> None
    def assign_contact(self, transaction: Transaction, contact_id: int, role: str) -> None
    def get_entity_defaults(self, entity_type: str, entity_id: int) -> dict
    def validate_entity(self, entity_type: str, entity_id: int) -> ValidationResult
```

---

### 6. Payment Service

**Purpose**: Process and apply payments to transactions.

**Single Point of Authority**:
- Backend: `apps/transactions/services/payment_service.py`
- Frontend: `src/apps/transactions/services/paymentService.ts`

**Responsibilities**:
- Apply payments to invoices
- Process credit cards (via payment gateway)
- Handle payment plans/installments
- Manage refunds and credits
- Track payment history
- Update balance due

**API**:
```typescript
interface PaymentService {
  applyPayment(invoiceId: number, payment: PaymentInput): Promise<PaymentResult>;
  processCard(invoiceId: number, cardInfo: CardInput): Promise<PaymentResult>;
  createRefund(paymentId: number, amount: number): Promise<RefundResult>;
  getPaymentHistory(invoiceId: number): Promise<Payment[]>;
}
```

---

### 7. Document Service

**Purpose**: Generate and manage transaction documents (PDFs, emails).

**Single Point of Authority**:
- Backend: `apps/transactions/services/document_service.py`
- Frontend: `src/apps/transactions/services/documentService.ts`

**Responsibilities**:
- Generate PDFs (quotes, orders, invoices, POs)
- Email documents to customers/vendors
- Store document history
- Support document templates
- Handle attachments

**API**:
```typescript
interface DocumentService {
  generatePdf(transactionId: number, template?: string): Promise<Blob>;
  emailDocument(transactionId: number, recipients: string[], options?: EmailOptions): Promise<void>;
  getDocumentHistory(transactionId: number): Promise<Document[]>;
  attachFile(transactionId: number, file: File): Promise<Attachment>;
}
```

---

### 8. Workflow Service

**Purpose**: Manage transaction status transitions and approvals.

**Single Point of Authority**:
- Backend: `apps/transactions/services/workflow_service.py`
- Frontend: `src/apps/transactions/services/workflowService.ts`

**Responsibilities**:
- Define valid status transitions
- Check approval requirements
- Execute status changes
- Trigger side effects (emails, inventory, etc.)
- Audit trail of status changes

**Status Transitions**:
```
planned → released → in_progress → complete
    ↓         ↓           ↓
   hold ←────────────────────
    ↓
 canceled
```

**API**:
```typescript
interface WorkflowService {
  getAvailableTransitions(transaction: Transaction): StatusTransition[];
  transition(transactionId: number, newStatus: string, reason?: string): Promise<void>;
  requestApproval(transactionId: number, approverId: number): Promise<ApprovalRequest>;
  approve(approvalId: number, decision: 'approve' | 'reject', notes?: string): Promise<void>;
}
```

---

### 9. Inventory Service

**Purpose**: Manage inventory allocation and availability for transactions.

**Single Point of Authority**:
- Backend: `apps/transactions/services/inventory_service.py`
- Frontend: `src/apps/transactions/services/inventoryService.ts`

**Responsibilities**:
- Check item availability
- Allocate/reserve inventory for orders
- Release allocations on cancel
- Update inventory on fulfillment
- Handle backorders
- Support multiple warehouses

**API**:
```typescript
interface InventoryService {
  checkAvailability(itemId: number, quantity: number, warehouseId?: number): Promise<Availability>;
  allocate(transactionId: number, lines: AllocationRequest[]): Promise<AllocationResult>;
  release(transactionId: number): Promise<void>;
  fulfill(transactionId: number, fulfillmentLines: FulfillmentLine[]): Promise<void>;
}
```

---

### 10. Pricing Service

**Purpose**: Determine correct pricing based on rules, levels, and promotions.

**Single Point of Authority**:
- Backend: `apps/transactions/services/pricing_service.py`
- Frontend: `src/apps/transactions/services/pricingService.ts`

**Responsibilities**:
- Look up price by price level
- Apply quantity break pricing
- Evaluate promotional pricing
- Handle contract pricing
- Support date-effective pricing
- Calculate customer-specific pricing

**API**:
```typescript
interface PricingService {
  getPrice(itemId: number, options: PricingOptions): Promise<PriceResult>;
  applyPromoCode(transaction: Transaction, code: string): Promise<PromoResult>;
  getPriceBreaks(itemId: number, priceLevel?: string): Promise<PriceBreak[]>;
}

interface PricingOptions {
  customerId?: number;
  priceLevel?: string;
  quantity?: number;
  effectiveDate?: string;
}
```

---

### 11. Credit Service

**Purpose**: Manage customer credit limits and holds.

**Single Point of Authority**:
- Backend: `apps/transactions/services/credit_service.py`
- Frontend: `src/apps/transactions/services/creditService.ts`

**Responsibilities**:
- Check credit availability
- Evaluate credit holds
- Calculate credit utilization
- Request credit limit increases
- Manage credit terms

**API**:
```typescript
interface CreditService {
  checkCredit(customerId: number, orderAmount: number): Promise<CreditCheck>;
  getCreditStatus(customerId: number): Promise<CreditStatus>;
  requestCreditIncrease(customerId: number, requestedLimit: number): Promise<void>;
  overrideHold(transactionId: number, approverNotes: string): Promise<void>;
}

interface CreditStatus {
  creditLimit: number;
  availableCredit: number;
  openBalance: number;
  creditHold: boolean;
  utilizationPct: number;
}
```

---

### 12. Calculation Service

**Purpose**: Centralized transaction math and totals calculation.

**Single Point of Authority**:
- Backend: `apps/transactions/services/calculation_service.py`
- Frontend: `src/apps/transactions/hooks/useHeaderCalculator.ts` + `useLineCalculator.ts`

**Responsibilities**:
- Calculate line extensions
- Aggregate header totals
- Apply discounts at line and header level
- Calculate margins (internal)
- Validate calculation accuracy
- Round consistently

**See**: [transaction-calculations.md](./transaction-calculations.md) for detailed implementation.

---

### 13. Linkage Service

**Purpose**: Manage links to external resources (PDFs, videos, images, documents) that attach to line items and flow through the transaction lifecycle.

**Single Point of Authority**:
- Backend: `apps/transactions/services/linkage_service.py`
- Frontend: `src/apps/transactions/services/linkageService.ts`

**Responsibilities**:
- Attach external resources to line items
- Support multiple link types (PDF, video, image, URL, document)
- Propagate links through transaction flow (proposal → sales order → invoice → PO → work order)
- Manage link visibility (customer-facing vs internal)
- Track link versions and history
- Support cloud storage (S3, Azure Blob, etc.)
- Handle link expiration and access control

**Link Types**:
```typescript
type LinkType = 
  | 'pdf'           // Product specs, drawings, certificates
  | 'video'         // Installation guides, demos
  | 'image'         // Product photos, diagrams
  | 'url'           // External resources
  | 'document'      // Word, Excel, etc.
  | 'cad'           // CAD files, 3D models
  | 'certificate';  // Compliance, safety certs
```

**Flow Propagation**:
```
Proposal (line links) 
    ↓ convert
Sales Order (links copied)
    ↓ invoice
Invoice (links copied)
    ↓ create PO for fulfillment
Purchase Order (links copied, internal only)
    ↓ work order
Work Order (links copied, internal only)
```

**API**:
```typescript
// Frontend
interface LinkageService {
  attachLink(lineId: number, link: LinkInput): Promise<LineLink>;
  removeLink(linkId: number): Promise<void>;
  getLinksForLine(lineId: number): Promise<LineLink[]>;
  getLinksForTransaction(transactionId: number): Promise<LineLink[]>;
  propagateLinks(sourceTransactionId: number, targetTransactionId: number): Promise<void>;
  updateLinkVisibility(linkId: number, visibility: 'customer' | 'internal'): Promise<void>;
}

interface LineLink {
  id: number;
  line_id: number;
  link_type: LinkType;
  url: string;
  title: string;
  description?: string;
  visibility: 'customer' | 'internal';
  file_size?: number;
  mime_type?: string;
  expires_at?: string;
  source_link_id?: number;  // ID of original link if propagated
}

interface LinkInput {
  link_type: LinkType;
  url: string;
  title: string;
  description?: string;
  visibility?: 'customer' | 'internal';
  file?: File;  // For upload
}
```

```python
# Backend
class LinkageService:
    def attach_link(self, line_id: int, link_data: dict) -> LineLink
    def remove_link(self, link_id: int) -> None
    def get_links_for_line(self, line_id: int) -> List[LineLink]
    def get_links_for_transaction(self, transaction_id: int) -> List[LineLink]
    def propagate_links(self, source_txn_id: int, target_txn_id: int, line_mapping: dict) -> List[LineLink]
    def upload_file(self, file: UploadedFile, link_type: str) -> str  # returns URL
    def generate_presigned_url(self, link_id: int, expires_in: int = 3600) -> str
```

---

### 14. Serial Service

**Purpose**: Track serialized inventory items through transactions, maintaining chain of custody from receipt through sale.

**Single Point of Authority**:
- Backend: `apps/transactions/services/serial_service.py`
- Frontend: `src/apps/transactions/services/serialService.ts`

**Responsibilities**:
- Assign serial numbers to line items
- Validate serial number uniqueness
- Track serial number history (receipt → inventory → sale)
- Support serial number formats and validation rules
- Handle serial number generation (auto or manual)
- Manage warranty registration
- Support batch/lot tracking alongside serials

**Serial Lifecycle**:
```
Purchase Order (serial TBD or pre-assigned)
    ↓ receive
Inventory (serial captured at receipt)
    ↓ allocate to order
Sales Order (serial allocated)
    ↓ ship
Invoice (serial confirmed shipped)
    ↓ warranty
Warranty Record (serial + customer linked)
```

**Serial States**:
```typescript
type SerialState = 
  | 'expected'      // On PO, not yet received
  | 'in_stock'      // Received, available
  | 'allocated'     // Reserved for an order
  | 'shipped'       // Shipped to customer
  | 'returned'      // RMA'd back
  | 'scrapped';     // Disposed
```

**API**:
```typescript
// Frontend
interface SerialService {
  assignSerial(lineId: number, serialNumber: string): Promise<SerialAssignment>;
  assignMultipleSerials(lineId: number, serialNumbers: string[]): Promise<SerialAssignment[]>;
  removeSerial(assignmentId: number): Promise<void>;
  getSerialsForLine(lineId: number): Promise<SerialAssignment[]>;
  getSerialsForTransaction(transactionId: number): Promise<SerialAssignment[]>;
  lookupSerial(serialNumber: string): Promise<SerialHistory>;
  validateSerial(serialNumber: string, itemId: number): Promise<SerialValidation>;
  generateSerials(itemId: number, quantity: number): Promise<string[]>;
  getAvailableSerials(itemId: number, warehouseId?: number): Promise<AvailableSerial[]>;
}

interface SerialAssignment {
  id: number;
  line_id: number;
  serial_number: string;
  state: SerialState;
  item_id: number;
  lot_number?: string;
  manufacture_date?: string;
  warranty_expires?: string;
  notes?: string;
}

interface SerialHistory {
  serial_number: string;
  item_id: number;
  item_code: string;
  item_description: string;
  current_state: SerialState;
  history: SerialEvent[];
  warranty?: WarrantyInfo;
}

interface SerialEvent {
  date: string;
  event_type: 'received' | 'allocated' | 'shipped' | 'returned' | 'transferred';
  transaction_type: string;
  transaction_id: number;
  transaction_ida: string;
  notes?: string;
}

interface AvailableSerial {
  serial_number: string;
  warehouse_id: number;
  warehouse_name: string;
  location?: string;
  received_date: string;
}
```

```python
# Backend
class SerialService:
    def assign_serial(self, line_id: int, serial_number: str) -> SerialAssignment
    def assign_multiple_serials(self, line_id: int, serial_numbers: List[str]) -> List[SerialAssignment]
    def remove_serial(self, assignment_id: int) -> None
    def get_serials_for_line(self, line_id: int) -> List[SerialAssignment]
    def get_serials_for_transaction(self, transaction_id: int) -> List[SerialAssignment]
    def lookup_serial(self, serial_number: str) -> SerialHistory
    def validate_serial(self, serial_number: str, item_id: int) -> SerialValidation
    def generate_serials(self, item_id: int, quantity: int) -> List[str]
    def get_available_serials(self, item_id: int, warehouse_id: int = None) -> List[AvailableSerial]
    def transfer_serial(self, serial_number: str, from_txn_id: int, to_txn_id: int) -> SerialAssignment
    def capture_serial_at_receipt(self, po_line_id: int, serial_numbers: List[str]) -> List[SerialAssignment]
```

---

## Frontend Service Registry

```typescript
// src/apps/transactions/services/index.ts

export { LineItemService } from './lineItemService';
export { TaxService } from './taxService';
export { ShippingService } from './shippingService';
export { CommissionService } from './commissionService';
export { EntityService } from './entityService';
export { PaymentService } from './paymentService';
export { DocumentService } from './documentService';
export { WorkflowService } from './workflowService';
export { InventoryService } from './inventoryService';
export { PricingService } from './pricingService';
export { CreditService } from './creditService';
export { CalculationService } from './calculationService';
export { LinkageService } from './linkageService';
export { SerialService } from './serialService';

// Service factory with configuration
export function createTransactionServices(config: TransactionServiceConfig) {
  return {
    lineItem: new LineItemService(config),
    tax: new TaxService(config),
    shipping: new ShippingService(config),
    commission: new CommissionService(config),
    entity: new EntityService(config),
    payment: new PaymentService(config),
    document: new DocumentService(config),
    workflow: new WorkflowService(config),
    inventory: new InventoryService(config),
    pricing: new PricingService(config),
    credit: new CreditService(config),
    calculation: new CalculationService(config),
    linkage: new LinkageService(config),
    serial: new SerialService(config),
  };
}
```

---

## Backend Service Registry

```python
# apps/transactions/services/__init__.py

from .line_item_service import LineItemService
from .tax_service import TaxService
from .shipping_service import ShippingService
from .commission_service import CommissionService
from .entity_service import EntityService
from .payment_service import PaymentService
from .document_service import DocumentService
from .workflow_service import WorkflowService
from .inventory_service import InventoryService
from .pricing_service import PricingService
from .credit_service import CreditService
from .calculation_service import CalculationService
from .linkage_service import LinkageService
from .serial_service import SerialService

__all__ = [
    'LineItemService',
    'TaxService',
    'ShippingService',
    'CommissionService',
    'EntityService',
    'PaymentService',
    'DocumentService',
    'WorkflowService',
    'InventoryService',
    'PricingService',
    'CreditService',
    'CalculationService',
    'LinkageService',
    'SerialService',
]
```

---

## Usage Pattern

### In Transaction Detail Components

```typescript
// src/apps/transactions/models/sales_order/pages/SalesOrderDetail.tsx

import { createTransactionServices } from '../../../services';

const SalesOrderDetail: React.FC = () => {
  const services = useMemo(() => createTransactionServices({
    transactionType: 'sales',
    useCost: false,
  }), []);
  
  // Adding a line item
  const handleAddItem = (item: CatalogItem, quantity: number) => {
    const newLine = services.lineItem.addItem(item, quantity, {
      transactionType: 'sales',
      useCost: false,
      priceField: 'price',
    });
    setLines(prev => [...prev, newLine]);
  };
  
  // Assigning a customer
  const handleAssignCustomer = async (customerId: number) => {
    const assignment = await services.entity.assignCustomer(transaction, customerId);
    setTransaction(prev => ({
      ...prev,
      customer_id: customerId,
      price_level: assignment.priceLevel,
      terms: assignment.terms,
    }));
  };
  
  // Calculate tax
  const handleCalculateTax = async () => {
    const taxResult = await services.tax.calculateTax(transaction, lines);
    setTransaction(prev => ({
      ...prev,
      totals: { ...prev.totals, tax: taxResult.totalTax },
    }));
  };
};
```

### In Purchase Order Detail

```typescript
// src/apps/transactions/models/purchase_order/pages/PurchaseOrderDetail.tsx

const PurchaseOrderDetail: React.FC = () => {
  const services = useMemo(() => createTransactionServices({
    transactionType: 'purchase',
    useCost: true,
  }), []);
  
  // Adding a line item - uses cost instead of price
  const handleAddItem = (item: CatalogItem, quantity: number) => {
    const newLine = services.lineItem.addItem(item, quantity, {
      transactionType: 'purchase',
      useCost: true,
      priceField: 'cost',
    });
    setLines(prev => [...prev, newLine]);
  };
  
  // Assigning a vendor
  const handleAssignVendor = async (vendorId: number) => {
    const assignment = await services.entity.assignVendor(transaction, vendorId);
    setTransaction(prev => ({
      ...prev,
      vendor_id: vendorId,
      terms: assignment.terms,
    }));
  };
};
```

---

## Service Implementation Guidelines

### 1. Single Responsibility
Each service handles ONE domain of functionality.

### 2. Consistent Interface
All services follow the same patterns:
- Async methods return Promises
- Validation before mutation
- Error handling with typed exceptions

### 3. Transaction Type Awareness
Services accept configuration for sales vs purchase behavior.

### 4. Backend Authority
Frontend services call backend APIs - backend is the source of truth.

### 5. Optimistic Updates
Frontend can show optimistic results, but must sync with backend on save.

---

## File Structure

```
React2025/src/apps/transactions/
├── services/
│   ├── index.ts                    # Service registry and factory
│   ├── lineItemService.ts          # Line item management
│   ├── taxService.ts               # Tax calculations
│   ├── shippingService.ts          # Shipping rates/labels
│   ├── commissionService.ts        # Commission calculations
│   ├── entityService.ts            # Customer/vendor assignment
│   ├── paymentService.ts           # Payment processing
│   ├── documentService.ts          # PDF/email generation
│   ├── workflowService.ts          # Status transitions
│   ├── inventoryService.ts         # Inventory allocation
│   ├── pricingService.ts           # Price lookups
│   ├── creditService.ts            # Credit management
│   ├── calculationService.ts       # Math/totals
│   ├── linkageService.ts           # External resource links
│   └── serialService.ts            # Serialized item tracking
├── hooks/
│   ├── useTransactionServices.ts   # Hook to access services
│   ├── useLineCalculator.ts        # Line math hook
│   └── useHeaderCalculator.ts      # Header totals hook
└── types/
    └── serviceTypes.ts             # Service type definitions

webClerk3/apps/transactions/
├── services/
│   ├── __init__.py                 # Service registry
│   ├── line_item_service.py
│   ├── tax_service.py
│   ├── shipping_service.py
│   ├── commission_service.py
│   ├── entity_service.py
│   ├── payment_service.py
│   ├── document_service.py
│   ├── workflow_service.py
│   ├── inventory_service.py
│   ├── pricing_service.py
│   ├── credit_service.py
│   ├── calculation_service.py
│   ├── linkage_service.py
│   └── serial_service.py
└── views/
    └── transaction_service_views.py  # API endpoints for services
```

---

## Summary Table

| # | Service | Purpose | Sales | Purchase |
|---|---------|---------|-------|----------|
| 1 | Line Item | Add/manage line items | Price-based | Cost-based |
| 2 | Tax | Tax calculation | Sales tax | Use tax |
| 3 | Shipping | Shipping rates/labels | Customer shipping | Freight in |
| 4 | Commission | Rep commissions | Yes | No |
| 5 | Entity | Assign customer/vendor | Customer, Rep | Vendor, Buyer |
| 6 | Payment | Process payments | Yes (invoices) | Yes (AP) |
| 7 | Document | PDF/email generation | Yes | Yes |
| 8 | Workflow | Status transitions | Yes | Yes |
| 9 | Inventory | Allocation/fulfillment | Allocate out | Receive in |
| 10 | Pricing | Price lookups | Customer pricing | Vendor costs |
| 11 | Credit | Credit limits | Customer credit | Vendor terms |
| 12 | Calculation | Math/totals | Yes | Yes |
| 13 | Linkage | External resource links | Yes (customer-facing) | Yes (internal) |
| 14 | Serial | Serialized item tracking | Ship serials | Receive serials |

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-16 | 1.0 | Initial document - 12 core services defined |
| 2026-01-16 | 1.1 | Added Linkage Service (#13) and Serial Service (#14) |
