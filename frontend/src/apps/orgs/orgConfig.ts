/**
 * orgConfig — config-driven org page definitions.
 *
 * One config per org type. Shared components read this to know
 * which fields to show, what actions to offer, what related
 * records to display, and what to publish to the web.
 *
 * A contact can relate to ALL org types simultaneously.
 * A customer can also be a vendor and a rep.
 */

export interface OrgFieldDef {
  name: string;         // field name on OrgBase
  label: string;        // display label
  type?: 'text' | 'email' | 'phone' | 'select' | 'readonly' | 'badge';
  width?: string;       // column width for list
  options?: { value: string; label: string }[];  // for select type
  publishable?: boolean; // can be published to web for this relationship
}

export interface OrgAction {
  label: string;
  icon?: string;
  route?: string;       // navigate to this route with {id} placeholder
  model?: string;       // create new record of this model
  variant?: 'primary' | 'default' | 'danger';
}

export interface OrgRelated {
  label: string;
  model: string;        // wcapi model_name to query
  filterField: string;  // field on related model that references this org (e.g., 'customer_id')
  listFields: string[]; // fields to show in the related list
}

export interface OrgTypeConfig {
  key: string;              // wcapi model_name
  label: string;            // singular display name
  labelPlural: string;
  icon?: string;
  color: string;            // accent color for badges/headers

  // Fields for list view (compact)
  listFields: OrgFieldDef[];
  // Fields for detail header (top card)
  headerFields: OrgFieldDef[];
  // Fields for detail form (editable)
  formFields: OrgFieldDef[];
  // Fields publishable to web (blessed list per relationship)
  publishFields: string[];

  // Actions available on this org type
  actions: OrgAction[];
  // Related records to show as tabs/panels
  related: OrgRelated[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Status options shared across all org types
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'prospect', label: 'Prospect' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'retired', label: 'Retired' },
];

const PRICE_LEVEL_OPTIONS = [
  { value: 'retail', label: 'Retail' },
  { value: 'wholesale', label: 'Wholesale' },
  { value: 'distributor', label: 'Distributor' },
  { value: 'sample', label: 'Sample' },
];

// ─────────────────────────────────────────────────────────────────────────────
// Shared field definitions (reused across org types)
// ─────────────────────────────────────────────────────────────────────────────

const F = {
  id:           { name: 'id', label: 'ID', type: 'readonly' as const, width: '70px' },
  displayName:  { name: 'display_name', label: 'Name', type: 'text' as const, width: '20%', publishable: true },
  status:       { name: 'status', label: 'Status', type: 'badge' as const, width: '100px', options: STATUS_OPTIONS },
  email:        { name: 'email', label: 'Email', type: 'email' as const, width: '15%', publishable: true },
  phone:        { name: 'phone', label: 'Phone', type: 'phone' as const, width: '12%', publishable: true },
  attention:    { name: 'attention', label: 'Attention', type: 'text' as const, width: '15%' },
  addressFull:  { name: 'address_full', label: 'Address', type: 'text' as const, publishable: true },
  domain:       { name: 'domain', label: 'Domain', type: 'text' as const },
  priceLevel:   { name: 'price_level', label: 'Price Level', type: 'select' as const, options: PRICE_LEVEL_OPTIONS },
  terms:        { name: 'terms', label: 'Terms', type: 'text' as const },
  orgType:      { name: 'org_type', label: 'Org Type', type: 'readonly' as const, width: '100px' },
  company:      { name: 'company', label: 'Company', type: 'text' as const },
  isActive:     { name: 'is_active', label: 'Active', type: 'badge' as const, width: '80px' },
};

// ─────────────────────────────────────────────────────────────────────────────
// Per-type configurations
// ─────────────────────────────────────────────────────────────────────────────

export const ORG_CONFIGS: Record<string, OrgTypeConfig> = {
  customer: {
    key: 'customer',
    label: 'Customer',
    labelPlural: 'Customers',
    color: '#0d6efd',
    listFields: [F.id, F.displayName, F.status, F.email, F.phone, F.addressFull, F.priceLevel],
    headerFields: [F.displayName, F.status, F.email, F.phone],
    formFields: [F.displayName, F.attention, F.email, F.phone, F.domain, F.addressFull, F.priceLevel, F.terms, F.status],
    publishFields: ['display_name', 'email', 'phone', 'address_full', 'domain'],
    actions: [
      { label: 'New Order', model: 'order', variant: 'primary' },
      { label: 'New Proposal', model: 'proposal' },
      { label: 'New Invoice', model: 'invoice' },
      { label: 'Statement', route: '/transactions/customer-statement/{id}' },
    ],
    related: [
      { label: 'Orders', model: 'order', filterField: 'customer_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
      { label: 'Invoices', model: 'invoice', filterField: 'customer_id', listFields: ['ida', 'status', 'total', 'balance', 'dt_created'] },
      { label: 'Proposals', model: 'proposal', filterField: 'customer_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
      { label: 'Payments', model: 'payment', filterField: 'contact_id', listFields: ['amount', 'status', 'dt_payment', 'reference_number'] },
    ],
  },

  vendor: {
    key: 'vendor',
    label: 'Vendor',
    labelPlural: 'Vendors',
    color: '#6f42c1',
    listFields: [F.id, F.displayName, F.status, F.email, F.phone, F.addressFull],
    headerFields: [F.displayName, F.status, F.email, F.phone],
    formFields: [F.displayName, F.attention, F.email, F.phone, F.domain, F.addressFull, F.terms, F.status],
    publishFields: ['display_name', 'email', 'phone'],
    actions: [
      { label: 'New PO', model: 'purchase', variant: 'primary' },
      { label: 'AP Statement', route: '/transactions/vendor-statement/{id}' },
    ],
    related: [
      { label: 'Purchases', model: 'purchase', filterField: 'vendor_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
      { label: 'Disbursements', model: 'payment', filterField: 'contact_id', listFields: ['amount', 'status', 'dt_payment', 'type'] },
      { label: 'Items Supplied', model: 'org_item', filterField: 'orgbase_id', listFields: ['item_ida', 'description', 'availability'] },
    ],
  },

  manufacturer: {
    key: 'manufacturer',
    label: 'Manufacturer',
    labelPlural: 'Manufacturers',
    color: '#198754',
    listFields: [F.id, F.displayName, F.status, F.email, F.phone, F.addressFull],
    headerFields: [F.displayName, F.status, F.email, F.phone],
    formFields: [F.displayName, F.attention, F.email, F.phone, F.domain, F.addressFull, F.status],
    publishFields: ['display_name', 'domain'],
    actions: [
      { label: 'New PO', model: 'purchase', variant: 'primary' },
    ],
    related: [
      { label: 'Items', model: 'org_item', filterField: 'orgbase_id', listFields: ['item_ida', 'description', 'availability'] },
      { label: 'Purchases', model: 'purchase', filterField: 'manufacturer_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
    ],
  },

  employee: {
    key: 'employee',
    label: 'Employee',
    labelPlural: 'Employees',
    color: '#fd7e14',
    listFields: [F.id, F.displayName, F.status, F.email, F.phone],
    headerFields: [F.displayName, F.status, F.email, F.phone],
    formFields: [F.displayName, F.attention, F.email, F.phone, F.addressFull, F.status],
    publishFields: ['display_name', 'email', 'phone'],
    actions: [
      { label: 'Assign Task', model: 'action' },
    ],
    related: [
      { label: 'Tasks', model: 'action', filterField: 'contact_id', listFields: ['action', 'status', 'kanban_column', 'priority', 'dt_deadline'] },
      { label: 'Work Orders', model: 'work_order', filterField: 'contact_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
    ],
  },

  rep: {
    key: 'rep',
    label: 'Rep',
    labelPlural: 'Reps',
    color: '#dc3545',
    listFields: [F.id, F.displayName, F.status, F.email, F.phone],
    headerFields: [F.displayName, F.status, F.email, F.phone],
    formFields: [F.displayName, F.attention, F.email, F.phone, F.domain, F.addressFull, F.status],
    publishFields: ['display_name', 'email', 'phone'],
    actions: [
      { label: 'Commission Report', route: '/reports/commission/{id}' },
    ],
    related: [
      { label: 'Orders (as Rep)', model: 'order', filterField: 'rep_id', listFields: ['ida', 'status', 'total', 'dt_created'] },
      { label: 'Customers', model: 'customer', filterField: 'rep_id', listFields: ['display_name', 'status', 'email'] },
    ],
  },
};

export const getOrgConfig = (orgType: string): OrgTypeConfig | null =>
  ORG_CONFIGS[orgType] || null;

export const ALL_ORG_TYPES = Object.keys(ORG_CONFIGS);
