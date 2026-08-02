/* LastChecked: 2026-08-01 | WhereUsed: TransactionDetail | WhoCreated: Claude */
/**
 * applyCustomerDefaults — fetch customer record and return fields to merge into transaction.
 *
 * When a user selects a customer on an order (or any sell-side transaction),
 * this function fetches the customer + primary contact and returns a dict of
 * fields to merge into the edit buffer.
 *
 * This is NOT a save. The caller merges the returned fields into editData.
 * Post or Pend applies on save.
 *
 * Usage:
 *   const defaults = await applyCustomerDefaults(customerId);
 *   setEditData(prev => ({ ...prev, ...defaults }));
 */
import { getRecord } from '@/api/wcapi';

export interface CustomerDefaults {
  customer_id: number;
  company: string;
  phone: string;
  email: string;
  attention: string;
  address_full: string;
  price_level: string;
  terms: string;
  ship_via: string;
  customer_config?: Record<string, any>;
  customer_company?: string;
  config?: { ship_to?: Record<string, any> };
}

/**
 * Fetch customer + contact and build defaults dict.
 * @param customerId - OrgBase record ID
 * @param contactId - optional Contact record ID (overrides customer fields)
 */
export async function applyCustomerDefaults(
  customerId: number,
  contactId?: number,
): Promise<CustomerDefaults> {
  // Fetch customer
  const custResp = await getRecord('customer', customerId);
  const cust = custResp?.record || custResp;

  if (!cust) throw new Error(`Customer ${customerId} not found`);

  const company = cust.company || cust.display_name || cust.name || '';
  const config = cust.config || {};

  // Build defaults from customer
  const defaults: CustomerDefaults = {
    customer_id: customerId,
    company,
    customer_company: company,
    phone: cust.phone || '',
    email: cust.email || '',
    attention: cust.attention || '',
    address_full: cust.address_full || '',
    price_level: cust.price_level || '',
    terms: cust.terms || '',
    ship_via: cust.ship_via || config.ship_via || '',
  };

  // Ship-to: use config.ship_to if present, otherwise default from customer base data
  if (config.ship_to) {
    defaults.config = { ship_to: config.ship_to };
  } else {
    // No dedicated ship_to — default to customer's own address
    defaults.config = {
      ship_to: {
        company: company,
        phone: defaults.phone,
        attention: defaults.attention,
        address1: defaults.address_full,
        city_state_zip: '',
        ship_via: defaults.ship_via,
      }
    };
  }

  // Credit/sales data for Summary tab
  const creditFields = [
    'credit_limit', 'credit_available', 'balance_due', 'balance_current',
    'sales_mtd', 'sales_ytd', 'sales_lifetime', 'avg_pay_days',
    'last_payment_amount', 'last_sale',
  ];
  const customerConfig: Record<string, any> = {};
  for (const k of creditFields) {
    if (config[k] != null) customerConfig[k] = config[k];
  }
  if (Object.keys(customerConfig).length) {
    defaults.customer_config = customerConfig;
  }

  // Fetch contact if specified — overrides customer fields
  if (contactId) {
    try {
      const ctResp = await getRecord('contact', contactId);
      const ct = ctResp?.record || ctResp;
      if (ct) {
        defaults.attention = ct.attention || ct.display_name ||
          [ct.name_first, ct.name_last].filter(Boolean).join(' ') || defaults.attention;
        defaults.phone = ct.phone || defaults.phone;
        defaults.email = ct.email || defaults.email;
        defaults.address_full = ct.address_full || defaults.address_full;
      }
    } catch { /* contact fetch failed, keep customer defaults */ }
  }

  return defaults;
}
