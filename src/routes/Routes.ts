export class PageRoutes {
  static readonly login: string = "/";
  static readonly register: string = "/register";
  static readonly dashboard: string = "/dashboard";
  static readonly profile: string = "/profile";
  static readonly profile2: string = "/profile2";

  static readonly actionList: string = "/action-list";
  static readonly actionAdd: string = "/action-add";
  static readonly actionsCallReportAdd: string = "/actions/call-reports/add";
  static readonly actionsCallReportDetail: string = "/actions/call-reports/:id";
  static readonly actionsServiceAdd: string = "/actions/services/add";
  static readonly actionsServiceDetail: string = "/actions/services/:id";
  static readonly actionsTaskMarkerAdd: string = "/actions/task-markers/add";
  static readonly actionsTaskMarkerDetail: string = "/actions/task-markers/:id";

  static readonly contactList: string = "/core/contact/list";

  static readonly customerDetail: string = "/contacts/:id";
  static readonly customerAdd: string = "/contacts/add";

  static readonly settingAdd: string = "/setting-add";
  static readonly settingList: string = "/setting-list";

  static readonly domainList: string = "/communications/domain/list";
  static readonly emailList: string = "/communications/email/list";
  static readonly locationList: string = "/communications/location/list";
  static readonly phoneList: string = "/communications/phone/list";

  static readonly calendar: string = "/calendar";
  static readonly formElements: string = "/form-elements";
  static readonly basicTables: string = "/basic-models";
  static readonly test: string = "/test";
  static readonly adminWorkbench: string = "/admin-wb";
  static readonly whitelist: string = "/whitelist";
  static readonly docs: string = "/docs";
  static readonly notionTracker: string = "/notion-tracker";
  static readonly kanbanBoard: string = "/kanban-board";
  static readonly kanbanBoardData: string = "/kanban-board-data";
  static readonly kanbanGantt: string = "/kanban-gantt";
  static readonly svarGantt: string = "/svar-gantt";

  // Products & Transactions
  static readonly products: string = "/products";

  static readonly transactionsOrders: string = "/transactions/orders";
  static readonly transactionsOrderDetail: string = "/transactions/orders/:id";
  static readonly transactionsOrderDetailTest: string =
    "/transactions/orders-test";

  static readonly transactionsInvoices: string = "/transactions/invoices";
  static readonly transactionsInvoiceDetail: string =
    "/transactions/invoices/:id";

  static readonly transactionsPurchaseOrders: string =
    "/transactions/purchase-orders";
  static readonly transactionsPurchaseOrderDetail: string =
    "/transactions/purchase-orders/:id";

  static readonly transactionsProposals: string = "/transactions/proposals";
  static readonly transactionsProposalDetail: string =
    "/transactions/proposals/:id";

  // Accounts
  static readonly auditList: string = "/accounts/audit/list";
  static readonly auditDetail: string = "/accounts/audit/detail/:id?";
  static readonly auditDisplay: string = "/accounts/audit/display/:id?";
  static readonly currencyList: string = "/accounts/currency/list";
  static readonly currencyDetail: string = "/accounts/currency/detail/:id?";
  static readonly currencyDisplay: string = "/accounts/currency/display/:id?";
  static readonly exchangeRateList: string = "/accounts/exchange-rate/list";

  // static readonly exchangeRateDisplay: string =
  //   "/accounts/exchange-rate/display/:id?";
  // static readonly exchangeTransactionList: string =
  //   "/accounts/exchange-transaction/list";
  // static readonly exchangeTransactionDisplay: string =
  //   "/accounts/exchange-transaction/display/:id?";

  static readonly exchangeRateDetail: string =
    "/accounts/exchange-rate/detail/:id?";
  static readonly exchangeRateDisplay: string =
    "/accounts/exchange-rate/display/:id?";
  static readonly exchangeTransactionList: string =
    "/accounts/exchange-transaction/list";
  static readonly exchangeTransactionDetail: string =
    "/accounts/exchange-transaction/detail/:id?";
  static readonly exchangeTransactionDisplay: string =
    "/accounts/exchange-transaction/display/:id?";
  static readonly glAccountList: string = "/accounts/gl-account/list";
  static readonly glAccountDetail: string = "/accounts/gl-account/detail/:id?";
  static readonly glJournalList: string = "/accounts/gl-journal/list";
  static readonly glJournalDetail: string = "/accounts/gl-journal/detail/:id?";
  static readonly glJournalDisplay: string =
    "/accounts/gl-journal/display/:id?";
  static readonly ledgerList: string = "/accounts/ledger/list";
  static readonly ledgerDisplay: string = "/accounts/ledger/display/:id?";
  static readonly taxJurisdictionList: string =
    "/accounts/tax-jurisdiction/list";
  static readonly taxJurisdictionDisplay: string =
    "/accounts/tax-jurisdiction/display/:id?";
  static readonly termList: string = "/accounts/term/list";
  static readonly termDisplay: string = "/accounts/term/display/:id?";

  // Communications
  static readonly commDomainList: string = "/communications/domain/list";
  static readonly commDomainDetail: string =
    "/communications/domain/detail/:id?";
  static readonly commEmailList: string = "/communications/email/list";
  static readonly commEmailDetail: string = "/communications/email/detail/:id?";
  static readonly commLocationList: string = "/communications/location/list";
  static readonly commLocationDetail: string =
    "/communications/location/detail/:id?";
  static readonly commPhoneList: string = "/communications/phone/list";
  static readonly commPhoneDetail: string = "/communications/phone/detail/:id?";

  // Core
  static readonly coreActionList: string = "/core/action/list";
  static readonly coreContactList: string = "/core/contact/list";
  static readonly coreContactDetail: string = "/core/contact/detail/:id?";
  static readonly coreReportList: string = "/core/report/list";
  static readonly coreReportDetail: string = "/core/report/detail/:id?";
  static readonly coreReportDisplay: string = "/core/report/display/:id?";
  static readonly coreSettingList: string = "/core/setting/list";
  static readonly coreSettingDetail: string = "/core/setting/detail/:id?";
  static readonly coreSettingDisplay: string = "/core/setting/display/:id?";
  static readonly coreTemplateList: string = "/core/template/list";
  static readonly coreTemplateDetail: string = "/core/template/detail/:id?";
  static readonly coreTemplateDisplay: string = "/core/template/display/:id?";

  // Docs
  static readonly documentList: string = "/docs/document/list";
  static readonly documentDetail: string = "/docs/document/detail/:id?";
  static readonly documentDisplay: string = "/docs/document/display/:id?";
  static readonly linkageList: string = "/docs/linkage/list";
  static readonly linkageDisplay: string = "/docs/linkage/display/:id?";
  static readonly linkageIndexList: string = "/docs/linkage-index/list";
  static readonly linkageIndexDisplay: string =
    "/docs/linkage-index/display/:id?";
  static readonly questionAnswerList: string = "/docs/question-answer/list";
  static readonly questionAnswerDisplay: string =
    "/docs/question-answer/display/:id?";
  static readonly tagList: string = "/docs/tag/list";
  static readonly tagDisplay: string = "/docs/tag/display/:id?";
}
