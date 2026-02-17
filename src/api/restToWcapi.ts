/**
 * REST to WCAPI Route Mapper
 * 
 * This module provides utilities to convert legacy RESTful API calls to the 
 * standardized wcapi endpoints. All data access should flow through wcapi for:
 * - Consistent authentication/authorization
 * - Audit logging
 * - Single point of control for data access
 * 
 * WCAPI Endpoints:
 *   GET  /wcapi/get/?model_name={name}           - List records
 *   GET  /wcapi/get/?model_name={name}&id={id}   - Get single record
 *   POST /wcapi/save/                            - Create/Update/Delete records
 * 
 * Usage:
 *   import { convertRestToWcapi, getWcapiEndpoint } from '@/api/restToWcapi';
 *   
 *   // Convert a RESTful path to wcapi params
 *   const { endpoint, params } = convertRestToWcapi('/api/orgs/customer/42');
 *   // { endpoint: '/wcapi/get/', params: { model_name: 'customer', id: 42 } }
 */

import { resolveModelName, parseRestfulPath } from './modelNameResolver';

// ============================================================================
// Route Mapping Configuration
// ============================================================================

/**
 * Maps RESTful path patterns to wcapi model names.
 * Keys are path patterns (lowercase), values are the canonical wcapi model_name.
 */
export const REST_PATH_TO_MODEL: Record<string, string> = {
  // Orgs
  'orgs/customer': 'customer',
  'orgs/customers': 'customer',
  'orgs/vendor': 'vendor',
  'orgs/vendors': 'vendor',
  'orgs/employee': 'employee',
  'orgs/employees': 'employee',
  'orgs/contact': 'contact',
  'orgs/contacts': 'contact',
  'orgs/rep': 'rep',
  'orgs/reps': 'rep',
  'orgs/manufacturer': 'manufacturer',
  'orgs/manufacturers': 'manufacturer',
  'orgs/organization': 'organization',
  'orgs/organizations': 'organization',
  
  // Transactions
  'transactions/order': 'order',
  'transactions/orders': 'order',
  'transactions/invoice': 'invoice',
  'transactions/invoices': 'invoice',
  'transactions/purchase': 'purchase',
  'transactions/purchases': 'purchase',
  'transactions/purchase-order': 'purchase',
  'transactions/proposal': 'proposal',
  'transactions/proposals': 'proposal',
  'transactions/quote': 'proposal',
  'transactions/quotes': 'proposal',
  'transactions/workorder': 'workorder',
  'transactions/workorders': 'workorder',
  'transactions/work-order': 'workorder',
  'transactions/requisition': 'requisition',
  'transactions/requisitions': 'requisition',
  'transactions/project': 'project',
  'transactions/projects': 'project',
  'transactions/receipt': 'receipt',
  'transactions/receipts': 'receipt',
  
  // Transaction Lines
  'transactions/order-line': 'order_line',
  'transactions/orderline': 'order_line',
  'transactions/invoice-line': 'invoice_line',
  'transactions/invoiceline': 'invoice_line',
  'transactions/purchase-line': 'purchase_line',
  'transactions/purchaseline': 'purchase_line',
  'transactions/proposal-line': 'proposal_line',
  'transactions/proposalline': 'proposal_line',
  'transactions/workorder-line': 'workorderline',
  'transactions/workorderline': 'workorderline',
  
  // Products
  'products/item': 'item',
  'products/items': 'item',
  'products/service': 'service',
  'products/services': 'service',
  'products/category': 'category',
  'products/categories': 'category',
  'products/warehouse': 'warehouse',
  'products/warehouses': 'warehouse',
  'products/serial': 'serial',
  'products/serials': 'serial',
  'products/variant': 'variant',
  'products/variants': 'variant',
  'products/specification': 'specification',
  'products/specifications': 'specification',
  'products/catalog': 'catalog',
  'products/catalogs': 'catalog',
  'products/bom': 'bill_of_material',
  'products/bill-of-material': 'bill_of_material',
  'products/flow': 'flow',
  'products/flows': 'flow',
  'products/usage': 'usage',
  'products/usages': 'usage',
  'products/matrics': 'matrics',
  'products/metrics': 'metrics',
  'products/org-item': 'org_item',
  'products/orgitem': 'org_item',
  'products/item-xref': 'item_xref',
  'products/itemxref': 'item_xref',
  
  // Communications
  'communications/email': 'email',
  'communications/emails': 'email',
  'communications/phone': 'phone',
  'communications/phones': 'phone',
  'communications/domain': 'domain',
  'communications/domains': 'domain',
  'communications/address': 'location',
  'communications/addresses': 'location',
  'communications/location': 'location',
  'communications/locations': 'location',
  
  // Accounts
  'accounts/gl-account': 'gl_account',
  'accounts/glaccount': 'gl_account',
  'accounts/gl-journal': 'gl_journal',
  'accounts/gljournal': 'gl_journal',
  'accounts/currency': 'currency',
  'accounts/currencies': 'currency',
  'accounts/exchange-rate': 'exchange_rate',
  'accounts/exchangerate': 'exchange_rate',
  'accounts/exchange-transaction': 'exchange_transaction',
  'accounts/exchangetransaction': 'exchange_transaction',
  'accounts/audit': 'audit',
  'accounts/audits': 'audit',
  'accounts/term': 'term',
  'accounts/terms': 'term',
  'accounts/ledger': 'ledger',
  'accounts/ledgers': 'ledger',
  'accounts/tax-jurisdiction': 'tax_jurisdiction',
  'accounts/taxjurisdiction': 'tax_jurisdiction',
  
  // Core
  'core/contact': 'contact',
  'core/contacts': 'contact',
  'core/setting': 'setting',
  'core/settings': 'setting',
  'core/report': 'report',
  'core/reports': 'report',
  'core/action': 'action',
  'core/actions': 'action',
  'core/template': 'template',
  'core/templates': 'template',
  'core/notification': 'notification',
  'core/notifications': 'notification',
  'core/api-log': 'api_log',
  'core/apilog': 'api_log',
  
  // Docs
  'docs/document': 'document',
  'docs/documents': 'document',
  'docs/tag': 'tag',
  'docs/tags': 'tag',
  'docs/question-answer': 'question_answer',
  'docs/questionanswer': 'question_answer',
  'docs/qa': 'question_answer',
  'docs/linkage': 'linkage_entry',
  'docs/linkage-entry': 'linkage_entry',
  'docs/linkageentry': 'linkage_entry',
  
  // Support
  'support/campaign': 'campaign',
  'support/campaigns': 'campaign',
  'support/task': 'task',
  'support/tasks': 'task',
  'support/event': 'event',
  'support/events': 'event',
  
  // Sync
  'sync/bundle': 'bundle',
  'sync/bundles': 'bundle',
  'sync/connection': 'connection',
  'sync/connections': 'connection',
};

// ============================================================================
// WCAPI Endpoint Configuration
// ============================================================================

export const WCAPI_ENDPOINTS = {
  // Data endpoints
  GET: '/wcapi/get/',           // GET with params: model_name, id?, limit?, offset?, search?, filters?
  SAVE: '/wcapi/save/',         // POST with body: { model_name, id?, data? }
  DELETE: '/wcapi/delete/',     // GET with params: model_name, id OR POST with body: { model_name, id }
  
  // Model metadata endpoints
  MODEL_LIST: '/wcapi/model_name/list/',
  MODEL_DETAIL: '/wcapi/model_name/detail/',
  
  // Auth endpoints
  LOGIN: '/wcapi/login/',
  LOGOUT: '/wcapi/logout/',
  REFRESH: '/wcapi/token_refresh/',
  ME: '/wcapi/me/',
} as const;

// ============================================================================
// Conversion Functions
// ============================================================================

export interface WcapiRequest {
  endpoint: string;
  method: 'GET' | 'POST';
  params?: Record<string, any>;
  body?: Record<string, any>;
}

/**
 * Convert a RESTful API path to wcapi request format.
 * 
 * @param restPath - RESTful path like '/api/orgs/customer/42' or 'customers/42'
 * @param httpMethod - Original HTTP method (GET, POST, PUT, DELETE, PATCH)
 * @param data - Request body for POST/PUT/PATCH requests
 * @returns WcapiRequest with endpoint, method, params, and body
 * 
 * @example
 * // GET list
 * convertRestToWcapi('/api/orgs/customers', 'GET')
 * // { endpoint: '/wcapi/get/', method: 'GET', params: { model_name: 'customer' } }
 * 
 * @example
 * // GET single record
 * convertRestToWcapi('/api/orgs/customer/42', 'GET')
 * // { endpoint: '/wcapi/get/', method: 'GET', params: { model_name: 'customer', id: 42 } }
 * 
 * @example
 * // Create record
 * convertRestToWcapi('/api/orgs/customer', 'POST', { name: 'Acme Corp' })
 * // { endpoint: '/wcapi/save/', method: 'POST', body: { model_name: 'customer', data: { name: 'Acme Corp' } } }
 * 
 * @example
 * // Update record
 * convertRestToWcapi('/api/orgs/customer/42', 'PUT', { name: 'Updated' })
 * // { endpoint: '/wcapi/save/', method: 'POST', body: { model_name: 'customer', id: 42, data: { name: 'Updated' } } }
 * 
 * @example
 * // Delete record
 * convertRestToWcapi('/api/orgs/customer/42', 'DELETE')
 * // { endpoint: '/wcapi/save/', method: 'POST', body: { model_name: 'customer', id: 42, method: 'delete' } }
 */
export function convertRestToWcapi(
  restPath: string,
  httpMethod: string = 'GET',
  data?: Record<string, any>
): WcapiRequest {
  // Parse the path to extract model name and optional ID
  const { modelName, id } = parseRestfulPath(restPath);
  const resolvedModel = resolveModelName(modelName);
  const method = httpMethod.toUpperCase();
  
  // GET requests use the /wcapi/get/ endpoint
  if (method === 'GET') {
    const params: Record<string, any> = { model_name: resolvedModel };
    if (id !== undefined) {
      params.id = id;
    }
    return {
      endpoint: WCAPI_ENDPOINTS.GET,
      method: 'GET',
      params,
    };
  }
  
  // DELETE uses /wcapi/delete/ endpoint
  if (method === 'DELETE') {
    if (id === undefined) {
      throw new Error(`DELETE requires a record ID in the path: ${restPath}`);
    }
    return {
      endpoint: WCAPI_ENDPOINTS.DELETE,
      method: 'GET',
      params: {
        model_name: resolvedModel,
        id,
      },
    };
  }
  
  // POST/PUT/PATCH use /wcapi/save/ endpoint
  // POST without ID = create, POST/PUT/PATCH with ID = update
  const body: Record<string, any> = {
    model_name: resolvedModel,
  };
  
  if (id !== undefined) {
    body.id = id;
  }
  
  if (data) {
    body.data = data;
  }
  
  return {
    endpoint: WCAPI_ENDPOINTS.SAVE,
    method: 'POST',
    body,
  };
}

/**
 * Get the appropriate wcapi endpoint URL for a model operation.
 * 
 * @param operation - 'list' | 'detail' | 'create' | 'update' | 'delete'
 * @param modelName - Model name (will be resolved to canonical form)
 * @param id - Record ID (required for detail, update, delete)
 * @returns Complete endpoint URL with query params
 */
export function getWcapiEndpoint(
  operation: 'list' | 'detail' | 'create' | 'update' | 'delete',
  modelName: string,
  id?: number
): { url: string; method: 'GET' | 'POST' } {
  const resolved = resolveModelName(modelName);
  
  switch (operation) {
    case 'list':
      return {
        url: `${WCAPI_ENDPOINTS.GET}?model_name=${resolved}`,
        method: 'GET',
      };
    
    case 'detail':
      if (id === undefined) {
        throw new Error(`detail operation requires an ID for model: ${modelName}`);
      }
      return {
        url: `${WCAPI_ENDPOINTS.GET}?model_name=${resolved}&id=${id}`,
        method: 'GET',
      };
    
    case 'create':
    case 'update':
      return {
        url: WCAPI_ENDPOINTS.SAVE,
        method: 'POST',
      };
    
    case 'delete':
      if (id === undefined) {
        throw new Error(`delete operation requires an ID for model: ${modelName}`);
      }
      return {
        url: `${WCAPI_ENDPOINTS.DELETE}?model_name=${resolved}&id=${id}`,
        method: 'GET',
      };
  }
}

/**
 * Build the request body for a wcapi save operation.
 * 
 * @param operation - 'create' | 'update' | 'delete'
 * @param modelName - Model name (will be resolved)
 * @param data - Record data (for create/update)
 * @param id - Record ID (for update/delete)
 */
export function buildSaveBody(
  operation: 'create' | 'update' | 'delete',
  modelName: string,
  data?: Record<string, any>,
  id?: number
): Record<string, any> {
  const resolved = resolveModelName(modelName);
  const body: Record<string, any> = { model_name: resolved };
  
  if (operation === 'delete') {
    if (id === undefined) {
      throw new Error(`delete operation requires an ID for model: ${modelName}`);
    }
    return {
      model_name: resolved,
      id,
    };
  }
  
  if (operation === 'update') {
    if (id === undefined) {
      throw new Error(`update operation requires an ID for model: ${modelName}`);
    }
    body.id = id;
  }
  
  if (data) {
    body.data = data;
  }
  
  return body;
}

// ============================================================================
// Migration Helpers
// ============================================================================

/**
 * Check if a path is already using wcapi endpoints.
 */
export function isWcapiPath(path: string): boolean {
  const lower = path.toLowerCase();
  return lower.includes('/wcapi/');
}

/**
 * Extract model name from a RESTful path without the full conversion.
 */
export function extractModelFromPath(path: string): string | null {
  try {
    const { modelName } = parseRestfulPath(path);
    return resolveModelName(modelName);
  } catch {
    return null;
  }
}

/**
 * Validate that a model name is known and can be resolved.
 */
export function isKnownModel(modelName: string): boolean {
  try {
    resolveModelName(modelName);
    return true;
  } catch {
    return false;
  }
}

// ============================================================================
// Exports
// ============================================================================

export {
  resolveModelName,
  parseRestfulPath,
} from './modelNameResolver';
