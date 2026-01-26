/**
 * Model Name Resolver
 * 
 * Centralizes all model name translation for the wcapi endpoints.
 * Converts RESTful-style paths and various naming conventions to 
 * the canonical wcapi model_name format.
 * 
 * Security: All data access flows through wcapi endpoints, never directly to REST endpoints.
 * This provides a single point of control for authentication, authorization, and auditing.
 * 
 * Usage:
 *   resolveModelName('order')           -> 'order'
 *   resolveModelName('sales_order')     -> 'order'
 *   resolveModelName('SalesOrder')      -> 'order'
 *   resolveModelName('purchase-order')  -> 'purchase'
 *   resolveModelName('invoice')         -> 'invoice'
 */

// Canonical model name mappings
// Keys are normalized (lowercase, no separators), values are the wcapi model_name
const MODEL_NAME_MAP: Record<string, string> = {
  // Transactions - canonical names use snake_case per WC3 model_registry
  salesorder: 'order',
  order: 'order',
  sales: 'order',
  invoice: 'invoice',
  purchaseorder: 'purchase',
  purchase: 'purchase',
  po: 'purchase',
  proposal: 'proposal',
  quote: 'proposal',
  workorder: 'work_order',
  work: 'work_order',
  wo: 'work_order',
  requisition: 'requisition',
  req: 'requisition',
  
  // Transaction Lines
  salesorderline: 'order_line',
  orderline: 'order_line',
  invoiceline: 'invoice_line',
  purchaseorderline: 'purchase_line',
  purchaseline: 'purchase_line',
  poline: 'purchase_line',
  proposalline: 'proposal_line',
  quoteline: 'proposal_line',
  workorderline: 'work_order_line',
  woline: 'work_order_line',
  requisitionline: 'requisition_line',
  reqline: 'requisition_line',
  
  // Organizations
  customer: 'customer',
  vendor: 'vendor',
  manufacturer: 'manufacturer',
  rep: 'rep',
  employee: 'employee',
  organization: 'organization',
  org: 'organization',
  
  // Products
  item: 'item',
  product: 'item',
  category: 'category',
  warehouse: 'warehouse',
  serial: 'serial',
  variant: 'variant',
  specification: 'specification',
  spec: 'specification',
  
  // Core
  contact: 'contact',
  location: 'location',
  address: 'location',
  setting: 'setting',
  report: 'report',
  action: 'action',
  
  // Communications
  email: 'email',
  phone: 'phone',
  domain: 'domain',
  
  // Accounts
  audit: 'audit',
  currency: 'currency',
  exchangerate: 'exchange_rate',
  glaccount: 'gl_account',
  gljournal: 'gl_journal',
  ledger: 'ledger',
  taxjurisdiction: 'tax_jurisdiction',
  term: 'term',
  
  // Support
  campaign: 'campaign',
  task: 'task',
  event: 'event',
  
  // Sync
  bundle: 'bundle',
};

// RESTful path patterns to model name
// Handles paths like /api/transactions/salesorder/22
const PATH_PATTERN_MAP: Record<string, string> = {
  'transactions/sales-order': 'order',
  'transactions/salesorder': 'order',
  'transactions/order': 'order',
  'transactions/invoice': 'invoice',
  'transactions/purchase-order': 'purchase',
  'transactions/purchaseorder': 'purchase',
  'transactions/purchase': 'purchase',
  'transactions/proposal': 'proposal',
  'transactions/work-order': 'work_order',
  'transactions/workorder': 'work_order',
  'transactions/requisition': 'requisition',
  'orgs/customer': 'customer',
  'orgs/vendor': 'vendor',
  'orgs/manufacturer': 'manufacturer',
  'orgs/rep': 'rep',
  'orgs/employee': 'employee',
  'orgs/organization': 'organization',
  'products/item': 'item',
  'products/category': 'category',
  'products/warehouse': 'warehouse',
  'core/contact': 'contact',
  'core/location': 'location',
  'core/setting': 'setting',
  'core/action': 'action',
  'communications/email': 'email',
  'communications/phone': 'phone',
  'accounts/audit': 'audit',
  'accounts/currency': 'currency',
  'accounts/gl-account': 'gl_account',
  'accounts/ledger': 'ledger',
  'support/campaign': 'campaign',
  'support/task': 'task',
};

/**
 * Normalize a string by removing separators and converting to lowercase
 */
function normalize(input: string): string {
  return input
    .replace(/[-_/]/g, '')  // Remove hyphens, underscores, slashes
    .toLowerCase();
}

/**
 * Resolve a model name from various formats to the canonical wcapi model_name.
 * 
 * @param input - Model name in any format (kebab-case, snake_case, camelCase, etc.)
 * @returns Canonical wcapi model_name
 * @throws Error if model name cannot be resolved
 */
export function resolveModelName(input: string): string {
  if (!input) {
    throw new Error('Model name is required');
  }
  
  // First, try direct lookup after normalization
  const normalized = normalize(input);
  if (MODEL_NAME_MAP[normalized]) {
    return MODEL_NAME_MAP[normalized];
  }
  
  // If input looks like a path, try path pattern matching
  const lowerInput = input.toLowerCase();
  for (const [pattern, modelName] of Object.entries(PATH_PATTERN_MAP)) {
    if (lowerInput.includes(pattern)) {
      return modelName;
    }
  }
  
  // Fallback: assume the normalized input IS the model name
  // This handles cases where the exact model name is passed
  console.warn(`[resolveModelName] Unknown model "${input}", using normalized: "${normalized}"`);
  return normalized;
}

/**
 * Extract model name and ID from a RESTful path.
 * 
 * Handles patterns like:
 *   /api/transactions/salesorder/22
 *   /transactions/sales-order/detail/22
 *   /api/salesorder/22
 * 
 * @param path - URL path
 * @returns Object with modelName and optional id
 */
export function parseRestfulPath(path: string): { modelName: string; id?: number } {
  // Remove leading slash and split
  const segments = path.replace(/^\/+/, '').split('/').filter(Boolean);
  
  // Try to find an ID (numeric segment)
  let id: number | undefined;
  const numericIdx = segments.findIndex(s => /^\d+$/.test(s));
  if (numericIdx !== -1) {
    id = parseInt(segments[numericIdx], 10);
    segments.splice(numericIdx, 1);
  }
  
  // Remove common prefixes
  const filtered = segments.filter(s => !['api', 'wcapi', 'detail', 'list', 'edit', 'new'].includes(s.toLowerCase()));
  
  // Join remaining segments and resolve
  const pathPart = filtered.join('/');
  const modelName = resolveModelName(pathPart);
  
  return { modelName, id };
}

/**
 * Convert a URL path segment to wcapi model_name format.
 * Used for URL-based routing to API calls.
 * 
 * @param urlSegment - URL segment like "sales-order" or "purchase-order"
 * @returns wcapi model_name like "salesorder" or "purchaseorder"
 */
export function urlToModelName(urlSegment: string): string {
  return resolveModelName(urlSegment);
}

/**
 * Convert a wcapi model_name to URL-friendly format.
 * Used for building navigation URLs.
 * 
 * @param modelName - wcapi model_name like "salesorder"
 * @returns URL segment like "sales-order"
 */
export function modelNameToUrl(modelName: string): string {
  // Special cases with hyphens in URL
  const URL_MAP: Record<string, string> = {
    sales_order: 'sales-order',
    order: 'order',
    purchase: 'purchase',
    work_order: 'work-order',
    sales_order_line: 'sales-order-line',
    order_line: 'order-line',
    purchase_line: 'purchase-line',
    work_order_line: 'work-order-line',
    invoice_line: 'invoice-line',
    proposal_line: 'proposal-line',
    exchange_rate: 'exchange-rate',
    gl_account: 'gl-account',
    gl_journal: 'gl-journal',
    tax_jurisdiction: 'tax-jurisdiction',
  };
  
  return URL_MAP[modelName] || modelName.replace(/_/g, '-');
}

/**
 * Get the transaction type for routing purposes from a model name.
 * 
 * @param modelName - wcapi model_name
 * @returns Transaction type for routing (e.g., "sales_order", "invoice")
 */
export function getTransactionType(modelName: string): string {
  const TYPE_MAP: Record<string, string> = {
    sales_order: 'sales_order',
    order: 'order',
    invoice: 'invoice',
    purchase: 'purchase',
    proposal: 'proposal',
    work_order: 'work_order',
    requisition: 'requisition',
  };
  
  return TYPE_MAP[modelName] || modelName;
}

// Export the maps for testing/debugging
export { MODEL_NAME_MAP, PATH_PATTERN_MAP };
