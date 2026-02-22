# Model Hierarchy

> Auto-generated overview of the CoreModel → BaseModel mixin chain.

---

## Two-Tier Pattern

| Base | Use Case | JSON Envelopes |
|------|----------|----------------|
| `CoreModel` | Lightweight entities (Pending, Log) | No |
| `BaseModel` | Full entities (Contact, Order, Item) | Yes (metadata, refs, prefs, actions, comments) |
| `TransactionBaseModel` | Transactions (Order, Invoice) | Yes + totals, status, flow fields |

## BaseModel Composition

```
BaseModel
  ├── CoreModel          (id, uuid, ida, dt_created, dt_modified, version, is_active, security_level)
  ├── ActionsMixin        (actions JSONField — required, status, who, when, what)
  ├── MetadataMixin       (metadata JSONField — history, health, flags, images, flow, source)
  ├── RefsMixin           (refs JSONField — keywords, tags, links, parents, depends_on, categories)
  ├── KeywordsMixin       (keywords TextField — full-text search)
  ├── PrefsMixin          (prefs JSONField — user-defined settings)
  ├── CommentsMixin       (comments JSONField — public, process, partner, notes[])
  ├── HealthMixin         (health_rating IntegerField)
  ├── LifecycleMixin      (is_deleted, is_archived + soft_delete/restore/archive)
  ├── UniversalDictMixin  (to_universal_dict() serialization contract)
  └── AtomicJSONMixin     (atomic_json_set, atomic_list_append for partial JSONB updates)
```

## Models by Base Class

### CoreModel (lightweight)

- `core.Pending`

### BaseModel (full)

- `core.APILog`
- `core.Action`
- `communications.Address`
- `accounts.Audit`
- `core.AuditLog`
- `products.BillOfMaterial`
- `sync.Bundle`
- `products.Catalog`
- `products.CatalogLine`
- `sync.Connection`
- `core.Contact`
- `accounts.Currency`
- `orgs.Customer`
- `products.DeliveryLine`
- `products.DeliveryVisit`
- `docs.Document`
- `communications.Domain`
- `communications.Email`
- `orgs.Employee`
- `accounts.ExchangeRate`
- `accounts.ExchangeTransaction`
- `accounts.GlAccount`
- `accounts.GlJournal`
- `products.InventoryAdjustmentProcessorRun`
- `products.InventoryCheck`
- `products.InventoryCheckLine`
- `products.InventoryLayer`
- `products.InventoryMetricsSnapshot`
- `products.InventoryMovement`
- `transactions.InvoiceLine`
- `products.Item`
- `products.ItemUsage`
- `products.ItemXRef`
- `accounts.Ledger`
- `docs.LinkageEntry`
- `orgs.Manufacturer`
- `core.Notification`
- `transactions.OrderLine`
- `orgs.OrgBase`
- `products.OrgItem`
- `transactions.Payment`
- `transactions.PaymentApplication`
- `transactions.PaymentMethod`
- `transactions.PaymentTerm`
- `communications.Phone`
- `transactions.Project`
- `transactions.ProposalLine`
- `transactions.PurchaseLine`
- `docs.QuestionAnswer`
- `transactions.Receipt`
- `transactions.ReceiptLine`
- `core.RefsMismatchLog`
- `orgs.Rep`
- `core.Report`
- `transactions.Requisition`
- `transactions.RequisitionLine`
- `products.Serial`
- `products.SerialLog`
- `products.Service`
- `core.Setting`
- `products.SiteInventory`
- `products.Specification`
- `docs.Tag`
- `accounts.TaxJurisdiction`
- `core.Template`
- `accounts.Term`
- `core.UserDailyLog`
- `products.Variant`
- `orgs.Vendor`
- `products.Warehouse`
- `transactions.WorkOrderLine`

### TransactionBaseModel (transactions)

- `transactions.Invoice`
- `transactions.Order`
- `transactions.Proposal`
- `transactions.Purchase`
- `transactions.WorkOrder`

### Other

- `ai_assistant.Conversation`
- `products.InventoryReservation`
- `ai_assistant.Message`
- `products.PendingInventoryAdjustment`
- `core.SoftDeleteLedger`
