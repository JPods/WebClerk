/* LastChecked: 2026-09-18 | WhereUsed: Router.tsx, protectedRoutesConfig.tsx | WhoCreated: Bill+Claude */
/**
 * recordRoutes — the one list of /{model}/:id record pages.
 *
 * Router.tsx and protectedRoutesConfig.tsx both read this list. Before, each held
 * its own copy; the WindowManager copy lacked action, item's neighbours, document,
 * setting, report, project ... so /action/31242 fell through to the /:model
 * catch-all and showed an empty DataBrowser (2026-09-18).
 */
import React from "react";

const UiDetail = React.lazy(() => import("../apps/transactions/components/TransactionDetail"));
const ModelDetailPage = React.lazy(() => import("../components/common/ModelDetailPage"));

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <React.Suspense fallback={<div style={{padding:40}}>Loading...</div>}>{children}</React.Suspense>
);

// Transaction models — use UiDetail
export const TRANSACTION_MODELS = [
  'order', 'invoice', 'quote', 'purchase', 'workorder',
  'receipt', 'requisition', 'cash',
];

// Every other model with a record page — use ModelDetailPage
export const DETAIL_MODELS = [
  'contact', 'item', 'customer', 'vendor', 'manufacturer', 'employee', 'rep', 'action', 'touch',
  'document', 'setting', 'report', 'serial', 'project', 'email', 'phone', 'address', 'domain',
  'notification', 'warehouse', 'catalog', 'cash_method', 'gl_account', 'ledger', 'audit',
  'pending',
];

export const recordRoutes: { path: string; element: React.ReactElement }[] = [
  ...TRANSACTION_MODELS.map(m => ({ path: `/${m}/:id`, element: <S><UiDetail modelName={m} /></S> })),
  ...DETAIL_MODELS.map(m => ({ path: `/${m}/:id`, element: <S><ModelDetailPage modelName={m} /></S> })),
];
