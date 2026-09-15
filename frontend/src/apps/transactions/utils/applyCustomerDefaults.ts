/* LastChecked: 2026-09-04 | WhereUsed: UiDetail | WhoCreated: Claude */
/**
 * applyCustomerDefaults — fetch customer record and return fields to merge into transaction.
 *
 * PJPV: writes to JSON aspect envelopes (addresses, emails, phones),
 * not scalar columns. Scalar company/attention/email are also set as
 * search indexes but the aspects are the source of truth.
 */
import { getRecord } from '@/api/wcapi';

export interface CustomerDefaults {
  customer_id: number;
  company: string;
  attention: string;
  email: string;
  phone: string;
  address_full: string;
  price_level: string;
  terms: string;
  ship_via: string;
  // JSON aspects (source of truth)
  addresses: {
    bill_to: { contact_id?: number; attention: string; full_address: string; instructions: string };
    ship_to: { contact_id?: number; attention: string; full_address: string; instructions: string };
  };
  emails: {
    bill_to: { email: string };
    ship_to: { email: string };
  };
  phones: {
    bill_to: { number: string };
    ship_to: { number: string };
  };
  finance?: Record<string, any>;
  tax?: Record<string, any>;
  customer_config?: Record<string, any>;
  has_reps?: boolean;
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
  const custResp = await getRecord('customer', customerId);
  const cust = custResp?.record || custResp;
  if (!cust) throw new Error(`Customer ${customerId} not found`);

  const company = cust.company || cust.display_name || cust.name || '';
  const config = cust.config || {};

  // Read from org's JSON aspects (source of truth)
  const orgAddrs = cust.addresses || {};
  const orgEmails = cust.emails || {};
  const orgPhones = cust.phones || {};

  const billAttn = orgAddrs.bill_to?.attention || cust.attention || '';
  const billAddr = orgAddrs.bill_to?.full_address || cust.address_full || '';
  const billInstr = orgAddrs.bill_to?.instructions || '';
  const billEmail = orgEmails.bill_to?.email || cust.email || '';
  const billPhone = orgPhones.bill_to?.number || cust.phone || '';
  const billContactId = orgAddrs.bill_to?.contact_id || cust.contact_id || null;

  const shipAttn = orgAddrs.ship_to?.attention || billAttn;
  const shipAddr = orgAddrs.ship_to?.full_address || billAddr;
  const shipInstr = orgAddrs.ship_to?.instructions || '';
  const shipEmail = orgEmails.ship_to?.email || billEmail;
  const shipPhone = orgPhones.ship_to?.number || billPhone;
  const shipContactId = orgAddrs.ship_to?.contact_id || billContactId;

  const defaults: CustomerDefaults = {
    customer_id: customerId,
    company,
    // Scalar indexes (for search — not source of truth)
    attention: billAttn,
    email: billEmail,
    phone: billPhone,
    address_full: billAddr,
    price_level: cust.price_level || '',
    terms: cust.terms || '',
    ship_via: cust.ship_via || config.ship_via || '',
    // JSON aspects (source of truth)
    addresses: {
      bill_to: { contact_id: billContactId, attention: billAttn, full_address: billAddr, instructions: billInstr },
      ship_to: { contact_id: shipContactId, attention: shipAttn, full_address: shipAddr, instructions: shipInstr },
    },
    emails: {
      bill_to: { email: billEmail },
      ship_to: { email: shipEmail },
    },
    phones: {
      bill_to: { number: billPhone },
      ship_to: { number: shipPhone },
    },
  };

  // ── Tax jurisdiction + exemption ─────────────────────────────────
  const taxExemptCode = cust.tax_exempt_code || '';
  const isExempt = taxExemptCode !== '' && taxExemptCode !== 'DoTax';

  if (isExempt) {
    defaults.finance = {
      sales_tax_rate: 0,
      sales_tax_name: 'Exempt',
      sales_tax_id: 0,
    };
    defaults.tax = {
      sales_rate: 0,
      sales: 0,
      exempt_code: taxExemptCode,
    };
  } else if (cust.tax_jurisdiction_id) {
    try {
      const tjResp = await getRecord('tax_jurisdiction', cust.tax_jurisdiction_id);
      const tj = tjResp?.record || tjResp;
      if (tj) {
        defaults.finance = {
          sales_tax_rate: tj.tax_rate_sales || 0,
          sales_tax_name: tj.tax_name || tj.tax_jurisdiction || '',
          sales_tax_id: tj.id,
        };
        defaults.tax = {
          sales_rate: tj.tax_rate_sales || 0,
          cost_rate: tj.tax_rate_cost || 0,
          shipping: tj.tax_rate_on_shipping || 0,
        };
      }
    } catch { /* jurisdiction fetch failed — user sets rate manually */ }
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

  // ── Rep assignments → commission flag ────────────────────────────
  const refs = cust.refs || {};
  const repLinks = refs.links?.reps || [];
  const repIds = cust.relations?.rep_ids || [];
  if ((Array.isArray(repLinks) && repLinks.length > 0) ||
      (Array.isArray(repIds) && repIds.length > 0)) {
    defaults.has_reps = true;
  }

  // Fetch contact if specified — overrides bill_to fields
  if (contactId) {
    try {
      const ctResp = await getRecord('contact', contactId);
      const ct = ctResp?.record || ctResp;
      if (ct) {
        const ctAttn = ct.attention || ct.display_name ||
          [ct.name_first, ct.name_last].filter(Boolean).join(' ') || '';
        const ctEmail = ct.email || '';
        const ctPhone = ct.phone || '';
        const ctAddr = ct.address_full || '';

        if (ctAttn) {
          defaults.attention = ctAttn;
          defaults.addresses.bill_to.attention = ctAttn;
        }
        if (ctEmail) {
          defaults.email = ctEmail;
          defaults.emails.bill_to.email = ctEmail;
        }
        if (ctPhone) {
          defaults.phone = ctPhone;
          defaults.phones.bill_to.number = ctPhone;
        }
        if (ctAddr) {
          defaults.address_full = ctAddr;
          defaults.addresses.bill_to.full_address = ctAddr;
        }
      }
    } catch { /* contact fetch failed, keep customer defaults */ }
  }

  return defaults;
}
