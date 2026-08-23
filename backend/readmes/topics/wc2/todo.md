# WC2 Mining TODO

Working note for extracting useful WC2 behavior and layout ideas without inheriting WC2 architecture.

Guiding policy:
- Use WC2 as behavior reference, not implementation template.
- Port intent, simplify design, and align with WC3 manage actions + React2025 patterns.

Retention policy:
- Keep WC2 and Vue2020 sources available until parity checklists and migration acceptance tests are complete.
- After parity is signed off, archive legacy sources as read-only snapshot artifacts (do not delete immediately).
- Remove only after one full release cycle confirms no rollback dependency.

## Current Strict-Type Track (React2025)

- [ ] Proposal/Purchase list page implicit-any cleanup (next strict slice)
- [ ] Transaction line-detail props normalization across proposal/purchase/workorder line pages
- [ ] Shared data-table wrapper typing pass to remove remaining dist import shims
- [ ] Optional: split qqq demo files into separate permissive tsconfig to protect strict migration velocity

## WC2 Recon Scope Snapshot

Source inventory from [00WebClerk19/Project/Sources](../../../../00WebClerk19/Project/Sources):
- Methods files: 4,087
- Forms files: 493
- TableForms files: 10,629

Convert from:
- /Users/williamjames/Documents/CommerceExpert/vue2020 
- /Users/williamjames/Documents/CommerceExpert/VueChimney
- /Users/williamjames/Documents/CommerceExpert/00WebClerk19
- /Users/williamjames/Documents/CommerceExpert/webclerk2

## High-Value Function Clusters To Mine

### 1) Tally and Reporting Behavior

Candidate methods:
- [Methods/WCapiTask_TallyMasters.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_TallyMasters.4dm)
- [Methods/Execute_TallyMasterNewProcess.4dm](../../../../00WebClerk19/Project/Sources/Methods/Execute_TallyMasterNewProcess.4dm)
- [Methods/GetTallyMasterScript.4dm](../../../../00WebClerk19/Project/Sources/Methods/GetTallyMasterScript.4dm)
- [Methods/TallyMasterExecuteSort.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyMasterExecuteSort.4dm)
- [Methods/TallyMasterRecordsToTextXML.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyMasterRecordsToTextXML.4dm)
- [Methods/ShowTallyResult.4dm](../../../../00WebClerk19/Project/Sources/Methods/ShowTallyResult.4dm)
- [Methods/TallySalesByMfrByMonth.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallySalesByMfrByMonth.4dm)
- [Methods/TallyMonthlyUsage.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyMonthlyUsage.4dm)
- [Methods/TallyUsageEOMValue.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyUsageEOMValue.4dm)
- [Methods/TallyEndOfYr.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyEndOfYr.4dm)

Action items:
- [ ] Build a mapping matrix: WC2 tally name -> WC3 action key -> React page mode
- [ ] Capture sort/group/rollup semantics not yet represented in WC3
- [ ] Identify any WC2 edge-case coercions for null/blank/date boundaries
- [ ] Add export parity checklist for csv/json (column order, naming, totals rows)

### 2) WCapi and Task Command Patterns

Candidate methods:
- [Methods/WCapi_SaveRecord.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_SaveRecord.4dm)
- [Methods/WCapi_QueryByFieldValues.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_QueryByFieldValues.4dm)
- [Methods/WCapi_RecordBasics.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_RecordBasics.4dm)
- [Methods/WCapi_SetupFieldLists.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_SetupFieldLists.4dm)
- [Methods/WCapi_SetParameter.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_SetParameter.4dm)
- [Methods/WCapiTask_AddRecord.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_AddRecord.4dm)
- [Methods/WCapiTask_DeleteRecord.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_DeleteRecord.4dm)
- [Methods/WCapiTask_Clone.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_Clone.4dm)
- [Methods/WCapiTask_AddFieldsOutput.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_AddFieldsOutput.4dm)

Action items:
- [ ] Extract reusable task primitives and map to WC3 manage actions
- [ ] Harvest useful parameter normalization logic for field projections/filters
- [ ] Compare WC2 dynamic field output behavior with WC3 safe allowlist strategy

### 3) Transfer and Inventory Flow Behavior

Candidate methods:
- [Methods/WO_TransferReceive.4dm](../../../../00WebClerk19/Project/Sources/Methods/WO_TransferReceive.4dm)
- [Methods/WO_TransferDirect.4dm](../../../../00WebClerk19/Project/Sources/Methods/WO_TransferDirect.4dm)
- [Methods/WOTransfers.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOTransfers.4dm)
- [Methods/WOTransfers_Query.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOTransfers_Query.4dm)
- [Methods/WOBarCodeReceive.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOBarCodeReceive.4dm)
- [Methods/dInventoryCreate.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryCreate.4dm)
- [Methods/dInventoryImport.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryImport.4dm)
- [Methods/dInventoryFillFromArray.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryFillFromArray.4dm)
- [Methods/dInventoryRebuildPOLines.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryRebuildPOLines.4dm)

Action items:
- [ ] Compare WC2 transfer guardrails against WC3 pending/remaining model
- [ ] Identify UI-assisted operator steps to turn into server-side validations
- [ ] Document barcode receive workflow and evaluate modern scanner UX in React

### 4) Financial Posting and Ledger Behavior

Candidate methods:
- [Methods/GL_PostConnected.4dm](../../../../00WebClerk19/Project/Sources/Methods/GL_PostConnected.4dm)
- [Methods/GL_CreatePrJrnl.4dm](../../../../00WebClerk19/Project/Sources/Methods/GL_CreatePrJrnl.4dm)
- [Methods/GL_MapInsightAc.4dm](../../../../00WebClerk19/Project/Sources/Methods/GL_MapInsightAc.4dm)
- [Methods/Ledger_InvSave.4dm](../../../../00WebClerk19/Project/Sources/Methods/Ledger_InvSave.4dm)
- [Methods/Ledger_PaySave.4dm](../../../../00WebClerk19/Project/Sources/Methods/Ledger_PaySave.4dm)
- [Methods/111Rp_DCashLedger.4dm](../../../../00WebClerk19/Project/Sources/Methods/111Rp_DCashLedger.4dm)

Action items:
- [ ] Identify posting invariants to encode as idempotent pending-ledger processors
- [ ] Note any legacy account mapping defaults still needed in WC3 migration scripts
- [ ] Verify cash-ledger report expectations for parity harness

## Layout and UX Patterns Worth Mining

Candidate form/layout artifacts:
- [Forms/oLoButtonBar/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/oLoButtonBar/form.4DForm)
- [Forms/QueryEditor-addCol/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/QueryEditor-addCol/form.4DForm)
- [Forms/LBXDraft/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/LBXDraft/form.4DForm)
- [Forms/ListBoxDraftNoSF/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/ListBoxDraftNoSF/form.4DForm)
- [TableForms/1/WorkOrdersTransfer/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/WorkOrdersTransfer/form.4DForm)
- [TableForms/1/InventoryAdjustment/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/InventoryAdjustment/form.4DForm)
- [TableForms/1/MatrixOrdering/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/MatrixOrdering/form.4DForm)
- [TableForms/1/SalesReport/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/SalesReport/form.4DForm)

Action items:
- [ ] Extract reusable interaction patterns: button bars, query-builder add-column flow, listbox drafts, matrix ordering
- [ ] Convert strong patterns into React design primitives instead of one-off pages
- [ ] Define where WC2 layout complexity should be intentionally simplified

## Deliverables

- [ ] WC2 mining matrix doc: behavior, source method/form, WC3 target, parity status
- [ ] Top 10 migration candidates with effort and risk scoring
- [ ] Gaps list where WC2 has value but WC3 currently has no equivalent
- [ ] Test checklist for each adopted behavior (unit + integration + UI)

## Ranked Top 10 Mining Sequence

Scoring legend:
- Impact: 1 (low) to 5 (high)
- Effort: 1 (low) to 5 (high)
- Risk: 1 (low) to 5 (high)

1. Tally execution and export parity hardening
- Sources: [Methods/WCapiTask_TallyMasters.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_TallyMasters.4dm), [Methods/Execute_TallyMasterNewProcess.4dm](../../../../00WebClerk19/Project/Sources/Methods/Execute_TallyMasterNewProcess.4dm), [Methods/TallyMasterRecordsToTextXML.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyMasterRecordsToTextXML.4dm)
- Target: phase-4 registry execute/export behavior and csv/json parity checklist
- Impact 5, Effort 3, Risk 2

2. Sales-by-dimension and period semantics parity
- Sources: [Methods/TallySalesByMfrByMonth.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallySalesByMfrByMonth.4dm), [Methods/TallySumOrdSale.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallySumOrdSale.4dm), [Methods/TallyPastDueLoo.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyPastDueLoo.4dm)
- Target: strengthen monthly/yoy edge cases and date-boundary tests
- Impact 5, Effort 3, Risk 3

3. Inventory usage/value tally semantics parity
- Sources: [Methods/TallyMonthlyUsage.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyMonthlyUsage.4dm), [Methods/TallyUsageEOMValue.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyUsageEOMValue.4dm), [Methods/TallyInventoryProcess.4dm](../../../../00WebClerk19/Project/Sources/Methods/TallyInventoryProcess.4dm)
- Target: reconcile usage/value/adjustment rollups with WC3 valuation model
- Impact 5, Effort 4, Risk 3

4. Transfer and receive guardrails consolidation
- Sources: [Methods/WO_TransferReceive.4dm](../../../../00WebClerk19/Project/Sources/Methods/WO_TransferReceive.4dm), [Methods/WOTransfers.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOTransfers.4dm), [Methods/WO_TransferDirect.4dm](../../../../00WebClerk19/Project/Sources/Methods/WO_TransferDirect.4dm)
- Target: tighten pending/remaining invariants and transfer validations
- Impact 5, Effort 4, Risk 4

5. WCapi task primitive extraction
- Sources: [Methods/WCapi_SaveRecord.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_SaveRecord.4dm), [Methods/WCapi_QueryByFieldValues.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapi_QueryByFieldValues.4dm), [Methods/WCapiTask_AddRecord.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_AddRecord.4dm)
- Target: explicit WC3 manage task primitives and parameter normalization
- Impact 4, Effort 3, Risk 2

6. Ledger posting and payment invariants
- Sources: [Methods/Ledger_InvSave.4dm](../../../../00WebClerk19/Project/Sources/Methods/Ledger_InvSave.4dm), [Methods/Ledger_PaySave.4dm](../../../../00WebClerk19/Project/Sources/Methods/Ledger_PaySave.4dm), [Methods/GL_PostConnected.4dm](../../../../00WebClerk19/Project/Sources/Methods/GL_PostConnected.4dm)
- Target: codify idempotent posting constraints in pending-ledger flow
- Impact 5, Effort 4, Risk 4

7. Query editor and add-column workflow uplift
- Sources: [Forms/QueryEditor-addCol/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/QueryEditor-addCol/form.4DForm), [Forms/TableList/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/TableList/form.4DForm)
- Target: reusable React query-builder patterns for power users
- Impact 4, Effort 4, Risk 2

8. Listbox draft and column personalization patterns
- Sources: [Forms/LBXDraft/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/LBXDraft/form.4DForm), [Forms/ListBoxDraftNoSF/form.4DForm](../../../../00WebClerk19/Project/Sources/Forms/ListBoxDraftNoSF/form.4DForm)
- Target: robust saved-column presets + field visibility UX in R25
- Impact 4, Effort 3, Risk 2

9. Work order transfer UI simplification opportunity
- Sources: [TableForms/1/WorkOrdersTransfer/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/WorkOrdersTransfer/form.4DForm), [Methods/WOTransfer_WindowOpen.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOTransfer_WindowOpen.4dm)
- Target: simplified modern transfer UI retaining critical operator steps
- Impact 4, Effort 4, Risk 3

10. Sales and cash ledger reporting alignment
- Sources: [TableForms/1/SalesReport/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/SalesReport/form.4DForm), [Methods/111Rp_DCashLedger.4dm](../../../../00WebClerk19/Project/Sources/Methods/111Rp_DCashLedger.4dm)
- Target: report parity harness and finance-facing validation outputs
- Impact 4, Effort 3, Risk 3

11. Barcode receive and scan-to-action workflow
- Sources: [Methods/WOBarCodeReceive.4dm](../../../../00WebClerk19/Project/Sources/Methods/WOBarCodeReceive.4dm), [Methods/WO_TransferReceive.4dm](../../../../00WebClerk19/Project/Sources/Methods/WO_TransferReceive.4dm)
- Target: mobile-friendly scan flow with explicit server validations and audit trails
- Impact 4, Effort 4, Risk 3

12. Clone and template task behavior parity
- Sources: [Methods/WCapiTask_Clone.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_Clone.4dm), [Methods/WCapiTask_AddFieldsOutput.4dm](../../../../00WebClerk19/Project/Sources/Methods/WCapiTask_AddFieldsOutput.4dm)
- Target: reusable clone/template operations for transaction acceleration in WC3 manage actions
- Impact 4, Effort 3, Risk 2

13. Inventory rebuild and reconciliation guardrails
- Sources: [Methods/dInventoryRebuildPOLines.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryRebuildPOLines.4dm), [Methods/dInventoryFillFromArray.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryFillFromArray.4dm), [Methods/dInventoryImport.4dm](../../../../00WebClerk19/Project/Sources/Methods/dInventoryImport.4dm)
- Target: controlled repair/rebuild tools for operations support with deterministic outputs
- Impact 4, Effort 4, Risk 4

14. Matrix ordering UX modernization
- Sources: [TableForms/1/MatrixOrdering/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/MatrixOrdering/form.4DForm)
- Target: high-density order-entry pattern for bulk assortment workflows in React
- Impact 3, Effort 4, Risk 2

15. Inventory adjustment operational ergonomics
- Sources: [TableForms/1/InventoryAdjustment/form.4DForm](../../../../00WebClerk19/Project/Sources/TableForms/1/InventoryAdjustment/form.4DForm)
- Target: safer adjustment wizard with reason codes, preview diffs, and approval checkpoints
- Impact 4, Effort 3, Risk 3

## Recommended First 3 To Execute

1. Tally execution and export parity hardening
- Why first: immediate value to current phase-4 implementation and lowest risk.

2. Sales-by-dimension and period semantics parity
- Why second: extends already-deployed phase-2 surface and closes reporting confidence gaps.

3. Inventory usage/value tally semantics parity
- Why third: completes the core tally family and stabilizes valuation-sensitive outputs.

## Notes

- This todo is intentionally biased toward reuse of business intent, not old implementation mechanics.
- Any adopted behavior should be normalized to current naming and envelope policies.

## Vue2020 Mining Addendum

Why include it:
- Vue2020 captures transitional UX and interaction decisions that may not be obvious from WC2 forms alone.
- It provides concrete browser-era implementations that can shorten React2025 design discovery.

Initial candidate areas:
- [vue2020/src/views](../../../../vue2020/src/views)
- [vue2020/src/components](../../../../vue2020/src/components)
- [vue2020/src/router/index.js](../../../../vue2020/src/router/index.js)
- [vue2020/src/libs](../../../../vue2020/src/libs)

Action items:
- [ ] Build Vue2020 feature inventory: route/page/component -> WC3/R25 equivalent
- [ ] Tag each Vue2020 feature as keep, modernize, or retire
- [ ] Extract reusable UX patterns (filters, table actions, batch operations, keyboard flow)
- [ ] Capture API expectations from Vue2020 and compare to current wcapi envelope/behavior
- [ ] Add parity tests for any adopted Vue2020 behavior before implementation

## Triage Matrix (WC2 + Vue2020)

Use this as the first-pass decision board before implementation.

| Source | Target | Decision |
|---|---|---|
| WC2: Tally execution/export methods | WC3 manage actions + R25 tally registry pages | Keep |
| WC2: Sales-by-dimension tally semantics | WC3 report actions + parity tests | Keep |
| WC2: Inventory usage/value rollups | WC3 inventory tally services | Keep |
| WC2: Transfer guardrails/operator steps | WC3 transfer validators + pending invariants | Modernize |
| WC2: QueryEditor add-column flow | R25 query-builder primitives | Modernize |
| WC2: Matrix ordering form | R25 bulk order-entry experience | Modernize |
| WC2: Dense legacy button bars | R25 contextual action bars | Retire |
| Vue2020: route/view decomposition | R25 route/page composition standards | Keep |
| Vue2020: table filters and batch actions | Shared R25 data-table tooling | Keep |
| Vue2020: older client-side API assumptions | wcapi envelope with typed service wrappers | Retire |

Matrix action items:
- [ ] Add owner and due-date columns
- [ ] Add confidence score per row (1-5)
- [ ] Link each Keep/Modernize row to concrete implementation issue
