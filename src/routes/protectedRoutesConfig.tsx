import React from "react";
import { Navigate } from "react-router";
import { PageRoutes } from "./Routes";
// import { CustomerDashboard as CustomerDashboardPage } from '../apps/orgs/models/customer/pages/CustomerDashboard';
import {
  CustomerList,
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  EmployeeList,
  ManufacturerList,
  OrganizationsList,
  RepList,
  VendorList,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  NotionTrackerPage,
  UnifiedGanttPage,
  UserProfiles,
  AuditList,
  AuditDetail,
  CurrencyList,
  CurrencyDetail,
  ExchangeRateList,
  ExchangeRateDetail,
  ExchangeTransactionList,
  ExchangeTransactionDetail,
  GLAccountList,
  GLAccountDetail,
  GLJournalList,
  GLJournalDetail,
  LedgerList,
  TaxJurisdictionList,
  TermList,
  DomainList,
  DomainDetail,
  EmailList,
  EmailDetail,
  AppAddressList,
  AppAddressDetail,
  AppPhoneList,
  AppPhoneDetail,
  CoreContactList,
  CoreContactDetail,
  CoreReportList,
  CoreReportDetail,
  CoreSettingList,
  CoreSettingDetail,
  CoreTemplateList,
  CoreTemplateDetail,
  DocumentList,
  DocumentDetail,
  LinkageEntryList,
  QuestionAnswerList,
  TagList,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import DetailReview from "../pages/admin/DetailReview";
import WhitelistTester from "../pages/tools/WhitelistTester";
import BillOfMaterialList from "../apps/products/models/bill_of_material/pages/BillOfMaterialList";
import CatalogList from "../apps/products/models/catalog/pages/CatalogList";
import FlowList from "../apps/products/models/flow/pages/FlowList";
import ItemList from "../apps/products/models/item/pages/ItemList";
import ItemXrefList from "../apps/products/models/item_xref/pages/ItemXrefList";
import MatricsList from "../apps/products/models/matrics/pages/MatricsList";
import OrgItemList from "../apps/products/models/org_item/pages/OrgItemList";
import SerialList from "../apps/products/models/serial/pages/SerialList";
import ServiceList from "../apps/products/models/service/pages/ServiceList";
import SpecificationList from "../apps/products/models/specification/pages/SpecificationList";
import UsageList from "../apps/products/models/usage/pages/UsageList";
import VariantList from "../apps/products/models/variant/pages/VariantList";
import WarehouseList from "../apps/products/models/warehouse/pages/WarehouseList";
import OrderDetail from "../apps/transactions/models/order/pages/OrderDetail";
import InvoiceList from "../apps/transactions/models/invoice/pages/InvoiceList";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import PurchaseDetail from "../apps/transactions/models/purchase/pages/PurchaseDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import PurchaseList from "../apps/transactions/models/purchase/pages/PurchaseList";
import OrderList from "../apps/transactions/models/order/pages/OrderList";
import WorkorderList from "../apps/transactions/models/workorder/pages/WorkorderList";
import WorkorderDetail from "../apps/transactions/models/workorder/pages/WorkorderDetail";
import ReceiptList from "../apps/transactions/models/receipt/pages/ReceiptList";
import ReceiptDetail from "../apps/transactions/models/receipt/pages/ReceiptDetail";
import InventoryAdjustmentList from "../apps/transactions/models/inventory_adjustment/pages/InventoryAdjustmentList";
import DocumentIndex from "../apps/docs/models/document/pages/DocumentIndex";
import ActionListPage from "../apps/core/models/action/pages/ActionList";
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
import APILogList from "../apps/core/models/api_log/pages/APILogList";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import Placeholder from "../pages/Placeholder";

export const protectedRoutesConfig = [
  { path: PageRoutes.dashboard, element: <Home /> },
  { path: PageRoutes.profile, element: <UserProfiles /> },
  { path: PageRoutes.coreContactList, element: <CoreContactList /> },
  { path: PageRoutes.coreContactDetail, element: <CoreContactDetail /> },
  { path: PageRoutes.customerList, element: <CustomerList /> },
  { path: `${PageRoutes.customerDetail}/:id`, element: <CustomerDetailPage /> },
  { path: PageRoutes.customerAdd, element: <CustomerAddPage /> },
  { path: `${PageRoutes.customerEdit}/:id`, element: <CustomerEditPage /> },
  { path: PageRoutes.employeeList, element: <EmployeeList /> },
  { path: PageRoutes.manufacturerList, element: <ManufacturerList /> },
  { path: PageRoutes.organizationList, element: <OrganizationsList /> },
  { path: PageRoutes.repList, element: <RepList /> },
  { path: PageRoutes.vendorList, element: <VendorList /> },
  { path: PageRoutes.coreSettingList, element: <CoreSettingList /> },
  { path: PageRoutes.coreSettingDetail, element: <CoreSettingDetail /> },
  { path: PageRoutes.coreReportList, element: <CoreReportList /> },
  { path: PageRoutes.coreReportDetail, element: <CoreReportDetail /> },
  { path: PageRoutes.coreTemplateList, element: <CoreTemplateList /> },
  { path: PageRoutes.coreTemplateDetail, element: <CoreTemplateDetail /> },
  { path: PageRoutes.coreApiLogList, element: <APILogList /> },
  { path: PageRoutes.commDomainList, element: <DomainList /> },
  { path: PageRoutes.commDomainDetail, element: <DomainDetail /> },
  { path: PageRoutes.commEmailList, element: <EmailList /> },
  { path: PageRoutes.commEmailDetail, element: <EmailDetail /> },
  { path: PageRoutes.commAddressList, element: <AppAddressList /> },
  { path: PageRoutes.commAddressDetail, element: <AppAddressDetail /> },
  { path: PageRoutes.commPhoneList, element: <AppPhoneList /> },
  { path: PageRoutes.commPhoneDetail, element: <AppPhoneDetail /> },
  { path: PageRoutes.notionTracker, element: <NotionTrackerPage /> },
  { path: PageRoutes.kanbanBoard, element: <KanbanBoardPage /> },
  { path: PageRoutes.kanbanBoardData, element: <KanbanBoardDataPage /> },
  // Unified Gantt - single/multi-project support
  { path: PageRoutes.gantt, element: <UnifiedGanttPage /> },
  // Deprecated routes - redirect to unified gantt
  { path: PageRoutes.kanbanGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.svarGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.multiProjectGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.actionList, element: <ActionListPage /> },
  { path: PageRoutes.actionDetail, element: <ActionDetail /> },
  { path: PageRoutes.adminWorkbench, element: <AdminWorkbench /> },
  { path: PageRoutes.detailReview, element: <DetailReview /> },
  { path: PageRoutes.modelWorkbench, element: <AllModelsWorkbench /> },
  { path: PageRoutes.whitelist, element: <WhitelistTester /> },
  { path: PageRoutes.docs, element: <DocumentIndex /> },
  { path: PageRoutes.documentList, element: <DocumentList /> },
  { path: PageRoutes.documentDetail, element: <DocumentDetail /> },
  { path: PageRoutes.linkageEntryList, element: <LinkageEntryList /> },
  { path: PageRoutes.questionAnswerList, element: <QuestionAnswerList /> },
  { path: PageRoutes.tagList, element: <TagList /> },
  { path: PageRoutes.products, element: <ItemList /> },
  { path: PageRoutes.productsBillOfMaterialList, element: <BillOfMaterialList /> },
  { path: PageRoutes.productsCatalogList, element: <CatalogList /> },
  { path: PageRoutes.productsFlowList, element: <FlowList /> },
  { path: PageRoutes.productsItemList, element: <ItemList /> },
  { path: PageRoutes.productsItemXrefList, element: <ItemXrefList /> },
  { path: PageRoutes.productsMatricsList, element: <MatricsList /> },
  { path: PageRoutes.productsOrgItemList, element: <OrgItemList /> },
  { path: PageRoutes.productsSerialList, element: <SerialList /> },
  { path: PageRoutes.productsServiceList, element: <ServiceList /> },
  { path: PageRoutes.productsSpecificationList, element: <SpecificationList /> },
  { path: PageRoutes.productsUsageList, element: <UsageList /> },
  { path: PageRoutes.productsVariantList, element: <VariantList /> },
  { path: PageRoutes.productsWarehouseList, element: <WarehouseList /> },
  { path: PageRoutes.transactionsOrderList, element: <OrderList /> },
  { path: PageRoutes.transactionsOrderDetail, element: <OrderDetail /> },
  { path: PageRoutes.transactionsInvoiceList, element: <InvoiceList /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <InvoiceDetail /> },
  { path: PageRoutes.transactionsApplyPayments, element: <ApplyPayments /> },
  { path: PageRoutes.transactionsPurchaseList, element: <PurchaseList /> },
  { path: PageRoutes.transactionsPurchaseDetail, element: <PurchaseDetail /> },
  { path: PageRoutes.transactionsProposalList, element: <ProposalList /> },
  { path: PageRoutes.transactionsProposalDetail, element: <ProposalDetail /> },
  { path: PageRoutes.transactionsWorkOrderList, element: <WorkorderList /> },
  { path: PageRoutes.transactionsWorkOrderDetail, element: <WorkorderDetail /> },
  { path: PageRoutes.transactionsReceiptList, element: <ReceiptList /> },
  { path: PageRoutes.transactionsReceiptDetail, element: <ReceiptDetail /> },
  { path: PageRoutes.transactionsAdjustmentList, element: <InventoryAdjustmentList /> },
  { path: PageRoutes.auditList, element: <AuditList /> },
  { path: PageRoutes.auditDetail, element: <AuditDetail /> },
  { path: PageRoutes.currencyList, element: <CurrencyList /> },
  { path: PageRoutes.currencyDetail, element: <CurrencyDetail /> },
  { path: PageRoutes.exchangeRateList, element: <ExchangeRateList /> },
  { path: PageRoutes.exchangeRateDetail, element: <ExchangeRateDetail /> },
  { path: PageRoutes.exchangeTransactionList, element: <ExchangeTransactionList /> },
  { path: PageRoutes.exchangeTransactionDetail, element: <ExchangeTransactionDetail /> },
  { path: PageRoutes.glAccountList, element: <GLAccountList /> },
  { path: PageRoutes.glAccountDetail, element: <GLAccountDetail /> },
  { path: PageRoutes.glJournalList, element: <GLJournalList /> },
  { path: PageRoutes.glJournalDetail, element: <GLJournalDetail /> },
  { path: PageRoutes.ledgerList, element: <LedgerList /> },
  { path: PageRoutes.taxJurisdictionList, element: <TaxJurisdictionList /> },
  { path: PageRoutes.termList, element: <TermList /> },
  // { path: "/org/customer/dashboard/:customerId", element: <CustomerDashboardPage /> },
  { path: "/core/audit/list", element: <Placeholder title="Core Audit" /> },
  { path: "/core/notification/list", element: <Placeholder title="Notifications" /> },
  { path: "/core/pending/list", element: <Placeholder title="Pending Items" /> },
];

export const resolveWindowElement = (path: string) => {
  // Strip query string for matching purposes
  const cleanPath = path.split("?")[0];
  const match = protectedRoutesConfig.find((r) => {
    if (r.path?.includes(":")) {
      const base = r.path.split(":")[0];
      // Match with or without trailing slash (e.g. /detail vs /detail/)
      const baseNoSlash = base.endsWith("/") ? base.slice(0, -1) : base;
      return cleanPath === baseNoSlash || cleanPath.startsWith(base);
    }
    return r.path === cleanPath;
  });
  return match?.element ?? null;
};