/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
  export class PageRoutes {
    static readonly productsItemDetail: string = "/products/item/detail/:id";
  static readonly login: string = "/";
  static readonly register: string = "/register";
  static readonly dashboard: string = "/dashboard";
  static readonly profile: string = "/profile";
  static readonly profile2: string = "/profile2";

  static readonly actionList: string = "/core/actions/list";
  static readonly actionDetail: string = "/core/actions/detail/:id?";
  static readonly actionsCallReportAdd: string = "/actions/call-reports/add";
  static readonly actionsCallReportDetail: string = "/actions/call-reports/:id";
  static readonly actionsServiceAdd: string = "/actions/services/add";
  static readonly actionsServiceDetail: string = "/actions/services/:id";
  static readonly actionsTaskMarkerAdd: string = "/actions/task-markers/add";
  static readonly actionsTaskMarkerDetail: string = "/actions/task-markers/:id";

  static readonly customerList: string = "/org/customer/list";
  static readonly customerDetail: string = "/org/customer/detail";
  static readonly customerAdd: string = "/org/customer/add";
  static readonly customerEdit: string = "/org/customer/edit";
  static readonly employeeList: string = "/org/employee/list";
  static readonly manufacturerList: string = "/org/manufacturer/list";
    static readonly manufacturerDetail: string = "/org/manufacturer/detail";
    static readonly manufacturerAdd: string = "/org/manufacturer/add";
    static readonly manufacturerEdit: string = "/org/manufacturer/edit";
  static readonly organizationList: string = "/org/organization/list";
  static readonly repList: string = "/org/rep/list";
    static readonly repDetail: string = "/org/rep/detail";
    static readonly repAdd: string = "/org/rep/add";
    static readonly repEdit: string = "/org/rep/edit";
  static readonly vendorList: string = "/org/vendor/list";

  static readonly test: string = "/test";
  static readonly adminWorkbench: string = "/admin-wb";
  static readonly jsonViewer: string = "/json-viewer";
  static readonly jsonTree: string = "/json-tree";
  static readonly commerceDashboard: string = "/commerce";
  static readonly accountingDashboard: string = "/accounting";
  static readonly aliceTraining: string = "/training";
  static readonly modelWorkbench: string = "/model-workbench";
  static readonly whitelist: string = "/whitelist";
  static readonly docs: string = "/docs";
  static readonly notionTracker: string = "/notion-tracker";
  static readonly kanbanBoard: string = "/kanban";
  static readonly kanbanBoardData: string = "/kanban-board-data";
  static readonly gantt: string = "/gantt";
  // Deprecated gantt routes - redirect to /gantt
  static readonly kanbanGantt: string = "/kanban-gantt";
  static readonly svarGantt: string = "/svar-gantt";
  static readonly multiProjectGantt: string = "/multi-project-gantt";

  // Products & Transactions
  static readonly products: string = "/products";
  static readonly productsBillOfMaterialList: string =
    "/products/bill-of-material/list";
  static readonly productsCatalogList: string = "/products/catalog/list";
  static readonly productsFlowList: string = "/products/flow/list";
  static readonly productsItemList: string = "/products/item/list";
  static readonly productsItemXrefList: string = "/products/item-xref/list";
  static readonly productsMatricsList: string = "/products/matrics/list";
  static readonly productsOrgItemList: string = "/products/org-item/list";
  static readonly productsSerialList: string = "/products/serial/list";
  static readonly productsServiceList: string = "/products/service/list";
  static readonly productsSpecificationList: string =
    "/products/specification/list";
  static readonly productsUsageList: string = "/products/usage/list";
  static readonly productsVariantList: string = "/products/variant/list";
  static readonly productsWarehouseList: string = "/products/warehouse/list";

  static readonly transactionsOrderList: string =
    "/transactions/order/list";
  static readonly transactionsOrderDetail: string =
    "/transactions/order/detail/:id?";

  static readonly transactionsInvoiceList: string =
    "/transactions/invoice/list";
  static readonly transactionsInvoiceDetail: string =
    "/transactions/invoice/detail/:id?";
  static readonly transactionsApplyPayments: string =
    "/transactions/apply-payments";

  static readonly transactionsPaymentList: string =
    "/transactions/payment/list";
  static readonly transactionsPaymentDetail: string =
    "/transactions/payment/detail/:id?";

  static readonly transactionsPurchaseList: string =
    "/transactions/purchase/list";
  static readonly transactionsPurchaseDetail: string =
    "/transactions/purchase/detail/:id?";

  static readonly transactionsProposalList: string =
    "/transactions/proposal/list";
  static readonly transactionsProposalDetail: string =
    "/transactions/proposal/detail/:id?";

  static readonly transactionsWorkOrderList: string =
    "/transactions/work-order/list";
  static readonly transactionsWorkOrderDetail: string =
    "/transactions/work-order/detail/:id?";

  static readonly transactionsReceiptList: string =
    "/transactions/receipt/list";
  static readonly transactionsReceiptDetail: string =
    "/transactions/receipt/detail/:id?";

  static readonly transactionsAdjustmentList: string =
    "/transactions/adjustment/list";
  static readonly transactionsAdjustmentDetail: string =
    "/transactions/adjustment/detail/:id?";

  // Accounts
  static readonly auditList: string = "/accounts/audit/list";
  static readonly auditDetail: string = "/accounts/audit/detail/:id?";
  static readonly currencyList: string = "/accounts/currency/list";
  static readonly currencyDetail: string = "/accounts/currency/detail/:id?";
  static readonly exchangeRateList: string = "/accounts/exchange-rate/list";

  static readonly exchangeRateDetail: string =
    "/accounts/exchange-rate/detail/:id?";
  static readonly exchangeTransactionList: string =
    "/accounts/exchange-transaction/list";
  static readonly exchangeTransactionDetail: string =
    "/accounts/exchange-transaction/detail/:id?";
  static readonly glAccountList: string = "/accounts/gl-account/list";
  static readonly glAccountDetail: string = "/accounts/gl-account/detail/:id?";
  static readonly glJournalList: string = "/accounts/gl-journal/list";
  static readonly glJournalDetail: string = "/accounts/gl-journal/detail/:id?";
  static readonly ledgerList: string = "/accounts/ledger/list";
  static readonly receivableList: string = "/accounts/receivable/list";
  static readonly tallySummaryList: string = "/accounts/tally-summary/list";
  static readonly salesDimensionTallyList: string =
    "/accounts/tally-sales/list";
  static readonly inventoryUsageTallyList: string =
    "/accounts/tally-inventory/list";
  static readonly tallyRegistryList: string = "/accounts/tally-registry/list";
  static readonly taxJurisdictionList: string =
    "/accounts/tax-jurisdiction/list";
  static readonly termList: string = "/accounts/term/list";

  // Communications
  static readonly commDomainList: string = "/communications/domain/list";
  static readonly commDomainDetail: string =
    "/communications/domain/detail/:id?";
  static readonly commEmailList: string = "/communications/email/list";
  static readonly commEmailDetail: string = "/communications/email/detail/:id?";
  static readonly commAddressList: string = "/communications/address/list";
  static readonly commAddressDetail: string =
    "/communications/address/detail/:id?";
  static readonly commPhoneList: string = "/communications/phone/list";
  static readonly commPhoneDetail: string = "/communications/phone/detail/:id?";

  // Core
  static readonly coreContactList: string = "/core/contact/list";
  static readonly coreContactDetail: string = "/core/contact/detail/:id?";
  static readonly coreReportList: string = "/core/report/list";
  static readonly coreReportDetail: string = "/core/report/detail/:id?";
  static readonly coreSettingList: string = "/core/setting/list";
  static readonly coreSettingDetail: string = "/core/setting/detail/:id?";
  static readonly coreTemplateList: string = "/core/template/list";
  static readonly coreTemplateDetail: string = "/core/template/detail/:id?";
  static readonly coreApiLogList: string = "/core/api-log/list";
  static readonly coreUserActivityDashboard: string = "/core/user-activity";
  static readonly coreTeamDashboard: string = "/core/team-dashboard";

  // Docs
  static readonly documentList: string = "/docs/document/list";
  static readonly documentDetail: string = "/docs/document/detail/:id?";
  static readonly linkageEntryList: string = "/docs/linkage-entry/list";
  static readonly questionAnswerList: string = "/docs/question-answer/list";
  static readonly tagList: string = "/docs/tag/list";
}
