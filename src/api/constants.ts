// API endpoint constants extracted and translated from vue2020
// Base URLs
export const BASE_URL = "http://localhost:8000"; // backend server with port
export const AUTH_PATH = `${BASE_URL}/WCapi/`;
export const CUSTOMERS_PATH = `${BASE_URL}/api/Customer/`;
export const ORDERS_PATH = `${BASE_URL}/api/Order/`;
export const ORDER_LINES_PATH = `${BASE_URL}/api/orderLine/`;
export const PROPOSALS_PATH = `${BASE_URL}/api/proposal/`;
export const PROPOSAL_LINES_PATH = `${BASE_URL}/api/proposalLine/`;
export const INVOICES_PATH = `${BASE_URL}/api/invoice/`;
export const INVOICE_LINES_PATH = `${BASE_URL}/api/invoiceLine/`;
export const SERVICES_PATH = `${BASE_URL}/api/service/`;
export const QA_PATH = `${BASE_URL}/api/qa/`;
export const ITEMS_PATH = `${BASE_URL}/api/item/`;
export const TASKS_PATH = `${BASE_URL}/api/task/`;
export const KANBAN_PATH = `${BASE_URL}/api/kanban/`;
export const ADMIN_PATH = `${BASE_URL}/api/Admin/`;

// API Endpoints
export const API_ENDPOINTS = {
  auth: {
    login: `${AUTH_PATH}login/`,
    logout: `${AUTH_PATH}logout/`,
    signup: `${AUTH_PATH}signup/`,
    verify: `${AUTH_PATH}verify-email/`,
  },
  customers: {
    getActionBy: `${CUSTOMERS_PATH}getActionBy`,
    getByKeyTags: `${CUSTOMERS_PATH}GetByKeyTags`,
    getByCompany: `${CUSTOMERS_PATH}GetBy/Company`,
    getQA: `${CUSTOMERS_PATH}getQA`,
    getById: `${CUSTOMERS_PATH}get`,
    save: `${CUSTOMERS_PATH}save`,
  },
  orders: {
    getById: `${ORDERS_PATH}get`,
    getActionBy: `${ORDERS_PATH}getActionBy`,
    getByCustomer: `${ORDERS_PATH}getByCustomer`,
    getByNum: `${ORDERS_PATH}getBy/OrderNum`,
    getByDate: `${ORDERS_PATH}getBy/ActionDate`,
    getLines: `${ORDERS_PATH}getLines`,
    save: `${ORDERS_PATH}save`,
    getQA: `${ORDERS_PATH}getQA`,
    makeInvoice: `${ORDERS_PATH}makeInvoice`,
  },
  proposals: {
    getById: `${PROPOSALS_PATH}get`,
    getActionBy: `${PROPOSALS_PATH}getActionBy`,
    getByCustomer: `${PROPOSALS_PATH}getByCustomer`,
    getLines: `${PROPOSALS_PATH}getLines`,
    save: `${PROPOSALS_PATH}save`,
    getQA: `${PROPOSALS_PATH}getQA`,
    getCloneChoiceList: `${PROPOSALS_PATH}CloneChoiceList`,
    getCloneables: `${PROPOSALS_PATH}GetCloneList`,
    clone: `${PROPOSALS_PATH}Clone`,
    getByNum: `${PROPOSALS_PATH}getBy/ProposalNum`,
    makeOrder: `${PROPOSALS_PATH}makeOrder`,
  },
  invoices: {
    getById: `${INVOICES_PATH}get`,
    getActionBy: `${INVOICES_PATH}getActionBy`,
    getByCustomer: `${INVOICES_PATH}getByCustomer`,
    getByNum: `${INVOICES_PATH}getBy/InvoiceNum`,
    getByDate: `${INVOICES_PATH}getBy/ActionDate`,
    save: `${INVOICES_PATH}save`,
    getLines: `${INVOICES_PATH}getLines`,
    getQA: `${INVOICES_PATH}getQA`,
  },
  services: {
    getById: `${SERVICES_PATH}get`,
    getActionBy: `${SERVICES_PATH}getActionBy`,
  },
  orderLines: {
    saveAll: `${ORDER_LINES_PATH}saveAll`,
  },
  proposalLines: {
    saveAll: `${PROPOSAL_LINES_PATH}saveAll`,
    delete: `${PROPOSAL_LINES_PATH}delete`,
  },
  invoiceLines: {
    saveAll: `${INVOICE_LINES_PATH}saveAll`,
  },
  QAs: {
    save: `${QA_PATH}save`,
    add: `${QA_PATH}add`,
  },
  Items: {
    getByKeyTags: `${ITEMS_PATH}GetByKeyTags`,
  },
  tasks: {
    getGantt: `${TASKS_PATH}GetGantt`,
    save: `${TASKS_PATH}SaveList`,
  },
  kanban: {
    getKanban: `${KANBAN_PATH}GetKanban`,
    save: `${KANBAN_PATH}SaveKanban`,
  },
  admins: {
    selectListsAll: `${ADMIN_PATH}SelectListsAll`,
  },
} as const;