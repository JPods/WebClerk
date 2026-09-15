# Unused & Duplicate Files (qqq_ prefix)

Files prefixed with `qqq_` are confirmed unused or duplicated. They are safe to delete once reviewed.

Search command: `find src -name "qqq_*" -type f`

---

## Legacy / Vue / Backup (5)

| File | Reason |
|------|--------|
| `src/apps/transactions/models/proposal/pages/qqq_ProposalDetailVueReact.tsx` | Legacy Vue-React hybrid — never imported |
| `src/apps/transactions/models/proposal/pages/qqq_ProposalDetailVue.tsx` | Legacy Vue port — never imported |
| `src/apps/transactions/models/invoice/pages/qqq_InvoiceDetailLegacy.tsx` | Legacy invoice detail — never imported |
| `src/type/qqq_kanban copy.ts` | Finder copy of `kanban.ts` — never imported |
| `src/apps/utils/kanban/type/qqq_kanban.backup.ts` | Backup of kanban type — never imported |

## Demo / Test / Example (4)

| File | Reason |
|------|--------|
| `src/apps/qqq_test.tsx` | Stub `<div>test</div>` component — never imported |
| `src/apps/transactions/qqq_ContactsDemo.tsx` | Demo contacts component — never imported |
| `src/apps/utils/3column/qqq_DemoThreeColumnPage.tsx` | Demo three-column page — never imported |
| `src/apps/utils/examples/qqq_ContactListExample.tsx` | Example component — never imported |

## Duplicate `sync/models/connection/` directory (7)

Active version is `src/apps/sync/connection/`. This entire `sync/models/connection/` directory is a never-imported copy.

| File | Reason |
|------|--------|
| `src/apps/sync/models/connection/qqq_Connection.ts` | Duplicate of `sync/connection/` |
| `src/apps/sync/models/connection/qqq_index.ts` | Duplicate of `sync/connection/` |
| `src/apps/sync/models/connection/pages/qqq_ConnectionDetail.tsx` | Duplicate of `sync/connection/pages/` |
| `src/apps/sync/models/connection/pages/qqq_ConnectionList.tsx` | Duplicate of `sync/connection/pages/` |
| `src/apps/sync/models/connection/services/qqq_connectionApi.ts` | Duplicate of `sync/connection/services/` |
| `src/apps/sync/models/connection/types/qqq_connectionType.ts` | Duplicate of `sync/connection/types/` |
| `src/apps/sync/models/connection/utils/qqq_connectionSchema.ts` | Duplicate of `sync/connection/utils/` |

## Duplicate `supports/campaign/` directory (3)

Active version is `src/apps/support/` (no trailing "s"). This `supports/` directory is a never-imported copy.

| File | Reason |
|------|--------|
| `src/apps/supports/models/campaign/qqq_index.ts` | Duplicate — `apps/support/` is active |
| `src/apps/supports/models/campaign/pages/qqq_CampaignList.tsx` | Duplicate — never imported externally |
| `src/apps/supports/models/campaign/pages/qqq_CampaignDisplay.tsx` | Duplicate — never imported externally |

## Duplicate docs model stubs (3)

Active versions are in subdirectories (`docs/models/tag/Tag.ts`, etc.). These bare files at `docs/models/` level are older, simpler interfaces.

| File | Reason |
|------|--------|
| `src/apps/docs/models/qqq_Tag.ts` | Duplicate of `docs/models/tag/Tag.ts` |
| `src/apps/docs/models/qqq_QuestionAnswer.ts` | Duplicate of `docs/models/question_answer/QuestionAnswer.ts` |
| `src/apps/docs/models/qqq_Document.ts` | Duplicate of `docs/models/document/Document.ts` |

## Unused `src/components/` (13)

Early-stage or abandoned components never wired into any page. Active equivalents live in `src/apps/`.

| File | Reason |
|------|--------|
| `src/components/qqq_CallReportForm.tsx` | Never imported |
| `src/components/qqq_InvoicesList.tsx` | Never imported |
| `src/components/qqq_OrdersList.tsx` | Never imported |
| `src/components/qqq_ProposalsList.tsx` | Never imported |
| `src/components/qqq_QAList.tsx` | Never imported |
| `src/components/qqq_ServiceForm.tsx` | Never imported |
| `src/components/qqq_TaskMarkerForm.tsx` | Never imported |
| `src/components/qqq_ProposalForm.tsx` | Never imported — active version at `proposal/components/ProposalForm.tsx` |
| `src/components/qqq_CustomerForm.tsx` | Never imported |
| `src/components/modals/qqq_LineItemModal.tsx` | Never imported |
| `src/components/transactions/payments/qqq_PaymentProcessor.tsx` | Never imported |
| `src/components/transactions/reservations/qqq_ReservationManager.tsx` | Never imported |
| `src/components/qqq_InputField.tsx` | Never imported — active version at `form/input/InputField.tsx` |

## Unused model / page files (4)

| File | Reason |
|------|--------|
| `src/model/qqq_httpResponse.interface.ts` | Never imported — replaced by WCAPI types |
| `src/model/qqq_modelMap.ts` | Never imported — superseded by other resolvers |
| `src/model/qqq_opportunity.interface.ts` | Never imported — abandoned interface |
| `src/pages/qqq_ItemDashboard.tsx` | Never imported — active version at `apps/products/models/item/pages/ItemDashboard.tsx` |
