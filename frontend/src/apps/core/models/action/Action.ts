/* LastChecked: 2026-09-09 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Claude */
// WC3 ↔ R25 TypeScript alignment interface for Action
// Mirrors Pydantic schemas: common/schemas/action.py

// ── action.config.times — clock in/out entries (mirrors ActionTimes) ───

/** One clock-in / clock-out span. Mirrors TimeEntry in action.py. */
export interface TimeEntry {
  id: string;                              // uuid
  who?: number | null;                     // contact_id of person logging time
  dt_in?: number | null;                   // epoch ms — clock in
  dt_out?: number | null;                  // epoch ms — clock out (null = still clocked in)
  elapsed_ms?: number | null;              // dt_out - dt_in (computed on clock-out)
  percent_active?: number;                 // 0-100, default 100
  reason?: string;                         // what this time span was for
  notes?: string;                          // freeform detail
  tags?: string[];                         // industry/task tags
  issue?: string | null;                   // interruption, delay, problem
  [key: string]: unknown;                  // extra="allow" — industry extensions
}

/** action.config.times — time tracking for any action. Mirrors ActionTimes. */
export interface ActionTimes {
  entries: TimeEntry[];
  total_elapsed_ms?: number | null;        // sum of entries[].elapsed_ms
  total_active_ms?: number | null;         // sum adjusted by percent_active
}

// ── action.config.billable — billing configuration (mirrors ActionBillable) ─

/** action.config.billable — the money side. Mirrors ActionBillable in action.py. */
export interface ActionBillable {
  // who is billed
  customer_id?: number | null;             // billing party (customer record)
  contact_id?: number | null;              // specific person on the account
  company?: string;                        // display name (denormalized)
  attention?: string;                      // attention line on invoice

  // rate
  is_billable?: boolean;                   // default true
  rate?: number | null;                    // per rate_unit
  rate_unit?: string;                      // "hour" | "day" | "flat" | "unit"
  currency?: string;                       // default "USD"

  // categorization
  skill_category?: string;                 // journeyman_plumber, electrician, etc.
  activity?: string;                       // installation, service, consultation, etc.

  // estimates vs actuals
  hours_estimated?: number | null;
  hours_actual?: number | null;
  total_estimated?: number | null;         // rate * hours_estimated (or flat amount)
  total_actual?: number | null;            // rate * hours_actual (or flat amount)
  variance_pct?: number | null;            // ((actual - estimated) / estimated) * 100

  // product set
  product_set?: number[];                  // Item IDs that this labor applies to

  // invoice linkage
  invoice_id?: number | null;
  invoice_line?: number | null;

  // Alice learning signal
  estimate_source?: string | null;         // "alice" | "user" | "historical"
  estimate_confidence?: number | null;     // 1-10

  [key: string]: unknown;                  // extra="allow" — industry extensions
}

// ── action.config — mirrors ActionConfig ────────────────────────────────

export interface ActionConfig {
  times?: ActionTimes | null;
  billable?: ActionBillable | null;
  [key: string]: unknown;                  // ConfigBase allows model-specific fields
}

// ── Action record ───────────────────────────────────────────────────────

export interface Action {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  action_id?: string;
  action?: Record<string, string>;
  description?: Record<string, string>;
  languages?: string[];
  assigned_to?: Array<{ id: number; name: string; email?: string }>;
  contact_id?: number;
  project_name?: string;
  project_id?: number;
  project_metadata?: Record<string, any>;
  linkage?: number;
  sequence?: number;
  kanban_column?: string;
  priority?: number;
  difficulty?: number;
  status?: string;
  percent_complete?: number;
  burndown?: number;
  dt_start?: number;
  dt_expected?: number;
  dt_deadline?: number;
  dt_completed?: number;
  dt_updated?: number;
  duration?: number;
  created_by?: Array<any>;
  updated_by?: Array<any>;
  expected_by?: Array<any>;
  due_by?: Array<any>;
  completed_by?: Array<any>;
  start_by?: Array<any>;
  end_by?: Array<any>;
  config?: ActionConfig;
  impact?: Record<string, any>;
  retrospection?: Record<string, any>;
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  actions?: Record<string, any>;
  health_rating?: number;
}
