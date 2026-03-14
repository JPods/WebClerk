# Primary Organization Defaults (wc2 -> wc3)

This document defines how to manage the singleton Setting record:

- Setting.name = primary_organization
- Setting.purpose = db_defaults
- Setting.parent_model = customer

It also defines how wc2-style defaults under data.wc2defaults should be explained, retained, renamed, or removed.

## Current State

The singleton currently stores:

- Core identity fields used by runtime services:
  - org_id
  - display_name
  - company
  - org_type
  - is_active
- A large legacy payload at data.wc2defaults.

## Design Rules

1. Primary identity keys are canonical.

- org_id is the source of truth.
- display_name, company, org_type, is_active are snapshots for operator context.
- Runtime lookups must resolve the OrgBase record by org_id.

2. wc2defaults is transitional config.

- wc2defaults is allowed during migration.
- New code should not directly bind to raw wc2 key names.
- New code should read from normalized wc3 config keys where available.

3. Every retained default needs an explanation and an owner.

For each retained key, define:
- What the key controls.
- Data type and allowed values.
- Read path in code (where used).
- Write path in admin/API (how changed).
- Fallback behavior if missing.

4. Unknown keys are not automatically deleted.

- Unknown keys are first marked as review-needed.
- Remove only after confirming no active reads in backend, frontend, scripts, or integrations.

## Governance Model

Each wc2defaults key should have one status:

- keep: still used and valid.
- rename: needs wc3 naming and compatibility mapping.
- remove: obsolete and safe to delete.
- defer: unclear; keep temporarily until usage analysis finishes.

Recommended metadata per key (stored in docs first, optionally in Setting later):

- status
- explanation
- owner
- reviewed_on
- replacement_key (for rename)

## Suggested Normalized Namespaces

When migrating keys from wc2defaults, group under clear namespaces:

- pricing.*
- inventory.*
- shipping.*
- commissions.*
- credit_card.*
- ui.*
- sync.*
- accounting.*
- print.*
- integrations.*

Example mapping pattern:

- wc2 key: TrackProposalQty
- wc3 key: inventory.track_proposal_qty

## Immediate Cleanup Targets

1. Typo field

- wc2defaults.explaination appears to be misspelled.
- Replace with explanation if retained.

2. Secret-like values

- Keys like CCVerPassword should not remain in plaintext defaults.
- Move sensitive values to environment variables or secret storage.
- Keep only non-sensitive metadata in the Setting record.

3. Legacy host/path fields

- Fields such as SharePath, ShareServer, PathOfStatus, jitHelpFolder likely represent legacy workstation assumptions.
- Verify live usage before keeping.

## How To Work Through The List

Phase 1: Inventory and classify

- Export all wc2defaults keys.
- Add one row per key in a working table with status = defer.
- Mark obvious keep/remove/rename items.

Phase 2: Usage scan

- Search backend and frontend for each key and known aliases.
- Identify runtime read points and remove dead keys.

Phase 3: Compatibility layer

- For renamed keys, implement a mapping function:
  - read new wc3 key first
  - fallback to wc2 key
  - optionally write both during transition

Phase 4: Hardening

- Move secrets out of Setting.data.
- Add validation for retained keys.
- Add tests for key defaults and fallback behavior.

Phase 5: Final prune

- Remove keys marked remove.
- Keep a dated changelog of removed keys.

## Proposed Documentation Table Template

Use this table structure in follow-up docs:

- key
- status (keep | rename | remove | defer)
- explanation
- wc3_key
- used_by
- owner
- reviewed_on

## Operational Notes

- Keep exactly one active primary_organization record per database.
- Update the singleton only through the primary org service where possible.
- Treat data.wc2defaults as migration data, not a permanent unbounded config bucket.

## Related Files

- readmes/topics/infrastructure/primary-organization.md
- apps/orgs/services/primary_org.py
- apps/core/models/setting.py

## Current .data Inventory (Draft)

This section is auto-generated from the live `primary_organization` Setting and contains draft explanations.

### Top-level `data` keys

| Key | Example Value | Draft Explanation |
| --- | --- | --- |
| `company` | `'WebClerk'` | Alias snapshot kept for compatibility with legacy readers. |
| `display_name` | `'WebClerk'` | Human-readable org name snapshot for operator context. |
| `is_active` | `True` | Snapshot of org active state at last update. |
| `org_id` | `2` | Primary organization primary key used by runtime lookup. |
| `org_type` | `'customer'` | Org type snapshot, expected customer for this singleton. |
| `wc2defaults` | `{'FOB': 'Tulsa OK', 'Terms': 'COD', 'Slogan': '', 'CODTerm': 'COD', 'CloneWO'...` | Legacy wc2 defaults payload pending classification/migration. |

### `data.wc2defaults` keys (draft explanations)

| Key | Draft Explanation |
| --- | --- |
| `APriceName` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `AddAllItem` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `AddInvCmplOrd` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `AlertNoCity` | Legacy feature toggle flag; verify active readers before retaining. |
| `Approval2Print` | Legacy feature toggle flag; verify active readers before retaining. |
| `AutoCalcFreight` | Legacy feature toggle flag; verify active readers before retaining. |
| `BPriceName` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `CODTerm` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `CPriceName` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `CancelByDate` | Date/time scheduling or timing behavior setting. |
| `CancelByDays` | Date/time scheduling or timing behavior setting. |
| `CashDrawOpen` | Legacy numeric threshold/counter; verify units and current usage. |
| `ClosingPrd1` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `ClosingPrd2` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `ClosingPrd3` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `CommissionOnAmount` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `CommissionType` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `ConfirmEmailSkip` | Communication/help/contact behavior default. |
| `ConfirmShipChange` | Shipping/logistics default. |
| `CostUpdate` | Date/time scheduling or timing behavior setting. |
| `CustAddr2PO` | Legacy feature toggle flag; verify active readers before retaining. |
| `DPriceName` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |

| `DateDDMMYY` | Date/time scheduling or timing behavior setting. |
| `DelayProcess` | Date/time scheduling or timing behavior setting. |
| `DelayQuit` | Date/time scheduling or timing behavior setting. |
| `DialOut` | Communication/help/contact behavior default. |
| `DialSpecial` | Communication/help/contact behavior default. |
| `DisableProcessWindow` | UI/display/workflow preference from legacy app. |
| `DoSerialNums` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `DunsNumber` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `EndOfYearDay` | Date/time scheduling or timing behavior setting. |
| `EndRecordExport` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `EndofYearMon` | Date/time scheduling or timing behavior setting. |
| `FOB` | Shipping/logistics default. |
| `FinanceChargePC` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `FindCustChkbx` | UI/display/workflow preference from legacy app. |
| `GracePrd1` | Legacy numeric threshold/counter; verify units and current usage. |
| `GracePrd2` | Legacy numeric threshold/counter; verify units and current usage. |
| `GracePrd3` | Legacy numeric threshold/counter; verify units and current usage. |
| `HeadingPrd1` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `HeadingPrd2` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `HeadingPrd3` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `HelpSource` | Communication/help/contact behavior default. |
| `IgnoreFoneFormat` | Legacy feature toggle flag; verify active readers before retaining. |
| `InvCondition` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `InvoiceComment` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `InvoicesLockOnPrint` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `InvtByOrdBOM` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `ItemBundle` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `ItemQtyPrecisio` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `ItemSrSeqXRef` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `ItemSrSequence` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `KeepRecord` | UI/display/workflow preference from legacy app. |
| `LCostUpDate` | Date/time scheduling or timing behavior setting. |
| `LateFreq` | Legacy numeric threshold/counter; verify units and current usage. |
| `Latitude` | Legacy numeric threshold/counter; verify units and current usage. |
| `LeadResponse` | Legacy numeric threshold/counter; verify units and current usage. |
| `LearningMode` | Legacy feature toggle flag; verify active readers before retaining. |
| `LedgerLinkedOnly` | Legacy feature toggle flag; verify active readers before retaining. |
| `LetterRecord` | UI/display/workflow preference from legacy app. |
| `LoadPlanning` | Legacy feature toggle flag; verify active readers before retaining. |
| `LockAcctNumber` | Legacy feature toggle flag; verify active readers before retaining. |
| `Longitude` | Legacy numeric threshold/counter; verify units and current usage. |
| `MacAuthAddress` | Legacy feature toggle flag; verify active readers before retaining. |
| `ManualOrdStat` | Legacy feature toggle flag; verify active readers before retaining. |
| `MaxArray` | Legacy numeric threshold/counter; verify units and current usage. |
| `MinimumMargin` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `MonLastPosted` | Date/time scheduling or timing behavior setting. |
| `NeedDelay` | Date/time scheduling or timing behavior setting. |
| `NoCODHand` | Legacy feature toggle flag; verify active readers before retaining. |
| `NoWeekEndShip` | Shipping/logistics default. |
| `OnNewRecordKeepOpen` | UI/display/workflow preference from legacy app. |
| `OpenItem` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `OrdLnTrak` | Legacy feature toggle flag; verify active readers before retaining. |
| `OrdToInvDShipOn` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `Order2POByBLQ` | Legacy numeric threshold/counter; verify units and current usage. |
| `OrderLinesInvoiceLines` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `OverPayInvoices` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `POCondition` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `POoloOrderDate` | Date/time scheduling or timing behavior setting. |
| `PathOfStatus` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `PeriodPerHour` | Date/time scheduling or timing behavior setting. |
| `PrJrnlToInsight` | Legacy numeric threshold/counter; verify units and current usage. |
| `PrcssMemory` | Legacy numeric threshold/counter; verify units and current usage. |
| `PriceCharacter` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `PriceMatrixUse` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `PrimeDefault` | Legacy numeric threshold/counter; verify units and current usage. |
| `PrmInvcDateShip` | Date/time scheduling or timing behavior setting. |
| `ProcessNewRecord` | UI/display/workflow preference from legacy app. |
| `QtyAvailable` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `RecentDays` | Date/time scheduling or timing behavior setting. |
| `SalesTaxOnAmount` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `SelectInvField` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `SerialNumOrd` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `SetConfirm` | Legacy feature toggle flag; verify active readers before retaining. |
| `ShareCommand` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `ShareName` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `SharePath` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `ShareServer` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `ShipCondition` | Shipping/logistics default. |
| `ShipVia1` | Shipping/logistics default. |
| `ShowPayByDate` | Date/time scheduling or timing behavior setting. |
| `ShowTallyInForcast` | UI/display/workflow preference from legacy app. |
| `SingleRecordoLo` | UI/display/workflow preference from legacy app. |
| `SiteCode` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `Slogan` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `SortOnDisplay` | UI/display/workflow preference from legacy app. |
| `StatusDelay` | Date/time scheduling or timing behavior setting. |
| `TaxIDCode` | Sensitive/identity value; should likely move to secure env/secret storage. |
| `TaxWebService` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `Terms` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `TotalPrecision` | Legacy numeric threshold/counter; verify units and current usage. |
| `TrackProposalQty` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `TrackSalesID` | Legacy feature toggle flag; verify active readers before retaining. |
| `TransAction` | Legacy numeric threshold/counter; verify units and current usage. |
| `TypeSale` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `UUIDKey` | Sensitive/identity value; should likely move to secure env/secret storage. |
| `UniqueID` | Legacy numeric threshold/counter; verify units and current usage. |
| `UnitCostPrecisi` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `UnitPricePrecis` | Pricing/financial behavior default; candidate for normalized pricing/accounting namespace. |
| `UpdateCommFromMaster` | Date/time scheduling or timing behavior setting. |
| `WebLogOption` | Legacy numeric threshold/counter; verify units and current usage. |
| `WebOrdStatus` | Legacy numeric threshold/counter; verify units and current usage. |
| `WindowHeightDefault` | UI/display/workflow preference from legacy app. |
| `WindowWidthDefault` | UI/display/workflow preference from legacy app. |
| `altPhoneFormat` | Communication/help/contact behavior default. |
| `dtLastSync` | Date/time scheduling or timing behavior setting. |
| `explaination` | Legacy wc2 default; usage unclear, keep as defer until code usage is verified. |
| `jitHelpFolder` | Communication/help/contact behavior default. |
| `jitHelpPath` | Integration/path endpoint setting from wc2; verify whether still used in wc3. |
| `trackInventory` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
| `valueInventory` | Inventory/item workflow setting; likely maps into inventory.* defaults. |
