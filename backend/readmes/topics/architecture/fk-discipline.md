# FK Discipline — Complete Reference

**Scar origin:** Touch.contact used CASCADE — deleting a contact deleted all
touch history. Extended audit found CASCADE on all communication models.
All converted to values (BigIntegerField) on 2026-08-27.

## The Rule

| Pattern | When to use | on_delete |
|---------|-------------|-----------|
| **FK CASCADE** | Child has no meaning without parent (line→header) | CASCADE |
| **FK PROTECT** | Prevent deletion while references exist (warehouse, BOM component) | PROTECT |
| **FK SET_NULL** | Both independent, but Django ORM benefits needed | SET_NULL |
| **BigIntegerField** | Both independent, no ORM traversal needed | — (no cascade) |

**Default for new fields:** BigIntegerField. Use FK only with explicit justification.

## Complete Field Inventory

### Correct CASCADE (structural — child dies with parent)

| Model | Field | Target | Why CASCADE is correct |
|-------|-------|--------|----------------------|
| InvoiceLine.invoice | Invoice | Line is part of invoice |
| OrderLine.order | Order | Line is part of order |
| ProposalLine.proposal | Proposal | Line is part of proposal |
| PurchaseLine.purchase | Purchase | Line is part of purchase |
| WorkOrderLine.workorder | WorkOrder | Line is part of workorder |
| RequisitionLine.requisition | Requisition | Line is part of requisition |
| ReceiptLine.receipt | Receipt | Line is part of receipt |
| Payment.invoice | Invoice | Payment applies to specific invoice |
| Payment.purchase | Purchase | Payment applies to specific purchase |
| PaymentApplication.payment | Payment | Application is part of payment |
| PaymentApplication.invoice | Invoice | Application targets specific invoice |
| PendingPaymentApplication.* | Payment/Invoice | Same as PaymentApplication |
| ProjectAssociation.project | Project | Junction record IS the relationship |
| UserDailyLog.user | AUTH_USER | Log belongs to user session |
| UserProfile.user | AUTH_USER | Profile IS the user extension |
| Action.parent_action | Action | Child action depends on parent |
| Bundle.connection | Connection | Bundle belongs to connection |
| SerialLog.serial | Serial | Log entry belongs to serial |
| CatalogLine.catalog | Catalog | Line is part of catalog |
| BillOfMaterial.parent_item | Item | BOM belongs to parent item |
| Variant.item | Item | Variant IS the item |
| Variant.parent_item | Item | Variant derives from parent |
| OrgItem.orgbase | OrgBase | Pricing record belongs to org |
| DeliveryVisit.orgbase | OrgBase | Visit belongs to org |
| DeliveryLine.delivery_visit | DeliveryVisit | Line is part of visit |
| DeliveryLine.orgitem | OrgItem | Line references org pricing |
| InventoryCheckLine.* | InventoryCheck/OrgItem | Line is part of check |
| InventoryReservation.item | Item | Reservation is for specific item |
| Conversation.user | AUTH_USER | Chat belongs to user |
| Message.conversation | Conversation | Message is part of conversation |
| SchemaDrift.git_event | GitEvent | Drift detected in specific event |
| SourceFile.project | ConversionProject | File belongs to project |
| ColumnMap.source_file | SourceFile | Map belongs to file |
| StagingRow.source_file | SourceFile | Row belongs to file |
| PassLog.project | ConversionProject | Log belongs to project |
| Oddity.project | ConversionProject | Oddity belongs to project |

### Correct PROTECT (prevent deletion while references exist)

| Model | Field | Target | Why PROTECT is correct |
|-------|-------|--------|----------------------|
| BaseLineCore.item_fk | Item | Can't delete item while on a transaction |
| InventoryLayer.warehouse | Warehouse | Can't delete warehouse with inventory |
| InventoryMovement.warehouse | Warehouse | Can't delete warehouse with history |
| InventoryReservation.warehouse | Warehouse | Can't delete warehouse with holds |
| ReceiptLine.warehouse | Warehouse | Can't delete warehouse with receipts |
| BillOfMaterial.child_item | Item | Can't delete component while in a BOM |

### Correct SET_NULL (independent lifecycle, ORM benefits)

| Model | Field | Target | Notes |
|-------|-------|--------|-------|
| TransactionBaseModel.customer | OrgBase | Transaction survives customer deactivation |
| TransactionBaseModel.vendor | OrgBase | Transaction survives vendor deactivation |
| TransactionBaseModel.manufacturer | OrgBase | Same |
| TransactionBaseModel.contact | Contact | Same |
| TransactionBaseModel.terms_fk | PaymentTerm | Terms can change |
| Contact.employee/customer/vendor/manufacturer/rep | OrgBase | Contact survives org deactivation |
| OrgBase.terms_fk | PaymentTerm | Terms can change |
| OrgBase.tax_jurisdiction | TaxJurisdiction | Jurisdiction can change |
| Item.vendor/manufacturer | OrgBase | Item survives org deactivation |
| Catalog.orgbase/customer_orgbase/etc. | OrgBase | Catalog survives org deactivation |
| Catalog.connection | Connection | Catalog survives connection removal |
| Receipt.purchase/workorder | Purchase/WorkOrder | Receipt survives source deactivation |
| ReceiptLine.purchase_line/workorder_line | *Line | Receipt survives source line removal |
| ReceiptLine.inventory_layer | InventoryLayer | Receipt survives layer depletion |
| InventoryMovement.inventory_layer | InventoryLayer | Movement history survives |
| InventoryReservation.inventory_layer | InventoryLayer | Reservation survives |
| Serial.inventory_layer | InventoryLayer | Serial survives layer depletion |
| OrgItem.catalog | Catalog | Pricing survives catalog removal |
| Ledger.org/invoice/term/gl_account | Various | Ledger survives reference changes |
| Erosion.org/contact | OrgBase/Contact | Erosion record survives |
| JournalBatch.run_by | Contact | Batch survives contact changes |
| AuditLog.user / APILog.user | Contact | Log survives user changes |
| UserProfile.contact | Contact | Profile survives contact changes |
| QuestionAnswer.document | Document | QA survives document changes |
| AliceObservation.contact/acknowledged_by | Contact | Observation survives |

### Correct BigIntegerField (value — no cascade, no ORM traversal)

| Model | Field | Target | Notes |
|-------|-------|--------|-------|
| Action.contact_id | Contact | Independent lifecycle |
| Action.project_id | Project | Independent lifecycle |
| Touch.contact_id | Contact | Historical record survives deletion |
| Touch.action_id | Action | Touch survives action deletion |
| Touch.org_id | OrgBase | Paired with org_model discriminator |
| OrgBase.contact_id | Contact | Primary-among-many pointer |
| Address.contact_id | Contact | Communication survives contact deletion |
| Phone.contact_id | Contact | Same |
| Email.contact_id | Contact | Same |
| Domain.contact_id | Contact | Same |
| Contact.email_id/address_id/phone_id/domain_id | Various | PJPV pointers to primary comm |
| OrgBase.address_id/email_id/phone_id/domain_id | Various | PJPV pointers to primary comm |
| Setting.org_id/contact_id | OrgBase/Contact | Scope pointers |
| Project.contact_id | Contact | Project owner pointer |
| TransactionBaseModel.parent_id | Polymorphic | Source document reference |
| Payment.parent_id | Polymorphic | Source document |
| GlJournal.source_id | Polymorphic | Paired with source_model |
| Erosion.source_id/parent_id | Polymorphic | Paired with discriminator |
| InventoryLayer.source_doc_id | Polymorphic | Source receipt/PO |
| InventoryMovement.source_doc_id | Polymorphic | Source transaction |
| ItemXRef.source_id | Polymorphic | External system reference |
| ProjectAssociation.object_id | Polymorphic | Paired with model_code |
| StatementLine.payment_id | Payment | Loose reference |
| LinkageEntry.group_id/record_id | Polymorphic | Linkage group system |
| Tag.record_id | Polymorphic | Paired with model_name |
| QuestionAnswer.parent_id | Polymorphic | Paired with parent_model |

### REVIEW NEEDED — FKs that may be wrong

| Model | Field | Current | Concern |
|-------|-------|---------|---------|
| Payment.contact | FK CASCADE | Should a payment disappear if the contact is deleted? Likely should be SET_NULL or BigInt |
| AliceCoachingLog.contact | FK CASCADE | Coaching history should survive contact deletion — convert to BigInt |
| AliceInsight.contact | FK CASCADE | Insights should survive — convert to BigInt |
| Contact.employee/customer/vendor/manufacturer/rep | FK SET_NULL | These are the WC2 value pattern. Bill used BigInt in WC2. Consider converting — but SET_NULL is safe (no data loss) |
| DeliveryVisit.customer_orgbase | FK CASCADE | Visit history should survive customer deactivation? |

## Alice Orphan Watch

With values replacing FKs, orphan records can accumulate. Alice runs a weekly scan:

1. Find communication records (Email, Phone, Address, Domain) where `contact_id` points to a deleted/inactive Contact
2. Find Touch records where `contact_id` or `action_id` points to deleted records
3. Mark orphans for deletion
4. Supervisor has 30 days to save them
5. Report: count per model, record IDs, suggested action
