/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser | WhoCreated: Bill+Claude */
import React from 'react';

/** Maps DataBrowser model name → .tsx detail route (used for double-click new-tab). */
export const APP_DETAIL_ROUTES: Record<string, string> = {
  order: '/order',
  invoice: '/invoice',
  proposal: '/proposal',
  purchase: '/purchase',
  workorder: '/work_order',
  work_order: '/work_order',
  receipt: '/receipt',
  requisition: '/requisition',
  payment: '/payment',
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
  contact: React.lazy(() => import('@/apps/core/models/contact/pages/ContactDetailJson')),
  report: React.lazy(() => import('@/apps/core/models/report/pages/ReportDisplay')),
  // Orgs
  customer: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  vendor: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  manufacturer: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  employee: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  rep: React.lazy(() => import('@/apps/orgs/components/OrgDetail.json')),
  // Products
  item: React.lazy(() => import('@/apps/products/pages/ItemDetailJson')),
  serial_log: React.lazy(() => import('@/apps/products/models/serial/pages/SerialDisplay')),
  // Transactions
  proposal: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  order: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  invoice: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  purchase: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  work_order: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  receipt: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  requisition: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  payment: React.lazy(() => import('@/apps/transactions/components/TransactionDetail')),
  // Communications — Display pages not yet built; fall through to Admin mode
  // Docs
  document: React.lazy(() => import('@/apps/docs/models/document/pages/DocumentDisplay')),
  question_answer: React.lazy(() => import('@/apps/docs/models/question_answer/pages/QuestionAnswerDisplay')),
};
