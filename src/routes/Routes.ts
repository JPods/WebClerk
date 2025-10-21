export class PageRoutes {  

  static readonly login: string = "/";  
  static readonly register: string = "/register";  
  static readonly dashboard: string = "/dashboard";
  static readonly profile: string = "/profile";
  static readonly profile2: string = "/profile2";

  static readonly actionList: string = "/action-list";
  static readonly actionAdd: string = "/action-add";

  static readonly contactAdd: string = "/contact-add";
  static readonly contactList: string = "/contact-list";

  static readonly settingAdd: string = "/setting-add";
  static readonly settingList: string = "/setting-list";

  static readonly domainAdd: string = "/domain-add";
  static readonly domainList: string = "/domain-list";

  static readonly calendar: string = "/calendar";
  static readonly formElements: string = "/form-elements";
  static readonly basicTables: string = "/basic-models";
  static readonly test: string = "/test";
  static readonly adminWorkbench: string = "/admin-wb";
  static readonly whitelist: string = "/whitelist";
  static readonly docs: string = "/docs";
  static readonly notionTracker: string = "/notion-tracker";
  static readonly kanbanBoard: string = "/kanban-board";
  static readonly kanbanGantt: string = "/kanban-gantt";

  // Products & Transactions
  static readonly products: string = "/products";

  static readonly transactionsOrders: string = "/transactions/orders";
  static readonly transactionsOrderDetail: string = "/transactions/orders/:id";

  static readonly transactionsInvoices: string = "/transactions/invoices";
  static readonly transactionsInvoiceDetail: string = "/transactions/invoices/:id";

  static readonly transactionsPurchaseOrders: string = "/transactions/purchase-orders";
  static readonly transactionsPurchaseOrderDetail: string = "/transactions/purchase-orders/:id";

  static readonly transactionsProposals: string = "/transactions/proposals";
  static readonly transactionsProposalDetail: string = "/transactions/proposals/:id";
}
