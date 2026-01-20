import React from "react";
import { PageRoutes } from "./Routes";
import {
  CustomerList,
  EmployeeList,
  ManufacturerList,
  OrganizationsList,
  RepList,
  VendorList,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  KanbanGanttPage,
  NotionTrackerPage,
  SvarGanttPage,
  MultiProjectGanttPage,
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
  AppLocationList,
  AppLocationDetail,
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
  LinkageList,
  LinkageIndexList,
  QuestionAnswerList,
  TagList,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
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
import SalesOrderDetail from "../apps/transactions/models/sales_order/pages/SalesOrderDetail";
import InvoiceList from "../apps/transactions/models/invoice/pages/InvoiceList";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import PurchaseOrderDetail from "../apps/transactions/models/purchase_order/pages/PurchaseOrderDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import PurchaseOrderList from "../apps/transactions/models/purchase_order/pages/PurchaseOrderList";
import SalesOrderList from "../apps/transactions/models/sales_order/pages/SalesOrderList";
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
  { path: PageRoutes.commLocationList, element: <AppLocationList /> },
  { path: PageRoutes.commLocationDetail, element: <AppLocationDetail /> },
  { path: PageRoutes.commPhoneList, element: <AppPhoneList /> },
  { path: PageRoutes.commPhoneDetail, element: <AppPhoneDetail /> },
  { path: PageRoutes.notionTracker, element: <NotionTrackerPage /> },
  { path: PageRoutes.kanbanBoard, element: <KanbanBoardPage /> },
  { path: PageRoutes.kanbanBoardData, element: <KanbanBoardDataPage /> },
  { path: PageRoutes.kanbanGantt, element: <KanbanGanttPage /> },
  { path: PageRoutes.svarGantt, element: <SvarGanttPage /> },
  { path: PageRoutes.multiProjectGantt, element: <MultiProjectGanttPage /> },
  { path: PageRoutes.actionList, element: <ActionListPage /> },
  { path: PageRoutes.actionDetail, element: <ActionDetail /> },
  { path: PageRoutes.adminWorkbench, element: <AdminWorkbench /> },
  { path: PageRoutes.modelWorkbench, element: <AllModelsWorkbench /> },
  { path: PageRoutes.whitelist, element: <WhitelistTester /> },
  { path: PageRoutes.docs, element: <DocumentIndex /> },
  { path: PageRoutes.documentList, element: <DocumentList /> },
  { path: PageRoutes.documentDetail, element: <DocumentDetail /> },
  { path: PageRoutes.linkageList, element: <LinkageList /> },
  { path: PageRoutes.linkageIndexList, element: <LinkageIndexList /> },
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
  { path: PageRoutes.transactionsSalesOrderList, element: <SalesOrderList /> },
  { path: PageRoutes.transactionsSalesOrderDetail, element: <SalesOrderDetail /> },
  { path: PageRoutes.transactionsInvoiceList, element: <InvoiceList /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <InvoiceDetail /> },
  { path: PageRoutes.transactionsPurchaseOrderList, element: <PurchaseOrderList /> },
  { path: PageRoutes.transactionsPurchaseOrderDetail, element: <PurchaseOrderDetail /> },
  { path: PageRoutes.transactionsProposalList, element: <ProposalList /> },
  { path: PageRoutes.transactionsProposalDetail, element: <ProposalDetail /> },
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
  { path: "/core/audit/list", element: <Placeholder title="Core Audit" /> },
  { path: "/core/notification/list", element: <Placeholder title="Notifications" /> },
  { path: "/core/pending/list", element: <Placeholder title="Pending Items" /> },
];

export const resolveWindowElement = (path: string) => {
  const match = protectedRoutesConfig.find((r) => {
    if (r.path?.includes(":")) {
      const base = r.path.split(":")[0];
      return path.startsWith(base);
    }
    return r.path === path;
  });
  return match?.element ?? null;
};