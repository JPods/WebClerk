/**
 * fieldRegistry — exposes WC3 model fields to the pdfme template system.
 *
 * Each transaction type has scalar fields + JSON envelope fields.
 * The registry tells the Designer which fields are available for data binding
 * and tells the generator how to extract values from a transaction record.
 *
 * Field paths use dot notation for JSON fields: "totals.subtotal", "refs.links.contact"
 */

export interface FieldDef {
  path: string;
  label: string;
  type: 'scalar' | 'currency' | 'date' | 'text' | 'address' | 'table' | 'json';
  group: string;
}

// ---------------------------------------------------------------------------
// Common fields shared by all transaction types
// ---------------------------------------------------------------------------

const COMMON_HEADER_FIELDS: FieldDef[] = [
  // Scalars
  { path: 'ida', label: 'Document Number', type: 'text', group: 'Header' },
  { path: 'status', label: 'Status', type: 'text', group: 'Header' },
  { path: 'attention', label: 'Attention', type: 'text', group: 'Header' },
  { path: 'address_full', label: 'Address (full)', type: 'address', group: 'Header' },
  { path: 'email', label: 'Email', type: 'text', group: 'Header' },
  { path: 'phone', label: 'Phone', type: 'text', group: 'Header' },
  { path: 'terms', label: 'Terms', type: 'text', group: 'Header' },
  { path: 'price_level', label: 'Price Level / Type Sale', type: 'text', group: 'Header' },
  { path: 'conditions_description', label: 'Conditions', type: 'text', group: 'Header' },
  { path: 'priority', label: 'Priority', type: 'text', group: 'Header' },

  // Dates
  { path: 'dt_created', label: 'Date Created', type: 'date', group: 'Dates' },
  { path: 'dt_modified', label: 'Date Modified', type: 'date', group: 'Dates' },

  // Totals JSON
  { path: 'totals.subtotal', label: 'Subtotal', type: 'currency', group: 'Totals' },
  { path: 'totals.tax', label: 'Tax', type: 'currency', group: 'Totals' },
  { path: 'totals.shipping', label: 'Shipping', type: 'currency', group: 'Totals' },
  { path: 'totals.handling', label: 'Handling', type: 'currency', group: 'Totals' },
  { path: 'totals.discount', label: 'Discount', type: 'currency', group: 'Totals' },
  { path: 'totals.total', label: 'Total', type: 'currency', group: 'Totals' },
  { path: 'totals.balance', label: 'Balance Due', type: 'currency', group: 'Totals' },
  { path: 'totals.down_payment', label: 'Down Payment', type: 'currency', group: 'Totals' },
  { path: 'totals.amount_paid', label: 'Amount Paid', type: 'currency', group: 'Totals' },
  { path: 'totals.cost', label: 'Total Cost', type: 'currency', group: 'Totals' },
  { path: 'totals.margin', label: 'Margin', type: 'currency', group: 'Totals' },
  { path: 'totals.margin_pct', label: 'Margin %', type: 'text', group: 'Totals' },
  { path: 'totals.line_count', label: 'Line Count', type: 'text', group: 'Totals' },

  // Sell JSON
  { path: 'sell.subtotal', label: 'Sell Subtotal', type: 'currency', group: 'Sell' },
  { path: 'sell.discount', label: 'Sell Discount', type: 'currency', group: 'Sell' },
  { path: 'sell.extended', label: 'Sell Extended', type: 'currency', group: 'Sell' },

  // Cost JSON
  { path: 'cost.subtotal', label: 'Cost Subtotal', type: 'currency', group: 'Cost' },
  { path: 'cost.extended', label: 'Cost Extended', type: 'currency', group: 'Cost' },
  { path: 'cost.freight', label: 'Cost Freight', type: 'currency', group: 'Cost' },

  // Finance JSON
  { path: 'finance.commission', label: 'Commission', type: 'currency', group: 'Finance' },
  { path: 'finance.commission_rate', label: 'Commission Rate', type: 'text', group: 'Finance' },

  // Comments JSON
  { path: 'comments.public', label: 'Public Comment', type: 'text', group: 'Comments' },
  { path: 'comments.process', label: 'Process Comment', type: 'text', group: 'Comments' },
  { path: 'comments.contract_detail', label: 'Contract Detail', type: 'text', group: 'Comments' },

  // Refs — customer/contact links
  { path: 'refs.links.customer', label: 'Customer Link', type: 'json', group: 'Refs' },
  { path: 'refs.links.contact', label: 'Contact Links', type: 'json', group: 'Refs' },
  { path: 'refs.links.rep', label: 'Rep Link', type: 'json', group: 'Refs' },
  { path: 'refs.keywords', label: 'Keywords', type: 'json', group: 'Refs' },

  // Source JSON
  { path: 'source.channel', label: 'Source Channel', type: 'text', group: 'Source' },
  { path: 'source.campaign', label: 'Source Campaign', type: 'text', group: 'Source' },

  // Flow JSON
  { path: 'flow.shipped_at', label: 'Shipped At', type: 'date', group: 'Flow' },
  { path: 'flow.invoiced_at', label: 'Invoiced At', type: 'date', group: 'Flow' },
  { path: 'flow.paid_at', label: 'Paid At', type: 'date', group: 'Flow' },
];

// ---------------------------------------------------------------------------
// Line item fields
// ---------------------------------------------------------------------------

const COMMON_LINE_FIELDS: FieldDef[] = [
  { path: 'line_number', label: 'Line #', type: 'text', group: 'Line' },
  { path: 'item.ida_item', label: 'Item Number', type: 'text', group: 'Line' },
  { path: 'item.name', label: 'Item Name', type: 'text', group: 'Line' },
  { path: 'item.description', label: 'Description', type: 'text', group: 'Line' },
  { path: 'item.bin', label: 'Bin Location', type: 'text', group: 'Line' },
  { path: 'quantity.ordered', label: 'Qty Ordered', type: 'text', group: 'Quantity' },
  { path: 'quantity.shipped', label: 'Qty Shipped', type: 'text', group: 'Quantity' },
  { path: 'quantity.staged', label: 'Qty Staged', type: 'text', group: 'Quantity' },
  { path: 'quantity.backordered', label: 'Qty Backordered', type: 'text', group: 'Quantity' },
  { path: 'quantity.received', label: 'Qty Received', type: 'text', group: 'Quantity' },
  { path: 'price.unit', label: 'Unit Price', type: 'currency', group: 'Price' },
  { path: 'price.base', label: 'Base Price (MSRP)', type: 'currency', group: 'Price' },
  { path: 'price.extended', label: 'Extended Price', type: 'currency', group: 'Price' },
  { path: 'price.discount_percent', label: 'Discount %', type: 'text', group: 'Price' },
  { path: 'price.discount_amount', label: 'Discount Amount', type: 'currency', group: 'Price' },
  { path: 'cost.unit', label: 'Unit Cost', type: 'currency', group: 'Cost' },
  { path: 'cost.extended', label: 'Extended Cost', type: 'currency', group: 'Cost' },
  { path: 'tax.amount', label: 'Tax Amount', type: 'currency', group: 'Tax' },
  { path: 'tax.rate', label: 'Tax Rate', type: 'text', group: 'Tax' },
  { path: 'physical.weight', label: 'Weight', type: 'text', group: 'Physical' },
  { path: 'physical.country_of_origin', label: 'Country of Origin', type: 'text', group: 'Physical' },
  { path: 'physical.hs_code', label: 'HS Code', type: 'text', group: 'Physical' },
  { path: 'commission.rate', label: 'Commission Rate', type: 'text', group: 'Commission' },
  { path: 'commission.amount', label: 'Commission Amount', type: 'currency', group: 'Commission' },
  // Serial number fields
  { path: 'serials', label: 'Serial Numbers', type: 'table', group: 'Serials' },
  { path: 'serials.count', label: 'Serial Count', type: 'text', group: 'Serials' },
  { path: 'serials.list', label: 'Serial Number List', type: 'text', group: 'Serials' },
];

// ---------------------------------------------------------------------------
// Computed fields (not directly from DB — built by the generator)
// ---------------------------------------------------------------------------

const COMPUTED_FIELDS: FieldDef[] = [
  { path: '_company.name', label: 'Company Name', type: 'text', group: 'Company' },
  { path: '_company.address_full', label: 'Company Address', type: 'address', group: 'Company' },
  { path: '_company.phone', label: 'Company Phone', type: 'text', group: 'Company' },
  { path: '_company.email', label: 'Company Email', type: 'text', group: 'Company' },
  { path: '_company.website', label: 'Company Website', type: 'text', group: 'Company' },
  { path: '_company.logo_url', label: 'Company Logo URL', type: 'text', group: 'Company' },
  { path: '_billTo', label: 'Bill To (formatted)', type: 'address', group: 'Addresses' },
  { path: '_shipTo', label: 'Ship To (formatted)', type: 'address', group: 'Addresses' },
  { path: '_shipFrom', label: 'Ship From (formatted)', type: 'address', group: 'Addresses' },
  { path: '_dateFormatted', label: 'Document Date (formatted)', type: 'text', group: 'Computed' },
  { path: '_orderNum', label: 'Order Number', type: 'text', group: 'Computed' },
  { path: '_custPO', label: 'Customer PO', type: 'text', group: 'Computed' },
  { path: '_salesId', label: 'Sales Person', type: 'text', group: 'Computed' },
  { path: '_repId', label: 'Rep ID', type: 'text', group: 'Computed' },
  { path: '_shipVia', label: 'Ship Via', type: 'text', group: 'Computed' },
  { path: '_fob', label: 'FOB', type: 'text', group: 'Computed' },
  { path: '_comments', label: 'Public Comment (formatted)', type: 'text', group: 'Computed' },
  { path: '_paymentInfo', label: 'Payment Info', type: 'text', group: 'Computed' },
  { path: '_lines', label: 'Line Items Table', type: 'table', group: 'Computed' },
];

// ---------------------------------------------------------------------------
// Per-model field registries
// ---------------------------------------------------------------------------

const INVOICE_SPECIFIC: FieldDef[] = [
  { path: 'flow.ship_via', label: 'Ship Via', type: 'text', group: 'Shipping' },
  { path: 'flow.fob', label: 'FOB', type: 'text', group: 'Shipping' },
  { path: 'flow.tracking_number', label: 'Tracking Number', type: 'text', group: 'Shipping' },
  { path: 'flow.packed_by', label: 'Packed By', type: 'text', group: 'Shipping' },
  { path: 'flow.ordered_by', label: 'Ordered By', type: 'text', group: 'Shipping' },
];

const PROPOSAL_SPECIFIC: FieldDef[] = [
  { path: 'flow.valid_days', label: 'Valid Days', type: 'text', group: 'Proposal' },
  { path: 'flow.lead_time_days', label: 'Lead Time (days)', type: 'text', group: 'Proposal' },
  { path: 'flow.requested_by', label: 'Requested By', type: 'text', group: 'Proposal' },
];

const PURCHASE_SPECIFIC: FieldDef[] = [
  { path: 'flow.expected_date', label: 'Expected Date', type: 'date', group: 'Purchase' },
  { path: 'flow.received_date', label: 'Received Date', type: 'date', group: 'Purchase' },
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getFieldsForModel(modelName: string): {
  header: FieldDef[];
  line: FieldDef[];
  computed: FieldDef[];
} {
  let specific: FieldDef[] = [];

  switch (modelName) {
    case 'invoice':
      specific = INVOICE_SPECIFIC;
      break;
    case 'proposal':
      specific = PROPOSAL_SPECIFIC;
      break;
    case 'purchase':
      specific = PURCHASE_SPECIFIC;
      break;
  }

  return {
    header: [...COMMON_HEADER_FIELDS, ...specific],
    line: COMMON_LINE_FIELDS,
    computed: COMPUTED_FIELDS,
  };
}

/**
 * Get all fields flattened (for Designer field picker dropdown).
 */
export function getAllFieldsFlat(modelName: string): FieldDef[] {
  const { header, line, computed } = getFieldsForModel(modelName);
  return [...computed, ...header, ...line];
}

/**
 * Get field groups for UI display.
 */
export function getFieldGroups(modelName: string): Record<string, FieldDef[]> {
  const all = getAllFieldsFlat(modelName);
  const groups: Record<string, FieldDef[]> = {};
  for (const f of all) {
    if (!groups[f.group]) groups[f.group] = [];
    groups[f.group].push(f);
  }
  return groups;
}
