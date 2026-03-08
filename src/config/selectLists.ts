/**
 * selectLists.ts — Typed select/picklist definitions (r25 source of truth)
 *
 * Replaces the legacy `staticLists.ts` with a typed, structured system.
 * Each list has:
 *   - key:      Stable identifier (used in config sync)
 *   - label:    Human-readable name for admin UI
 *   - options:  Array of { value, label } pairs
 *   - editable: Whether admins can modify this list at runtime
 *
 * Static lists (editable: false) ship with the build and never change.
 * Dynamic lists (editable: true) can be overridden from wc3 setting records
 * and are synced back when admins save changes.
 *
 * Backed up to wc3 via the config sync mechanism (see useAppConfig).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectListDef {
  key: string;
  label: string;
  options: SelectOption[];
  editable: boolean;
  /** Optional: restrict this list to a specific model context */
  model?: string;
  /** Optional: the field this list populates */
  field?: string;
}

// ---------------------------------------------------------------------------
// Helper to convert [value, label] tuples → SelectOption[]
// ---------------------------------------------------------------------------

function toOptions(pairs: [string, string][]): SelectOption[] {
  return pairs.map(([value, label]) => ({ value, label }));
}

function fromValues(values: string[]): SelectOption[] {
  return values.map((v) => ({ value: v, label: v }));
}

// ---------------------------------------------------------------------------
// Static lists (never editable — ship with build)
// ---------------------------------------------------------------------------

export const STATIC_LISTS: SelectListDef[] = [
  {
    key: 'type_contact',
    label: 'type',
    editable: false,
    options: fromValues([
      'retailer','wholesaler','distributor','contractor','end_customer','other','reseller','partner','vendor','prospect','lead','friend','internal','government','non_profit','press','analyst','investor','other',
    ]),
  },
 // contact.prefs.profiles.type["friend","press"]
 
 
 
  {
    key: 'states',
    label: 'US States',
    editable: false,
    options: fromValues([
      'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI',
      'ID','IN','IL','IA','KS','KY','LA','ME','MD','MA','MI','MN',
      'MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH',
      'OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA',
      'WV','WI','WY',
    ]),
  },
  {
    key: 'importance',
    label: 'Importance Levels',
    editable: false,
    options: toOptions([
      ['Emergency', 'Emergency'],
      ['High', 'High'],
      ['Medium', 'Medium'],
      ['Low', 'Low'],
      ['Objective', 'Objective'],
    ]),
  },
  {
    key: 'data_true_false',
    label: 'True / False',
    editable: false,
    options: toOptions([
      ['true', 'true'],
      ['false', 'false'],
    ]),
  },
  {
    key: 'data_yes_no',
    label: 'Yes / No',
    editable: false,
    options: toOptions([
      ['yes', 'Yes'],
      ['no', 'No'],
    ]),
  },
];

// ---------------------------------------------------------------------------
// Dynamic lists (editable — defaults here, overridden from wc3 at runtime)
// ---------------------------------------------------------------------------

export const DYNAMIC_LISTS: SelectListDef[] = [
  {
    key: 'terms',
    label: 'Payment Terms',
    editable: true,
    options: toOptions([
      ['N30', 'Net 30 days'],
      ['N30_2%N10', 'Net 30, 2% discount Net 10'],
      ['3Payments30Days', '3 Payments every 30 days'],
      ['Dec1', 'Due Dec 1'],
      ['On Order', 'Payment due on order'],
      ['Net 60', 'Net 60 days'],
      ['Net 90', 'Net 90 days'],
      ['COD', 'Cash on Delivery'],
      ['Prepaid', 'Payment in advance'],
      ['Due on Receipt', 'Due on Receipt'],
    ]),
  },
  {
    key: 'status',
    label: 'Record Status',
    editable: true,
    options: toOptions([
      ['active', 'Active'],
      ['staged', 'Staged'],
      ['completed', 'Completed'],
      ['cancelled', 'Cancelled'],
      ['on_hold', 'On Hold'],
    ]),
  },
  {
    key: 'priority',
    label: 'Priority',
    editable: true,
    options: toOptions([
      ['standard', 'Standard'],
      ['rush', 'Rush'],
      ['urgent', 'Urgent'],
      ['low', 'Low'],
    ]),
  },
  {
    key: 'price_level',
    label: 'Price Level',
    editable: true,
    options: toOptions([
      ['retail', 'Retail'],
      ['wholesale', 'Wholesale'],
      ['distributor', 'Distributor'],
      ['employee', 'Employee'],
      ['sample', 'Sample'],
    ]),
  },
  {
    key: 'sale_juris_source',
    label: 'Sale Jurisdiction Source',
    editable: true,
    options: toOptions([
      ['Distributor', 'Distributor'],
      ['Retail', 'Retail'],
      ['Subcontract', 'Subcontract'],
      ['TrucktoCustomer', 'Truck to Customer'],
      ['TrucktoTruck', 'Truck to Truck'],
      ['Wholesale', 'Wholesale'],
    ]),
  },
  {
    key: 'ad_source',
    label: 'Ad Source',
    editable: true,
    options: [],
  },
  {
    key: 'type_sale',
    label: 'Sale Type',
    editable: true,
    options: [],
  },
  {
    key: 'contract_detail',
    label: 'Contract Detail',
    editable: true,
    options: [],
  },
  {
    key: 'reps',
    label: 'Sales Reps',
    editable: true,
    options: [],
  },
  {
    key: 'actions_orders',
    label: 'Order Actions',
    editable: true,
    field: 'actions',
    model: 'order',
    options: [],
  },
  {
    key: 'actions_invoices',
    label: 'Invoice Actions',
    editable: true,
    field: 'actions',
    model: 'invoice',
    options: [],
  },
  {
    key: 'actions_proposals',
    label: 'Proposal Actions',
    editable: true,
    field: 'actions',
    model: 'proposal',
    options: [],
  },
  {
    key: 'actions_purchases',
    label: 'Purchase Actions',
    editable: true,
    field: 'actions',
    model: 'purchase',
    options: [],
  },
  {
    key: 'tax_juris',
    label: 'Tax Jurisdictions',
    editable: true,
    options: [],
  },
  {
    key: 'job_list',
    label: 'Job Types',
    editable: true,
    options: toOptions([
      ['Job Class', 'Job Class'],
      ['*Estimate Job', '*Estimate Job'],
      ['*Sweeps Service', '*Sweeps Service'],
      ['Attic Insulation Shield/FS', 'Attic Insulation Shield/FS'],
      ['Chase Cover', 'Chase Cover'],
      ['Chimney Caps', 'Chimney Caps'],
      ['Class A Install', 'Class A Install'],
      ['Class B Install', 'Class B Install'],
      ['Firebox Repairs', 'Firebox Repairs'],
      ['FireStop Install', 'FireStop Install'],
      ['Flashings/Crickets', 'Flashings/Crickets'],
      ['Gas Insert', 'Gas Insert'],
      ['Gas Log Installs', 'Gas Log Installs'],
      ['Gas Stove', 'Gas Stove'],
      ['level Three Inspect', 'level Three Inspect'],
      ['New Const Gas FP', 'New Const Gas FP'],
      ['New Const Masonry', 'New Const Masonry'],
      ['New Const Wood FP', 'New Const Wood FP'],
      ['Pellet Insert', 'Pellet Insert'],
      ['Pellet Stove', 'Pellet Stove'],
      ['Plaster & Paint', 'Plaster & Paint'],
      ['R&R Brick Chimneys', 'R&R Brick Chimneys'],
      ['R&R Gas FP', 'R&R Gas FP'],
      ['R&R Wood Chases', 'R&R Wood Chases'],
      ['R&R Wood FP', 'R&R Wood FP'],
      ['Recrown', 'Recrown'],
      ['Reface FirePlace', 'Reface FirePlace'],
      ['Reline Gas', 'Reline Gas'],
      ['Reline Wood', 'Reline Wood'],
      ['Run Gas Line', 'Run Gas Line'],
      ['Water Repellant', 'Water Repellant'],
      ['Wood Insert', 'Wood Insert'],
      ['Wood Stove', 'Wood Stove'],
    ]),
  },
  {
    key: 'qa_type',
    label: 'QA Types',
    editable: true,
    options: toOptions([
      ['Dryer-Vent', 'Dryer-Vent'],
      ['Gas-Service-Call', 'Gas-Service-Call'],
      ['Inspection-Level-2', 'Inspection-Level-2'],
      ['Job-Setup', 'Job-Setup'],
      ['Pellet-Stove', 'Pellet-Stove'],
    ]),
  },
];

// ---------------------------------------------------------------------------
// Combined registry — keyed for O(1) access
// ---------------------------------------------------------------------------

const ALL_LISTS = [...STATIC_LISTS, ...DYNAMIC_LISTS];

// ---------------------------------------------------------------------------
// wc3 Term Records — maps term name/id to full metadata
// Sync'd from wc3 accounts.Term table (10 records as of 2026-03-08)
// Canonical source: wc3 sync_terms management command
// ---------------------------------------------------------------------------

export interface TermRecord {
  id: number;
  name: string;
  description: string;
  daysDue: number;
  discountRate: number | null;
  daysDiscount: number | null;
  periodCount: number;
  daysInPeriod: number | null;
}

export const TERM_RECORDS: TermRecord[] = [
  { id: 1,  name: 'N30',              description: 'Net 30 days',                   daysDue: 30, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 2,  name: 'N30_2%N10',        description: 'Net 30, 2% discount Net 10',    daysDue: 30, discountRate: 2.0,  daysDiscount: 10,   periodCount: 1, daysInPeriod: null },
  { id: 3,  name: '3Payments30Days',  description: '3 Payments every 30 days',      daysDue: 30, discountRate: null, daysDiscount: null, periodCount: 3, daysInPeriod: 30   },
  { id: 4,  name: 'Dec1',             description: 'Due Dec 1',                     daysDue:  1, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 5,  name: 'On Order',         description: 'Payment due on order',          daysDue:  0, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 6,  name: 'Net 60',           description: 'Net 60 days',                   daysDue: 60, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 7,  name: 'Net 90',           description: 'Net 90 days',                   daysDue: 90, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 8,  name: 'COD',              description: 'Cash on Delivery',              daysDue:  0, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 9,  name: 'Prepaid',          description: 'Payment in advance',            daysDue:  0, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
  { id: 10, name: 'Due on Receipt',   description: 'Due on Receipt',                daysDue:  0, discountRate: null, daysDiscount: null, periodCount: 1, daysInPeriod: null },
];

/** Lookup term record by name (e.g. "N30") */
export function getTermByName(name: string): TermRecord | undefined {
  return TERM_RECORDS.find((t) => t.name === name);
}

/** Lookup term record by wc3 ID */
export function getTermById(id: number): TermRecord | undefined {
  return TERM_RECORDS.find((t) => t.id === id);
}

// ---------------------------------------------------------------------------

/** Lookup table: key → SelectListDef */
export const SELECT_LIST_MAP: Record<string, SelectListDef> = Object.fromEntries(
  ALL_LISTS.map((l) => [l.key, l]),
);

/**
 * Get a select list by key. Returns the list definition or undefined.
 */
export function getSelectList(key: string): SelectListDef | undefined {
  return SELECT_LIST_MAP[key];
}

/**
 * Get options for a select list key, with optional wc3-override map applied.
 * Used by the configSlice merge logic.
 */
export function getSelectOptions(key: string): SelectOption[] {
  return SELECT_LIST_MAP[key]?.options ?? [];
}

/**
 * Convert SelectOption[] to the legacy [value, label][] format
 * for backward compatibility with staticLists consumers.
 */
export function toLegacyPairs(options: SelectOption[]): [string, string][] {
  return options.map((o) => [o.value, o.label]);
}

/**
 * All editable (dynamic) list keys — used by sync to know what to push to wc3.
 */
export function editableListKeys(): string[] {
  return DYNAMIC_LISTS.map((l) => l.key);
}
