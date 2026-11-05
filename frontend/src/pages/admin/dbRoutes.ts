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
  contact: React.lazy(() => import('@/components/common/DbForm')),
  action: React.lazy(() => import('@/components/common/DbForm')),
  touch: React.lazy(() => import('@/components/common/DbForm')),
  report: React.lazy(() => import('@/apps/core/models/report/pages/ReportDisplay')),
  // Orgs
  customer: React.lazy(() => import('@/components/common/DbForm')),
  vendor: React.lazy(() => import('@/components/common/DbForm')),
  manufacturer: React.lazy(() => import('@/components/common/DbForm')),
  employee: React.lazy(() => import('@/components/common/DbForm')),
  rep: React.lazy(() => import('@/components/common/DbForm')),
  // Products
  item: React.lazy(() => import('@/components/common/DbForm')),
  // Transactions
  quote: React.lazy(() => import('@/components/common/DbForm')),
  order: React.lazy(() => import('@/components/common/DbForm')),
  invoice: React.lazy(() => import('@/components/common/DbForm')),
  purchase: React.lazy(() => import('@/components/common/DbForm')),
  // Hand-built, not the layout form (Bill, 2026-09-26: no JSON forms in workorder).
  workorder: React.lazy(() => import('@/apps/transactions/pages/WorkOrderWindow')),
  receipt: React.lazy(() => import('@/components/common/DbForm')),
  requisition: React.lazy(() => import('@/components/common/DbForm')),
  cash: React.lazy(() => import('@/components/common/DbForm')),
};

/** A non-staff login's form for a model not listed above: db.form, the one layout form — never
 *  the field grid, which only staff see (Bill, 2026-11-01, an always rule). */
export const FORM_FOR_ANY_MODEL = React.lazy(() => import('@/components/common/DbForm'));

