/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser | WhoCreated: Bill+Claude */
import React from 'react';

/** Maps DataBrowser model name → .tsx detail route (used for double-click new-tab). */
export const APP_DETAIL_ROUTES: Record<string, string> = {
  order: '/order',
  invoice: '/invoice',
  quote: '/quote',
  purchase: '/purchase',
  workorder: '/workorder',
  receipt: '/receipt',
  requisition: '/requisition',
  cash: '/cash',
  customer: '/customer',
  item: '/item',
  contact: '/contact',
  vendor: '/vendor',
  manufacturer: '/manufacturer',
  employee: '/employee',
  rep: '/rep',
  action: '/action',
};

/** Lazy-loaded detail components for App mode inline rendering.
 *  Every model with a detail_layout Setting should be mapped here.
 *  Models NOT mapped fall through to Admin mode (BehaviorField grid). */
export const APP_DETAIL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  // Core
  contact: React.lazy(() => import('@/components/common/ModelDetailPage')),
  action: React.lazy(() => import('@/components/common/ModelDetailPage')),
  touch: React.lazy(() => import('@/components/common/ModelDetailPage')),
  report: React.lazy(() => import('@/apps/core/models/report/pages/ReportDisplay')),
  // Orgs
  customer: React.lazy(() => import('@/components/common/ModelDetailPage')),
  vendor: React.lazy(() => import('@/components/common/ModelDetailPage')),
  manufacturer: React.lazy(() => import('@/components/common/ModelDetailPage')),
  employee: React.lazy(() => import('@/components/common/ModelDetailPage')),
  rep: React.lazy(() => import('@/components/common/ModelDetailPage')),
  // Products
  item: React.lazy(() => import('@/components/common/ModelDetailPage')),
  // Transactions
  quote: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  order: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  invoice: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  purchase: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  // Hand-built, not the layout form (Bill, 2026-09-26: no JSON forms in workorder).
  workorder: React.lazy(() => import('@/apps/transactions/pages/WorkOrderWindow')),
  receipt: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  requisition: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  cash: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
};

/** A non-staff login's form for a model with no form component of its own: the layout form
 *  (config.layout.form) — never the field grid, which only staff see (Bill, 2026-11-01, an always
 *  rule). Until one form (readmes/101-one-form.md) gives every model the same form. */
export const FORM_FOR_ANY_MODEL = React.lazy(() => import('@/components/common/ModelDetailPage'));

