/**
 * AUTO-GENERATED — DO NOT EDIT
 *
 * TypeScript interfaces generated from Django model definitions.
 * Source: webClerk3 WCAPI_BLESSED_MODELS
 * Generated: 2026-02-15 16:55
 *
 * Regenerate with:
 *   cd webClerk3 && python manage.py generate_ts_types \
 *     --out ../React2025/src/generated/modelTypes.ts
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

// ============================================================
// ACCOUNTS
// ============================================================

// ── Currency ──
// Django: accounts.Currency  table: acct_currencies
// wcapi model_name: "currency"

export interface CurrencyRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  code: string;  // max_length=10
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=64
  precision: number;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  symbol?: string | null;  // max_length=8
  version: number;  // read-only
}

export interface CreateCurrencyRequest {
  ida?: string;  // max_length=40
  code: string;  // max_length=10
  is_active?: boolean;
  name?: string | null;  // max_length=64
  precision?: number;
  symbol?: string | null;  // max_length=8
}

export interface UpdateCurrencyRequest {
  id: number | string;
  ida?: string;  // max_length=40
  code?: string;  // max_length=10
  is_active?: boolean;
  name?: string | null;  // max_length=64
  precision?: number;
  symbol?: string | null;  // max_length=8
}

// ── ExchangeRate ──
// Django: accounts.ExchangeRate  table: acct_exchange_rates
// wcapi model_name: "exchange_rate"

export interface ExchangeRateRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  currency_base: string;  // max_length=10
  currency_target: string;  // max_length=10
  dt_created: number;  // read-only
  dt_end?: string | null;
  dt_modified: number;  // read-only
  dt_start?: string | null;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=255
  precision_convert: number;
  precision_display: number;
  prefs: Record<string, any>;
  rate: number | string;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateExchangeRateRequest {
  ida?: string;  // max_length=40
  currency_base?: string;  // max_length=10
  currency_target?: string;  // max_length=10
  dt_end?: string | null;
  dt_start?: string | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  precision_convert?: number;
  precision_display?: number;
  rate?: number | string;
}

export interface UpdateExchangeRateRequest {
  id: number | string;
  ida?: string;  // max_length=40
  currency_base?: string;  // max_length=10
  currency_target?: string;  // max_length=10
  dt_end?: string | null;
  dt_start?: string | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  precision_convert?: number;
  precision_display?: number;
  rate?: number | string;
}

// ── ExchangeTransaction ──
// Django: accounts.ExchangeTransaction  table: acct_exchanges
// wcapi model_name: "exchange_transaction"

export interface ExchangeTransactionRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  currency_base: string;  // max_length=10
  currency_target: string;  // max_length=10
  dt_created: number;  // read-only
  dt_end?: string | null;
  dt_modified: number;  // read-only
  dt_start?: string | null;
  exchange?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=255
  precision_convert: number;
  precision_display: number;
  prefs: Record<string, any>;
  rate: number | string;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateExchangeTransactionRequest {
  ida?: string;  // max_length=40
  currency_base?: string;  // max_length=10
  currency_target?: string;  // max_length=10
  dt_end?: string | null;
  dt_start?: string | null;
  exchange?: Record<string, any>;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  precision_convert?: number;
  precision_display?: number;
  rate?: number | string;
}

export interface UpdateExchangeTransactionRequest {
  id: number | string;
  ida?: string;  // max_length=40
  currency_base?: string;  // max_length=10
  currency_target?: string;  // max_length=10
  dt_end?: string | null;
  dt_start?: string | null;
  exchange?: Record<string, any>;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  precision_convert?: number;
  precision_display?: number;
  rate?: number | string;
}

// ── GlAccount ──
// Django: accounts.GlAccount  table: gl_accounts
// wcapi model_name: "gl_account"

export interface GlAccountRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  account_credit?: string | null;  // max_length=255
  account_debit?: string | null;  // max_length=255
  account_number?: string | null;  // max_length=50
  actions?: Record<string, any>;
  category?: string | null;  // choices: cash, receivables, payables, inventory, sales, cogs, expense, other | max_length=255
  comment?: string | null;
  comments: Record<string, any>;
  division?: number | null;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=255
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  type?: string | null;  // choices: , asset, liability, equity, revenue, expense, contra | max_length=255
  type_id?: string | null;  // max_length=255
  used_for?: string | null;  // choices: posting, reporting, tax, consolidation, other | max_length=255
  version: number;  // read-only
}

export interface CreateGlAccountRequest {
  ida?: string;  // max_length=40
  account_credit?: string | null;  // max_length=255
  account_debit?: string | null;  // max_length=255
  account_number?: string | null;  // max_length=50
  category?: string | null;  // choices: cash, receivables, payables, inventory, sales, cogs, expense, other | max_length=255
  comment?: string | null;
  division?: number | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  type?: string | null;  // choices: , asset, liability, equity, revenue, expense, contra | max_length=255
  type_id?: string | null;  // max_length=255
  used_for?: string | null;  // choices: posting, reporting, tax, consolidation, other | max_length=255
}

export interface UpdateGlAccountRequest {
  id: number | string;
  ida?: string;  // max_length=40
  account_credit?: string | null;  // max_length=255
  account_debit?: string | null;  // max_length=255
  account_number?: string | null;  // max_length=50
  category?: string | null;  // choices: cash, receivables, payables, inventory, sales, cogs, expense, other | max_length=255
  comment?: string | null;
  division?: number | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  type?: string | null;  // choices: , asset, liability, equity, revenue, expense, contra | max_length=255
  type_id?: string | null;  // max_length=255
  used_for?: string | null;  // choices: posting, reporting, tax, consolidation, other | max_length=255
}

// ── Term ──
// Django: accounts.Term  table: terms
// wcapi model_name: "term"

export interface TermRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  approved_by?: string | null;  // max_length=255
  comments: Record<string, any>;
  day_cut_off_due?: number | null;
  day_cut_off_invoice?: number | null;
  days_discount?: number | null;
  days_due?: number | null;
  days_in_period?: number | null;
  description?: string | null;  // max_length=255
  discount_rate?: number | null;
  dt_begin?: string | null;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=255
  period_count?: number | null;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateTermRequest {
  ida?: string;  // max_length=40
  approved_by?: string | null;  // max_length=255
  day_cut_off_due?: number | null;
  day_cut_off_invoice?: number | null;
  days_discount?: number | null;
  days_due?: number | null;
  days_in_period?: number | null;
  description?: string | null;  // max_length=255
  discount_rate?: number | null;
  dt_begin?: string | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  period_count?: number | null;
}

export interface UpdateTermRequest {
  id: number | string;
  ida?: string;  // max_length=40
  approved_by?: string | null;  // max_length=255
  day_cut_off_due?: number | null;
  day_cut_off_invoice?: number | null;
  days_discount?: number | null;
  days_due?: number | null;
  days_in_period?: number | null;
  description?: string | null;  // max_length=255
  discount_rate?: number | null;
  dt_begin?: string | null;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  period_count?: number | null;
}

// ============================================================
// COMMUNICATIONS
// ============================================================

// ── Domain ──
// Django: communications.Domain  table: domains
// wcapi model_name: "domain"

export interface DomainRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comment?: string;
  comments: Record<string, any>;
  contact_id?: number | null;  // FK → core.Contact
  count_accessed: number;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  path?: string;  // max_length=255
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  sequence: number;
  status?: string;  // choices: , active, verifying, suspended, retired | max_length=30
  type?: string;  // choices: website, linkedin, facebook, twitter, github, other | max_length=50
  version: number;  // read-only
}

export interface CreateDomainRequest {
  ida?: string;  // max_length=40
  comment?: string;
  contact_id?: number | null;  // FK → core.Contact
  count_accessed?: number;
  is_active?: boolean;
  path?: string;  // max_length=255
  sequence?: number;
  status?: string;  // choices: , active, verifying, suspended, retired | max_length=30
  type?: string;  // choices: website, linkedin, facebook, twitter, github, other | max_length=50
}

export interface UpdateDomainRequest {
  id: number | string;
  ida?: string;  // max_length=40
  comment?: string;
  contact_id?: number | null;  // FK → core.Contact
  count_accessed?: number;
  is_active?: boolean;
  path?: string;  // max_length=255
  sequence?: number;
  status?: string;  // choices: , active, verifying, suspended, retired | max_length=30
  type?: string;  // choices: website, linkedin, facebook, twitter, github, other | max_length=50
}

// ── Email ──
// Django: communications.Email  table: emails
// wcapi model_name: "email"

export interface EmailRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  attention?: string;  // max_length=100
  comments: Record<string, any>;
  contact_id?: number | null;  // FK → core.Contact
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email: string;  // max_length=254
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  is_primary: boolean;
  is_verified: boolean;
  metadata: Record<string, any>;
  name?: string;  // max_length=100
  opt_out?: string;  // choices: , opted_out, bounced, invalid, spam_complaint | max_length=20
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  type?: string;  // choices: , work, personal, support, billing, other | max_length=50
  version: number;  // read-only
}

export interface CreateEmailRequest {
  ida?: string;  // max_length=40
  attention?: string;  // max_length=100
  contact_id?: number | null;  // FK → core.Contact
  email: string;  // max_length=254
  is_active?: boolean;
  is_primary?: boolean;
  is_verified?: boolean;
  name?: string;  // max_length=100
  opt_out?: string;  // choices: , opted_out, bounced, invalid, spam_complaint | max_length=20
  type?: string;  // choices: , work, personal, support, billing, other | max_length=50
}

export interface UpdateEmailRequest {
  id: number | string;
  ida?: string;  // max_length=40
  attention?: string;  // max_length=100
  contact_id?: number | null;  // FK → core.Contact
  email?: string;  // max_length=254
  is_active?: boolean;
  is_primary?: boolean;
  is_verified?: boolean;
  name?: string;  // max_length=100
  opt_out?: string;  // choices: , opted_out, bounced, invalid, spam_complaint | max_length=20
  type?: string;  // choices: , work, personal, support, billing, other | max_length=50
}

// ── Location ──
// Django: communications.Address  table: locations
// wcapi model_name: "location"

export interface LocationRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address1?: string;  // max_length=255
  address2?: string;  // max_length=255
  address_type?: string;  // max_length=255
  city?: string;  // max_length=255
  comments: Record<string, any>;
  contact_id?: number | null;  // FK → core.Contact
  country?: string;  // max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  full?: string;  // max_length=1000
  health_rating: number;
  instructions?: string;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  latitude?: number | null;
  longitude?: number | null;
  metadata: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  state?: string;  // max_length=255
  version: number;  // read-only
  zip?: string;  // max_length=255
}

export interface CreateLocationRequest {
  ida?: string;  // max_length=40
  address1?: string;  // max_length=255
  address2?: string;  // max_length=255
  address_type?: string;  // max_length=255
  city?: string;  // max_length=255
  contact_id?: number | null;  // FK → core.Contact
  country?: string;  // max_length=255
  full?: string;  // max_length=1000
  instructions?: string;
  is_active?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  state?: string;  // max_length=255
  zip?: string;  // max_length=255
}

export interface UpdateLocationRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address1?: string;  // max_length=255
  address2?: string;  // max_length=255
  address_type?: string;  // max_length=255
  city?: string;  // max_length=255
  contact_id?: number | null;  // FK → core.Contact
  country?: string;  // max_length=255
  full?: string;  // max_length=1000
  instructions?: string;
  is_active?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  state?: string;  // max_length=255
  zip?: string;  // max_length=255
}

// ── Phone ──
// Django: communications.Phone  table: phones
// wcapi model_name: "phone"

export interface PhoneRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  attention?: string;  // max_length=100
  comments: Record<string, any>;
  contact_id?: number | null;  // FK → core.Contact
  country_code?: string;  // max_length=5
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  format?: string;  // max_length=50
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string;  // max_length=100
  number?: string;  // max_length=20
  opt_out: boolean;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreatePhoneRequest {
  ida?: string;  // max_length=40
  attention?: string;  // max_length=100
  contact_id?: number | null;  // FK → core.Contact
  country_code?: string;  // max_length=5
  format?: string;  // max_length=50
  is_active?: boolean;
  name?: string;  // max_length=100
  number?: string;  // max_length=20
  opt_out?: boolean;
}

export interface UpdatePhoneRequest {
  id: number | string;
  ida?: string;  // max_length=40
  attention?: string;  // max_length=100
  contact_id?: number | null;  // FK → core.Contact
  country_code?: string;  // max_length=5
  format?: string;  // max_length=50
  is_active?: boolean;
  name?: string;  // max_length=100
  number?: string;  // max_length=20
  opt_out?: boolean;
}

// ============================================================
// CORE
// ============================================================

// ── Action ──
// Django: core.Action  table: actions
// wcapi model_name: "action"

export interface ActionRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  action?: Record<string, any>;
  action_id_id?: number | null;  // FK → core.Action
  actions?: Record<string, any>;
  assigned_to?: Record<string, any>;
  burndown: number;
  comments: Record<string, any>;
  completed_by?: Record<string, any>;
  contact_id: number;
  created_by?: Record<string, any>;
  deadline_by?: Record<string, any>;
  description?: Record<string, any>;
  difficulty: number;  // choices: None, 100, 50, 15, 10, 4, 1
  dt_completed?: number | null;
  dt_created: number;  // read-only
  dt_deadline?: number | null;
  dt_end_original?: number | null;
  dt_expected?: number | null;
  dt_modified: number;  // read-only
  dt_start?: number | null;
  dt_start_original?: number | null;
  dt_updated: number;
  duration?: number | null;
  end_by?: Record<string, any>;
  expected_by?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  kanban_column: string;  // choices: , Backlog, Planning, InProcess, Review, Complete | max_length=50
  languages?: Record<string, any>;
  linkage: number;
  metadata: Record<string, any>;
  percent_complete: number;
  prefs: Record<string, any>;
  priority: number;
  project_id: number;
  project_ida?: string | null;  // max_length=255
  project_metadata?: Record<string, any>;
  project_name?: string | null;  // max_length=255
  refs: Record<string, any>;
  security_level?: number;
  sequence: number;
  start_by?: Record<string, any>;
  status?: string | null;  // max_length=100
  updated_by?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateActionRequest {
  ida?: string;  // max_length=40
  action?: Record<string, any>;
  action_id_id?: number | null;  // FK → core.Action
  assigned_to?: Record<string, any>;
  burndown?: number;
  completed_by?: Record<string, any>;
  contact_id?: number;
  created_by?: Record<string, any>;
  deadline_by?: Record<string, any>;
  description?: Record<string, any>;
  difficulty?: number;  // choices: None, 100, 50, 15, 10, 4, 1
  dt_completed?: number | null;
  dt_deadline?: number | null;
  dt_end_original?: number | null;
  dt_expected?: number | null;
  dt_start?: number | null;
  dt_start_original?: number | null;
  dt_updated?: number;
  duration?: number | null;
  end_by?: Record<string, any>;
  expected_by?: Record<string, any>;
  is_active?: boolean;
  kanban_column?: string;  // choices: , Backlog, Planning, InProcess, Review, Complete | max_length=50
  languages?: Record<string, any>;
  linkage?: number;
  percent_complete?: number;
  priority?: number;
  project_id?: number;
  project_ida?: string | null;  // max_length=255
  project_metadata?: Record<string, any>;
  project_name?: string | null;  // max_length=255
  sequence?: number;
  start_by?: Record<string, any>;
  status?: string | null;  // max_length=100
  updated_by?: Record<string, any>;
}

export interface UpdateActionRequest {
  id: number | string;
  ida?: string;  // max_length=40
  action?: Record<string, any>;
  action_id_id?: number | null;  // FK → core.Action
  assigned_to?: Record<string, any>;
  burndown?: number;
  completed_by?: Record<string, any>;
  contact_id?: number;
  created_by?: Record<string, any>;
  deadline_by?: Record<string, any>;
  description?: Record<string, any>;
  difficulty?: number;  // choices: None, 100, 50, 15, 10, 4, 1
  dt_completed?: number | null;
  dt_deadline?: number | null;
  dt_end_original?: number | null;
  dt_expected?: number | null;
  dt_start?: number | null;
  dt_start_original?: number | null;
  dt_updated?: number;
  duration?: number | null;
  end_by?: Record<string, any>;
  expected_by?: Record<string, any>;
  is_active?: boolean;
  kanban_column?: string;  // choices: , Backlog, Planning, InProcess, Review, Complete | max_length=50
  languages?: Record<string, any>;
  linkage?: number;
  percent_complete?: number;
  priority?: number;
  project_id?: number;
  project_ida?: string | null;  // max_length=255
  project_metadata?: Record<string, any>;
  project_name?: string | null;  // max_length=255
  sequence?: number;
  start_by?: Record<string, any>;
  status?: string | null;  // max_length=100
  updated_by?: Record<string, any>;
}

// ── Audit ──
// Django: core.AuditLog  table: audit_logs
// wcapi model_name: "audit"

export interface AuditRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  action: string;  // max_length=50
  actions?: Record<string, any>;
  changes: Record<string, any>;
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  id_session?: string;  // max_length=255
  ip_address?: string | null;  // max_length=39
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  model_name: string;  // max_length=100
  prefs: Record<string, any>;
  record_id: number;
  refs: Record<string, any>;
  security_level?: number;
  user_agent?: string;
  user_id_id?: number | null;  // FK → core.Contact
  version: number;  // read-only
}

export interface CreateAuditRequest {
  ida?: string;  // max_length=40
  action: string;  // max_length=50
  changes?: Record<string, any>;
  id_session?: string;  // max_length=255
  ip_address?: string | null;  // max_length=39
  is_active?: boolean;
  model_name: string;  // max_length=100
  record_id: number;
  user_agent?: string;
  user_id_id?: number | null;  // FK → core.Contact
}

export interface UpdateAuditRequest {
  id: number | string;
  ida?: string;  // max_length=40
  action?: string;  // max_length=50
  changes?: Record<string, any>;
  id_session?: string;  // max_length=255
  ip_address?: string | null;  // max_length=39
  is_active?: boolean;
  model_name?: string;  // max_length=100
  record_id?: number;
  user_agent?: string;
  user_id_id?: number | null;  // FK → core.Contact
}

// ── Contact ──
// Django: core.Contact  table: contacts
// wcapi model_name: "contact"

export interface ContactRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  attention?: string;  // max_length=201
  comment?: string;
  comments: Record<string, any>;
  company?: string;  // max_length=200
  customer_id?: number | null;  // FK → orgs.OrgBase
  department?: string;  // max_length=100
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  dt_created: number;  // read-only
  dt_joined: string;  // read-only
  dt_modified: number;  // read-only
  email: string;  // max_length=254
  email_id?: number | null;
  employee_id?: number | null;  // FK → orgs.OrgBase
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  last_login?: string | null;  // read-only
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  name_first?: string;  // max_length=100
  name_last?: string;  // max_length=100
  name_middle?: string;  // max_length=100
  name_prefix?: string;  // max_length=20
  name_suffix?: string;  // max_length=20
  other_id?: number | null;
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  rep_id?: number | null;  // FK → orgs.OrgBase
  role: string;  // choices: , user, employee, admin | max_length=50
  security_level?: number;
  title?: string;  // max_length=100
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateContactRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  attention?: string;  // max_length=201
  comment?: string;
  company?: string;  // max_length=200
  customer_id?: number | null;  // FK → orgs.OrgBase
  department?: string;  // max_length=100
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  email: string;  // max_length=254
  email_id?: number | null;
  employee_id?: number | null;  // FK → orgs.OrgBase
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  name_first?: string;  // max_length=100
  name_last?: string;  // max_length=100
  name_middle?: string;  // max_length=100
  name_prefix?: string;  // max_length=20
  name_suffix?: string;  // max_length=20
  other_id?: number | null;
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  rep_id?: number | null;  // FK → orgs.OrgBase
  role?: string;  // choices: , user, employee, admin | max_length=50
  title?: string;  // max_length=100
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateContactRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  attention?: string;  // max_length=201
  comment?: string;
  company?: string;  // max_length=200
  customer_id?: number | null;  // FK → orgs.OrgBase
  department?: string;  // max_length=100
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  email?: string;  // max_length=254
  email_id?: number | null;
  employee_id?: number | null;  // FK → orgs.OrgBase
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  name_first?: string;  // max_length=100
  name_last?: string;  // max_length=100
  name_middle?: string;  // max_length=100
  name_prefix?: string;  // max_length=20
  name_suffix?: string;  // max_length=20
  other_id?: number | null;
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  rep_id?: number | null;  // FK → orgs.OrgBase
  role?: string;  // choices: , user, employee, admin | max_length=50
  title?: string;  // max_length=100
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── Notification ──
// Django: core.Notification  table: notifications
// wcapi model_name: "notification"

export interface NotificationRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  data: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  prefs: Record<string, any>;
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateNotificationRequest {
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

export interface UpdateNotificationRequest {
  id: number | string;
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

// ── Pending ──
// Django: core.Pending  table: pending
// wcapi model_name: "pending"

export interface PendingRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  data: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  dt_processed: number;
  is_active: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=120
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
  security_level?: number;
  version: number;  // read-only
}

export interface CreatePendingRequest {
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  dt_processed?: number;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=120
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

export interface UpdatePendingRequest {
  id: number | string;
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  dt_processed?: number;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=120
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

// ── Report ──
// Django: core.Report  table: reports
// wcapi model_name: "report"

export interface ReportRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  data: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  prefs: Record<string, any>;
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateReportRequest {
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

export interface UpdateReportRequest {
  id: number | string;
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=120
  record_id?: string | null;  // max_length=255
}

// ── Setting ──
// Django: core.Setting  table: settings
// wcapi model_name: "setting"

export interface SettingRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  data?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=255
  parent_model?: string | null;  // max_length=255
  prefs: Record<string, any>;
  purpose?: string | null;  // choices: , view_edit, constants, db_defaults, sales_defaults, purchase_defaults, accounting_defaults, keywords | max_length=255
  refs: Record<string, any>;
  role?: string | null;  // max_length=255
  security_level?: number;
  version: number;  // read-only
}

export interface CreateSettingRequest {
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  parent_model?: string | null;  // max_length=255
  purpose?: string | null;  // choices: , view_edit, constants, db_defaults, sales_defaults, purchase_defaults, accounting_defaults, keywords | max_length=255
  role?: string | null;  // max_length=255
}

export interface UpdateSettingRequest {
  id: number | string;
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  is_active?: boolean;
  name?: string | null;  // max_length=255
  parent_model?: string | null;  // max_length=255
  purpose?: string | null;  // choices: , view_edit, constants, db_defaults, sales_defaults, purchase_defaults, accounting_defaults, keywords | max_length=255
  role?: string | null;  // max_length=255
}

// ── Template ──
// Django: core.Template  table: templates
// wcapi model_name: "template"

export interface TemplateRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  data: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  dt_processed: number;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name?: string | null;  // max_length=120
  prefs: Record<string, any>;
  purpose?: string | null;  // max_length=120
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateTemplateRequest {
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  dt_processed?: number;
  is_active?: boolean;
  name?: string | null;  // max_length=120
  purpose?: string | null;  // max_length=120
}

export interface UpdateTemplateRequest {
  id: number | string;
  ida?: string;  // max_length=40
  data?: Record<string, any>;
  dt_processed?: number;
  is_active?: boolean;
  name?: string | null;  // max_length=120
  purpose?: string | null;  // max_length=120
}

// ============================================================
// DOCS
// ============================================================

// ── Document ──
// Django: docs.Document  table: documents
// wcapi model_name: "document"

export interface DocumentRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  body?: string | null;
  checksum?: string | null;  // max_length=255
  comment?: string;
  comments: Record<string, any>;
  confidential?: string | null;  // choices: , public, internal, restricted, confidential, secret | max_length=255
  copyright?: Record<string, any>;
  count_accessed: number;
  data?: Record<string, any>;
  description?: string | null;  // max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  mime_type?: string | null;  // max_length=255
  model_name?: string | null;  // choices: , readme, policy, spec, contract, template | max_length=255
  name?: string | null;  // max_length=255
  path?: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  retention_period?: number | null;
  search_vector?: any;  // read-only
  security_level?: number;
  sequence?: number | null;
  size_bytes?: number | null;
  slug?: string | null;  // max_length=255
  status?: string | null;  // choices: , draft, in_review, published, archived, retired | max_length=255
  version: number;  // read-only
}

export interface CreateDocumentRequest {
  ida?: string;  // max_length=40
  body?: string | null;
  checksum?: string | null;  // max_length=255
  comment?: string;
  confidential?: string | null;  // choices: , public, internal, restricted, confidential, secret | max_length=255
  copyright?: Record<string, any>;
  count_accessed?: number;
  data?: Record<string, any>;
  description?: string | null;  // max_length=255
  is_active?: boolean;
  mime_type?: string | null;  // max_length=255
  model_name?: string | null;  // choices: , readme, policy, spec, contract, template | max_length=255
  name?: string | null;  // max_length=255
  path?: Record<string, any>;
  retention_period?: number | null;
  sequence?: number | null;
  size_bytes?: number | null;
  slug?: string | null;  // max_length=255
  status?: string | null;  // choices: , draft, in_review, published, archived, retired | max_length=255
}

export interface UpdateDocumentRequest {
  id: number | string;
  ida?: string;  // max_length=40
  body?: string | null;
  checksum?: string | null;  // max_length=255
  comment?: string;
  confidential?: string | null;  // choices: , public, internal, restricted, confidential, secret | max_length=255
  copyright?: Record<string, any>;
  count_accessed?: number;
  data?: Record<string, any>;
  description?: string | null;  // max_length=255
  is_active?: boolean;
  mime_type?: string | null;  // max_length=255
  model_name?: string | null;  // choices: , readme, policy, spec, contract, template | max_length=255
  name?: string | null;  // max_length=255
  path?: Record<string, any>;
  retention_period?: number | null;
  sequence?: number | null;
  size_bytes?: number | null;
  slug?: string | null;  // max_length=255
  status?: string | null;  // choices: , draft, in_review, published, archived, retired | max_length=255
}

// ── Linkage ──
// Django: docs.LinkageEntry  table: linkage_entries
// wcapi model_name: "linkage"

export interface LinkageRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  group_id: number;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  model_name: string;  // max_length=255
  name?: string | null;  // max_length=255
  note?: string;
  prefs: Record<string, any>;
  purpose?: string | null;  // max_length=255
  record_id: number;
  refs: Record<string, any>;
  role?: string | null;  // max_length=100
  security_level?: number;
  sequence: number;
  version: number;  // read-only
}

export interface CreateLinkageRequest {
  ida?: string;  // max_length=40
  group_id: number;
  is_active?: boolean;
  model_name: string;  // max_length=255
  name?: string | null;  // max_length=255
  note?: string;
  purpose?: string | null;  // max_length=255
  record_id: number;
  role?: string | null;  // max_length=100
  sequence?: number;
}

export interface UpdateLinkageRequest {
  id: number | string;
  ida?: string;  // max_length=40
  group_id?: number;
  is_active?: boolean;
  model_name?: string;  // max_length=255
  name?: string | null;  // max_length=255
  note?: string;
  purpose?: string | null;  // max_length=255
  record_id?: number;
  role?: string | null;  // max_length=100
  sequence?: number;
}

// ── QuestionAnswer ──
// Django: docs.QuestionAnswer  table: qas
// wcapi model_name: "question_answer"

export interface QuestionAnswerRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  answer?: string | null;  // max_length=500
  answer_id?: number | null;
  answered_by?: Record<string, any>;
  comments: Record<string, any>;
  count_accessed: number;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // max_length=100
  prefs: Record<string, any>;
  question?: string | null;  // max_length=500
  question_id?: number | null;
  refs: Record<string, any>;
  search_vector?: any;  // read-only
  security_level?: number;
  sequence: number;
  setting_id_id?: number | null;  // FK → core.Setting
  status?: string | null;  // max_length=100
  version: number;  // read-only
}

export interface CreateQuestionAnswerRequest {
  ida?: string;  // max_length=40
  answer?: string | null;  // max_length=500
  answer_id?: number | null;
  answered_by?: Record<string, any>;
  count_accessed?: number;
  is_active?: boolean;
  parent_id?: number | null;
  parent_model?: string | null;  // max_length=100
  question?: string | null;  // max_length=500
  question_id?: number | null;
  sequence?: number;
  setting_id_id?: number | null;  // FK → core.Setting
  status?: string | null;  // max_length=100
}

export interface UpdateQuestionAnswerRequest {
  id: number | string;
  ida?: string;  // max_length=40
  answer?: string | null;  // max_length=500
  answer_id?: number | null;
  answered_by?: Record<string, any>;
  count_accessed?: number;
  is_active?: boolean;
  parent_id?: number | null;
  parent_model?: string | null;  // max_length=100
  question?: string | null;  // max_length=500
  question_id?: number | null;
  sequence?: number;
  setting_id_id?: number | null;  // FK → core.Setting
  status?: string | null;  // max_length=100
}

// ── Tag ──
// Django: docs.Tag  table: tags
// wcapi model_name: "tag"

export interface TagRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  count_accessed: number;
  data?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  prefs: Record<string, any>;
  purpose?: string | null;  // max_length=255
  record_id?: number | null;
  refs: Record<string, any>;
  security_level?: number;
  sequence: number;
  status?: string | null;  // max_length=100
  version: number;  // read-only
}

export interface CreateTagRequest {
  ida?: string;  // max_length=40
  count_accessed?: number;
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=255
  record_id?: number | null;
  sequence?: number;
  status?: string | null;  // max_length=100
}

export interface UpdateTagRequest {
  id: number | string;
  ida?: string;  // max_length=40
  count_accessed?: number;
  data?: Record<string, any>;
  is_active?: boolean;
  model_name?: string | null;  // max_length=255
  name?: string | null;  // max_length=255
  purpose?: string | null;  // max_length=255
  record_id?: number | null;
  sequence?: number;
  status?: string | null;  // max_length=100
}

// ============================================================
// ORGS
// ============================================================

// ── Customer ──
// Django: orgs.Customer  table: orgs_orgbase
// wcapi model_name: "customer"

export interface CustomerRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateCustomerRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateCustomerRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ── Employee ──
// Django: orgs.Employee  table: orgs_orgbase
// wcapi model_name: "employee"

export interface EmployeeRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateEmployeeRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateEmployeeRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ── Manufacturer ──
// Django: orgs.Manufacturer  table: orgs_orgbase
// wcapi model_name: "manufacturer"

export interface ManufacturerRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateManufacturerRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateManufacturerRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ── Org ──
// Django: orgs.OrgBase  table: orgs_orgbase
// wcapi model_name: "org"

export interface OrgRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateOrgRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateOrgRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ── Rep ──
// Django: orgs.Rep  table: orgs_orgbase
// wcapi model_name: "rep"

export interface RepRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateRepRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateRepRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ── Vendor ──
// Django: orgs.Vendor  table: orgs_orgbase
// wcapi model_name: "vendor"

export interface VendorRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses: Record<string, any>;
  attention?: string | null;  // max_length=255
  comments: Record<string, any>;
  connections: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts: Record<string, any>;
  data: Record<string, any>;
  display_name: string;  // max_length=255
  docs: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails: Record<string, any>;
  financial: Record<string, any>;
  gl_accounts: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  refs: Record<string, any>;
  relations: Record<string, any>;
  relationship_stats?: Record<string, any>;
  security_level?: number;
  stats?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  version: number;  // read-only
}

export interface CreateVendorRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

export interface UpdateVendorRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  address_id?: number | null;
  addresses?: Record<string, any>;
  attention?: string | null;  // max_length=255
  connections?: Record<string, any>;
  contact_id_id?: number | null;  // FK → core.Contact
  contacts?: Record<string, any>;
  data?: Record<string, any>;
  display_name?: string;  // max_length=255
  docs?: Record<string, any>;
  domain?: string | null;  // max_length=255
  domain_id?: number | null;
  domains?: Record<string, any>;
  email?: string | null;  // max_length=254
  email_id?: number | null;
  emails?: Record<string, any>;
  financial?: Record<string, any>;
  gl_accounts?: Record<string, any>;
  is_active?: boolean;
  metrics?: Record<string, any>;
  org_type?: string | null;  // choices: customer, vendor, rep, employee, manufacturer, other | max_length=20
  phone?: string | null;  // max_length=50
  phone_id?: number | null;
  phones?: Record<string, any>;
  price_level?: string | null;  // max_length=30
  relations?: Record<string, any>;
  status?: string;  // choices: , active, prospect, suspended, inactive, retired | max_length=30
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
}

// ============================================================
// PRODUCTS
// ============================================================

// ── BillOfMaterial ──
// Django: products.BillOfMaterial  table: products_billofmaterial
// wcapi model_name: "bill_of_material"

export interface BillOfMaterialRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  alternate_group?: string;  // max_length=40
  change_reason?: string;  // max_length=120
  child_description?: string;  // max_length=255
  child_id_id: number | null;  // FK → products.Item
  child_ida?: string;  // max_length=120
  comments: Record<string, any>;
  cost_snapshot?: number | string | null;
  dt_created: number;  // read-only
  dt_effective_from?: string | null;
  dt_effective_to?: string | null;
  dt_last_recalc?: string | null;
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_alternate: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  is_optional: boolean;
  metadata: Record<string, any>;
  op_data?: Record<string, any>;
  parent_id_id: number | null;  // FK → products.Item
  parent_ida?: string;  // max_length=120
  prefs: Record<string, any>;
  quantity: number | string;
  recalc_parent_cost_description?: string;  // max_length=255
  refs: Record<string, any>;
  revision?: string;  // max_length=20
  scrap_factor: number | string;
  security_level?: number;
  sequence: number;
  version: number;  // read-only
  yield_pct?: number | string | null;
}

export interface CreateBillOfMaterialRequest {
  alternate_group?: string;  // max_length=40
  change_reason?: string;  // max_length=120
  child_description?: string;  // max_length=255
  child_id_id: number | null;  // FK → products.Item
  child_ida?: string;  // max_length=120
  cost_snapshot?: number | string | null;
  dt_effective_from?: string | null;
  dt_effective_to?: string | null;
  dt_last_recalc?: string | null;
  is_active?: boolean;
  is_alternate?: boolean;
  is_optional?: boolean;
  op_data?: Record<string, any>;
  parent_id_id: number | null;  // FK → products.Item
  parent_ida?: string;  // max_length=120
  quantity?: number | string;
  recalc_parent_cost_description?: string;  // max_length=255
  revision?: string;  // max_length=20
  scrap_factor?: number | string;
  sequence?: number;
  yield_pct?: number | string | null;
}

export interface UpdateBillOfMaterialRequest {
  id: number | string;
  alternate_group?: string;  // max_length=40
  change_reason?: string;  // max_length=120
  child_description?: string;  // max_length=255
  child_id_id?: number | null;  // FK → products.Item
  child_ida?: string;  // max_length=120
  cost_snapshot?: number | string | null;
  dt_effective_from?: string | null;
  dt_effective_to?: string | null;
  dt_last_recalc?: string | null;
  is_active?: boolean;
  is_alternate?: boolean;
  is_optional?: boolean;
  op_data?: Record<string, any>;
  parent_id_id?: number | null;  // FK → products.Item
  parent_ida?: string;  // max_length=120
  quantity?: number | string;
  recalc_parent_cost_description?: string;  // max_length=255
  revision?: string;  // max_length=20
  scrap_factor?: number | string;
  sequence?: number;
  yield_pct?: number | string | null;
}

// ── Catalog ──
// Django: products.Catalog  table: products_catalog
// wcapi model_name: "catalog"

export interface CatalogRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  code: string;  // max_length=60
  comments: Record<string, any>;
  connection_id_id?: number | null;  // FK → sync.Connection
  currency: string;  // max_length=8
  customer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_effective_end?: number | null;
  dt_effective_start: number;
  dt_modified: number;  // read-only
  employee_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  metrics?: Record<string, any>;
  name: string;  // max_length=160
  orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  prefs: Record<string, any>;
  refs: Record<string, any>;
  rep_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  security_level?: number;
  version: number;  // read-only
}

export interface CreateCatalogRequest {
  code: string;  // max_length=60
  connection_id_id?: number | null;  // FK → sync.Connection
  currency?: string;  // max_length=8
  customer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  dt_effective_end?: number | null;
  dt_effective_start: number;
  employee_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  is_active?: boolean;
  manufacturer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  metrics?: Record<string, any>;
  name: string;  // max_length=160
  orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  rep_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateCatalogRequest {
  id: number | string;
  code?: string;  // max_length=60
  connection_id_id?: number | null;  // FK → sync.Connection
  currency?: string;  // max_length=8
  customer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  dt_effective_end?: number | null;
  dt_effective_start?: number;
  employee_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  is_active?: boolean;
  manufacturer_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  metrics?: Record<string, any>;
  name?: string;  // max_length=160
  orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  rep_orgbase_id_id?: number | null;  // FK → orgs.OrgBase
}

// ── InventoryCheck ──
// Django: products.InventoryCheck  table: products_inventorycheck
// wcapi model_name: "inventory_check"

export interface InventoryCheckRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  catalog_id_id?: number | null;  // FK → products.Catalog
  comments: Record<string, any>;
  data?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  dt_performed: number;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  notes?: string;
  orgbase_id_id: number | null;  // FK → orgs.OrgBase
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status: string;  // choices: planned, in_progress, completed, canceled | max_length=20
  user_id_id?: number | null;  // FK → core.Contact
  version: number;  // read-only
}

export interface CreateInventoryCheckRequest {
  catalog_id_id?: number | null;  // FK → products.Catalog
  data?: Record<string, any>;
  dt_performed: number;
  is_active?: boolean;
  notes?: string;
  orgbase_id_id: number | null;  // FK → orgs.OrgBase
  status?: string;  // choices: planned, in_progress, completed, canceled | max_length=20
  user_id_id?: number | null;  // FK → core.Contact
}

export interface UpdateInventoryCheckRequest {
  id: number | string;
  catalog_id_id?: number | null;  // FK → products.Catalog
  data?: Record<string, any>;
  dt_performed?: number;
  is_active?: boolean;
  notes?: string;
  orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  status?: string;  // choices: planned, in_progress, completed, canceled | max_length=20
  user_id_id?: number | null;  // FK → core.Contact
}

// ── InventoryLayer ──
// Django: products.InventoryLayer  table: products_inventorylayer
// wcapi model_name: "inventory_layer"

export interface InventoryLayerRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  is_locked: boolean;
  item_id_id: number | null;  // FK → products.Item
  lot?: string;  // max_length=80
  metadata: Record<string, any>;
  prefs: Record<string, any>;
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  serial_batch?: string;  // max_length=80
  serial_numbers?: Record<string, any>;
  source?: Record<string, any>;
  source_doc_id?: number | null;
  source_doc_type?: string;  // max_length=40
  status?: string;  // max_length=30
  version: number;  // read-only
  warehouse_id_id: number | null;  // FK → products.Warehouse
}

export interface CreateInventoryLayerRequest {
  cost?: Record<string, any>;
  is_active?: boolean;
  is_locked?: boolean;
  item_id_id: number | null;  // FK → products.Item
  lot?: string;  // max_length=80
  quantity?: Record<string, any>;
  serial_batch?: string;  // max_length=80
  serial_numbers?: Record<string, any>;
  source?: Record<string, any>;
  source_doc_id?: number | null;
  source_doc_type?: string;  // max_length=40
  status?: string;  // max_length=30
  warehouse_id_id: number | null;  // FK → products.Warehouse
}

export interface UpdateInventoryLayerRequest {
  id: number | string;
  cost?: Record<string, any>;
  is_active?: boolean;
  is_locked?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  lot?: string;  // max_length=80
  quantity?: Record<string, any>;
  serial_batch?: string;  // max_length=80
  serial_numbers?: Record<string, any>;
  source?: Record<string, any>;
  source_doc_id?: number | null;
  source_doc_type?: string;  // max_length=40
  status?: string;  // max_length=30
  warehouse_id_id?: number | null;  // FK → products.Warehouse
}

// ── InventoryReservation ──
// Django: products.InventoryReservation  table: products_inventoryreservation
// wcapi model_name: "inventory_reservation"

export interface InventoryReservationRecord {
  id?: number;  // read-only
  context?: Record<string, any>;
  description?: string;  // max_length=255
  dt_committed?: string | null;
  dt_expires: string;
  dt_modified?: string;  // read-only
  dt_released?: string | null;
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  qty: number | string;
  reason?: string;  // max_length=80
  state: string;  // choices: pending, committed, canceled, expired | max_length=20
  warehouse_id_id: number | null;  // FK → products.Warehouse
}

export interface CreateInventoryReservationRequest {
  context?: Record<string, any>;
  description?: string;  // max_length=255
  dt_committed?: string | null;
  dt_expires: string;
  dt_released?: string | null;
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  qty: number | string;
  reason?: string;  // max_length=80
  state?: string;  // choices: pending, committed, canceled, expired | max_length=20
  warehouse_id_id: number | null;  // FK → products.Warehouse
}

export interface UpdateInventoryReservationRequest {
  id: number | string;
  context?: Record<string, any>;
  description?: string;  // max_length=255
  dt_committed?: string | null;
  dt_expires?: string;
  dt_released?: string | null;
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  item_id_id?: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  qty?: number | string;
  reason?: string;  // max_length=80
  state?: string;  // choices: pending, committed, canceled, expired | max_length=20
  warehouse_id_id?: number | null;  // FK → products.Warehouse
}

// ── Item ──
// Django: products.Item  table: products_item
// wcapi model_name: "item"

export interface ItemRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  base_uom?: string;  // max_length=20
  catalog?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  description?: string;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  flags?: Record<string, any>;
  gls?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  kind: string;  // choices: physical, service, bundle | max_length=20
  metadata: Record<string, any>;
  name: string;  // max_length=160
  prefs: Record<string, any>;
  price?: Record<string, any>;
  qr_code?: string | null;  // max_length=255
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  row_version: number;
  security_level?: number;
  sku?: string | null;  // max_length=80
  specification_id?: number | null;
  stats?: Record<string, any>;
  tax_code?: Record<string, any>;
  uom?: string;  // max_length=20
  version: number;  // read-only
}

export interface CreateItemRequest {
  base_uom?: string;  // max_length=20
  catalog?: Record<string, any>;
  cost?: Record<string, any>;
  description?: string;
  flags?: Record<string, any>;
  gls?: Record<string, any>;
  is_active?: boolean;
  kind?: string;  // choices: physical, service, bundle | max_length=20
  name: string;  // max_length=160
  price?: Record<string, any>;
  qr_code?: string | null;  // max_length=255
  quantity?: Record<string, any>;
  row_version?: number;
  sku?: string | null;  // max_length=80
  specification_id?: number | null;
  tax_code?: Record<string, any>;
  uom?: string;  // max_length=20
}

export interface UpdateItemRequest {
  id: number | string;
  base_uom?: string;  // max_length=20
  catalog?: Record<string, any>;
  cost?: Record<string, any>;
  description?: string;
  flags?: Record<string, any>;
  gls?: Record<string, any>;
  is_active?: boolean;
  kind?: string;  // choices: physical, service, bundle | max_length=20
  name?: string;  // max_length=160
  price?: Record<string, any>;
  qr_code?: string | null;  // max_length=255
  quantity?: Record<string, any>;
  row_version?: number;
  sku?: string | null;  // max_length=80
  specification_id?: number | null;
  tax_code?: Record<string, any>;
  uom?: string;  // max_length=20
}

// ── ItemXref ──
// Django: products.ItemXRef  table: products_itemxref
// wcapi model_name: "item_xref"

export interface ItemXrefRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  external_sku: string;  // max_length=120
  external_uuid?: string | null;  // max_length=32
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  is_preferred: boolean;
  item_id_id: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  source: string;  // choices: manufacturer, wholesaler, other | max_length=40
  source_id?: number | null;
  source_model_name?: string;  // max_length=40
  source_name?: string;  // max_length=120
  status?: string;  // max_length=30
  version: number;  // read-only
}

export interface CreateItemXrefRequest {
  cost?: Record<string, any>;
  external_sku: string;  // max_length=120
  external_uuid?: string | null;  // max_length=32
  is_active?: boolean;
  is_preferred?: boolean;
  item_id_id: number | null;  // FK → products.Item
  source: string;  // choices: manufacturer, wholesaler, other | max_length=40
  source_id?: number | null;
  source_model_name?: string;  // max_length=40
  source_name?: string;  // max_length=120
  status?: string;  // max_length=30
}

export interface UpdateItemXrefRequest {
  id: number | string;
  cost?: Record<string, any>;
  external_sku?: string;  // max_length=120
  external_uuid?: string | null;  // max_length=32
  is_active?: boolean;
  is_preferred?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  source?: string;  // choices: manufacturer, wholesaler, other | max_length=40
  source_id?: number | null;
  source_model_name?: string;  // max_length=40
  source_name?: string;  // max_length=120
  status?: string;  // max_length=30
}

// ── Metrics ──
// Django: products.InventoryMetricsSnapshot  table: products_inventorymetricssnapshot
// wcapi model_name: "metrics"

export interface MetricsRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  metrics: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreateMetricsRequest {
  is_active?: boolean;
  metrics: Record<string, any>;
}

export interface UpdateMetricsRequest {
  id: number | string;
  is_active?: boolean;
  metrics?: Record<string, any>;
}

// ── OrgItem ──
// Django: products.OrgItem  table: products_orgitem
// wcapi model_name: "org_item"

export interface OrgItemRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  availability_state?: string;  // choices: enabled, paused, retired | max_length=20
  catalog_id_id?: number | null;  // FK → products.Catalog
  comments: Record<string, any>;
  data?: Record<string, any>;
  description?: string;  // max_length=255
  dt_created: number;  // read-only
  dt_last_checked?: number | null;
  dt_modified: number;  // read-only
  dt_next_check?: number | null;
  health_rating: number;
  inventory_frequency?: string;  // choices: daily, weekly, monthly, 30d | max_length=30
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metadata: Record<string, any>;
  metrics?: Record<string, any>;
  orgbase_id_id: number | null;  // FK → orgs.OrgBase
  prefs: Record<string, any>;
  quantity_maximum?: number | string | null;
  quantity_minimum?: number | string | null;
  refs: Record<string, any>;
  security_level?: number;
  status?: string;  // max_length=30
  version: number;  // read-only
}

export interface CreateOrgItemRequest {
  availability_state?: string;  // choices: enabled, paused, retired | max_length=20
  catalog_id_id?: number | null;  // FK → products.Catalog
  data?: Record<string, any>;
  description?: string;  // max_length=255
  dt_last_checked?: number | null;
  dt_next_check?: number | null;
  inventory_frequency?: string;  // choices: daily, weekly, monthly, 30d | max_length=30
  is_active?: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metrics?: Record<string, any>;
  orgbase_id_id: number | null;  // FK → orgs.OrgBase
  quantity_maximum?: number | string | null;
  quantity_minimum?: number | string | null;
  status?: string;  // max_length=30
}

export interface UpdateOrgItemRequest {
  id: number | string;
  availability_state?: string;  // choices: enabled, paused, retired | max_length=20
  catalog_id_id?: number | null;  // FK → products.Catalog
  data?: Record<string, any>;
  description?: string;  // max_length=255
  dt_last_checked?: number | null;
  dt_next_check?: number | null;
  inventory_frequency?: string;  // choices: daily, weekly, monthly, 30d | max_length=30
  is_active?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metrics?: Record<string, any>;
  orgbase_id_id?: number | null;  // FK → orgs.OrgBase
  quantity_maximum?: number | string | null;
  quantity_minimum?: number | string | null;
  status?: string;  // max_length=30
}

// ── ProcessorRuns ──
// Django: products.InventoryAdjustmentProcessorRun  table: products_inventoryadjustmentprocessorrun
// wcapi model_name: "processor_runs"

export interface ProcessorRunsRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  applied: number;
  attempted: number;
  canceled: number;
  comments: Record<string, any>;
  dry_run: boolean;
  dt_created: number;  // read-only
  dt_finished: string;
  dt_modified: number;  // read-only
  dt_started: string;
  duration_s: number | string;
  health_rating: number;
  insufficient: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  reserved_conflict_skipped: number;
  run_type: string;  // choices: global, stack | max_length=12
  security_level?: number;
  skipped_locked: number;
  stack_id?: number | null;
  still_locked: number;
  summary?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateProcessorRunsRequest {
  applied?: number;
  attempted?: number;
  canceled?: number;
  dry_run?: boolean;
  dt_finished: string;
  dt_started: string;
  duration_s: number | string;
  insufficient?: number;
  is_active?: boolean;
  reserved_conflict_skipped?: number;
  run_type: string;  // choices: global, stack | max_length=12
  skipped_locked?: number;
  stack_id?: number | null;
  still_locked?: number;
  summary?: Record<string, any>;
}

export interface UpdateProcessorRunsRequest {
  id: number | string;
  applied?: number;
  attempted?: number;
  canceled?: number;
  dry_run?: boolean;
  dt_finished?: string;
  dt_started?: string;
  duration_s?: number | string;
  insufficient?: number;
  is_active?: boolean;
  reserved_conflict_skipped?: number;
  run_type?: string;  // choices: global, stack | max_length=12
  skipped_locked?: number;
  stack_id?: number | null;
  still_locked?: number;
  summary?: Record<string, any>;
}

// ── Serial ──
// Django: products.Serial  table: products_serial
// wcapi model_name: "serial"

export interface SerialRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  comments: Record<string, any>;
  data?: Record<string, any>;
  description?: string;  // max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metadata: Record<string, any>;
  model_ida?: string;  // max_length=120
  prefs: Record<string, any>;
  qr_code?: string;  // max_length=255
  refs: Record<string, any>;
  security_level?: number;
  serial_ida: string;  // max_length=120
  site?: Record<string, any>;
  status?: string;  // max_length=40
  version: number;  // read-only
  warranty?: Record<string, any>;
}

export interface CreateSerialRequest {
  data?: Record<string, any>;
  description?: string;  // max_length=255
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  is_active?: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  model_ida?: string;  // max_length=120
  qr_code?: string;  // max_length=255
  serial_ida: string;  // max_length=120
  site?: Record<string, any>;
  status?: string;  // max_length=40
  warranty?: Record<string, any>;
}

export interface UpdateSerialRequest {
  id: number | string;
  data?: Record<string, any>;
  description?: string;  // max_length=255
  inventorylayer_id_id?: number | null;  // FK → products.InventoryLayer
  is_active?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  model_ida?: string;  // max_length=120
  qr_code?: string;  // max_length=255
  serial_ida?: string;  // max_length=120
  site?: Record<string, any>;
  status?: string;  // max_length=40
  warranty?: Record<string, any>;
}

// ── Service ──
// Django: products.Service  table: products_service
// wcapi model_name: "service"

export interface ServiceRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  billing?: Record<string, any>;
  billing_audit?: Record<string, any>;
  category?: string;  // max_length=120
  comments: Record<string, any>;
  default_duration_minutes: number;
  description?: string;  // max_length=255
  display?: string;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item_id_id: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  prefs: Record<string, any>;
  process?: Record<string, any>;
  purpose?: string;  // max_length=255
  refs: Record<string, any>;
  row_version: number;
  security_level?: number;
  status?: string;  // max_length=30
  travel?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateServiceRequest {
  ida?: string;  // max_length=40
  billing?: Record<string, any>;
  billing_audit?: Record<string, any>;
  category?: string;  // max_length=120
  default_duration_minutes?: number;
  description?: string;  // max_length=255
  display?: string;
  is_active?: boolean;
  item_id_id: number | null;  // FK → products.Item
  process?: Record<string, any>;
  purpose?: string;  // max_length=255
  row_version?: number;
  status?: string;  // max_length=30
  travel?: Record<string, any>;
}

export interface UpdateServiceRequest {
  id: number | string;
  ida?: string;  // max_length=40
  billing?: Record<string, any>;
  billing_audit?: Record<string, any>;
  category?: string;  // max_length=120
  default_duration_minutes?: number;
  description?: string;  // max_length=255
  display?: string;
  is_active?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  process?: Record<string, any>;
  purpose?: string;  // max_length=255
  row_version?: number;
  status?: string;  // max_length=30
  travel?: Record<string, any>;
}

// ── Usage ──
// Django: products.ItemUsage  table: products_itemusage
// wcapi model_name: "usage"

export interface UsageRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  comments: Record<string, any>;
  description?: string;  // max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metadata: Record<string, any>;
  metrics?: Record<string, any>;
  month: number;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string;  // max_length=30
  version: number;  // read-only
  year: number;
}

export interface CreateUsageRequest {
  description?: string;  // max_length=255
  is_active?: boolean;
  item_id_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metrics?: Record<string, any>;
  month: number;
  status?: string;  // max_length=30
  year: number;
}

export interface UpdateUsageRequest {
  id: number | string;
  description?: string;  // max_length=255
  is_active?: boolean;
  item_id_id?: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metrics?: Record<string, any>;
  month?: number;
  status?: string;  // max_length=30
  year?: number;
}

// ── Variant ──
// Django: products.Variant  table: products_variant
// wcapi model_name: "variant"

export interface VariantRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  attrs?: Record<string, any>;
  canonical_key: string;  // max_length=255
  comments: Record<string, any>;
  description?: string;  // max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  metadata: Record<string, any>;
  parent_item_id: number | null;  // FK → products.Item
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  set_uuid: string;  // max_length=32
  variant_uuid: string;  // max_length=32
  version: number;  // read-only
}

export interface CreateVariantRequest {
  attrs?: Record<string, any>;
  canonical_key: string;  // max_length=255
  description?: string;  // max_length=255
  is_active?: boolean;
  item_id: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  parent_item_id: number | null;  // FK → products.Item
  set_uuid: string;  // max_length=32
  variant_uuid: string;  // max_length=32
}

export interface UpdateVariantRequest {
  id: number | string;
  attrs?: Record<string, any>;
  canonical_key?: string;  // max_length=255
  description?: string;  // max_length=255
  is_active?: boolean;
  item_id?: number | null;  // FK → products.Item
  item_ida?: string;  // max_length=120
  parent_item_id?: number | null;  // FK → products.Item
  set_uuid?: string;  // max_length=32
  variant_uuid?: string;  // max_length=32
}

// ── Warehouse ──
// Django: products.Warehouse  table: products_warehouse
// wcapi model_name: "warehouse"

export interface WarehouseRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  actions?: Record<string, any>;
  code: string;  // max_length=40
  comments: Record<string, any>;
  count?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  location?: Record<string, any>;
  metadata: Record<string, any>;
  name: string;  // max_length=160
  prefs: Record<string, any>;
  priority: string;  // max_length=40
  refs: Record<string, any>;
  security_level?: number;
  site_code?: string;  // max_length=40
  version: number;  // read-only
}

export interface CreateWarehouseRequest {
  code: string;  // max_length=40
  count?: Record<string, any>;
  is_active?: boolean;
  location?: Record<string, any>;
  name: string;  // max_length=160
  priority?: string;  // max_length=40
  site_code?: string;  // max_length=40
}

export interface UpdateWarehouseRequest {
  id: number | string;
  code?: string;  // max_length=40
  count?: Record<string, any>;
  is_active?: boolean;
  location?: Record<string, any>;
  name?: string;  // max_length=160
  priority?: string;  // max_length=40
  site_code?: string;  // max_length=40
}

// ============================================================
// SYNC
// ============================================================

// ── Bundle ──
// Django: sync.Bundle  table: bundles
// wcapi model_name: "bundle"

export interface BundleRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  alert?: string | null;  // choices: , none, info, warning, critical | max_length=255
  comments: Record<string, any>;
  config: Record<string, any>;
  conflicts?: Record<string, any>;
  connection_id_id: number | null;  // FK → sync.Connection
  direction: string;  // choices: , push, pull, sync | max_length=255
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  duration: number;
  encryption?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  maps?: Record<string, any>;
  metadata: Record<string, any>;
  payload?: Record<string, any>;
  prefs: Record<string, any>;
  refs: Record<string, any>;
  response?: Record<string, any>;
  rules?: Record<string, any>;
  security_level?: number;
  size: number;
  status?: string | null;  // choices: , queued, running, success, warning, error | max_length=255
  version: number;  // read-only
}

export interface CreateBundleRequest {
  ida?: string;  // max_length=40
  alert?: string | null;  // choices: , none, info, warning, critical | max_length=255
  config: Record<string, any>;
  conflicts?: Record<string, any>;
  connection_id_id: number | null;  // FK → sync.Connection
  direction: string;  // choices: , push, pull, sync | max_length=255
  duration?: number;
  encryption?: Record<string, any>;
  is_active?: boolean;
  maps?: Record<string, any>;
  payload?: Record<string, any>;
  response?: Record<string, any>;
  rules?: Record<string, any>;
  size?: number;
  status?: string | null;  // choices: , queued, running, success, warning, error | max_length=255
}

export interface UpdateBundleRequest {
  id: number | string;
  ida?: string;  // max_length=40
  alert?: string | null;  // choices: , none, info, warning, critical | max_length=255
  config?: Record<string, any>;
  conflicts?: Record<string, any>;
  connection_id_id?: number | null;  // FK → sync.Connection
  direction?: string;  // choices: , push, pull, sync | max_length=255
  duration?: number;
  encryption?: Record<string, any>;
  is_active?: boolean;
  maps?: Record<string, any>;
  payload?: Record<string, any>;
  response?: Record<string, any>;
  rules?: Record<string, any>;
  size?: number;
  status?: string | null;  // choices: , queued, running, success, warning, error | max_length=255
}

// ── Connection ──
// Django: sync.Connection  table: connections
// wcapi model_name: "connection"

export interface ConnectionRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  action?: string;  // max_length=255
  actions?: Record<string, any>;
  changes?: Record<string, any>;
  comment?: string;
  comments: Record<string, any>;
  config: Record<string, any>;
  conflicts?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  encryption?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  maps?: Record<string, any>;
  metadata: Record<string, any>;
  name: string;  // max_length=255
  prefs: Record<string, any>;
  purpose?: string | null;  // choices: , ingest, export, bi, sync, monitor | max_length=255
  refs: Record<string, any>;
  relationships?: Record<string, any>;
  rules?: Record<string, any>;
  scripts?: Record<string, any>;
  security_level?: number;
  status?: string | null;  // choices: , draft, active, paused, error, retired | max_length=255
  type: string;  // choices: , api, sftp, database, webhook, manual | max_length=255
  version: number;  // read-only
}

export interface CreateConnectionRequest {
  ida?: string;  // max_length=40
  action?: string;  // max_length=255
  changes?: Record<string, any>;
  comment?: string;
  config: Record<string, any>;
  conflicts?: Record<string, any>;
  encryption?: Record<string, any>;
  is_active?: boolean;
  maps?: Record<string, any>;
  name: string;  // max_length=255
  purpose?: string | null;  // choices: , ingest, export, bi, sync, monitor | max_length=255
  relationships?: Record<string, any>;
  rules?: Record<string, any>;
  scripts?: Record<string, any>;
  status?: string | null;  // choices: , draft, active, paused, error, retired | max_length=255
  type: string;  // choices: , api, sftp, database, webhook, manual | max_length=255
}

export interface UpdateConnectionRequest {
  id: number | string;
  ida?: string;  // max_length=40
  action?: string;  // max_length=255
  changes?: Record<string, any>;
  comment?: string;
  config?: Record<string, any>;
  conflicts?: Record<string, any>;
  encryption?: Record<string, any>;
  is_active?: boolean;
  maps?: Record<string, any>;
  name?: string;  // max_length=255
  purpose?: string | null;  // choices: , ingest, export, bi, sync, monitor | max_length=255
  relationships?: Record<string, any>;
  rules?: Record<string, any>;
  scripts?: Record<string, any>;
  status?: string | null;  // choices: , draft, active, paused, error, retired | max_length=255
  type?: string;  // choices: , api, sftp, database, webhook, manual | max_length=255
}

// ============================================================
// TRANSACTIONS
// ============================================================

// ── Invoice ──
// Django: transactions.Invoice  table: invoices
// wcapi model_name: "invoice"

export interface InvoiceRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata?: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs?: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateInvoiceRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateInvoiceRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── InvoiceLine ──
// Django: transactions.InvoiceLine  table: invoice_lines
// wcapi model_name: "invoice_line"

export interface InvoiceLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  invoice_id?: number | null;  // FK → transactions.Invoice
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateInvoiceLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  invoice_id?: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

export interface UpdateInvoiceLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  invoice_id?: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

// ── Payment ──
// Django: transactions.Payment  table: payments
// wcapi model_name: "payment"

export interface PaymentRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  amount: number | string;
  comments: Record<string, any>;
  contact_id_id: number | null;  // FK → core.Contact
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  dt_payment: string;
  dt_processed?: string | null;
  dt_reconciliation?: string | null;
  fee_amount: number | string;
  gateway: string;  // choices: , manual, stripe, paypal | max_length=20
  gateway_response?: Record<string, any>;
  health_rating: number;
  id_gateway_payment_intent?: string;  // max_length=255
  id_gateway_transaction?: string;  // max_length=255
  invoice_id_id?: number | null;  // FK → transactions.Invoice
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata?: Record<string, any>;
  notes?: string;
  paymentmethod_id_id?: number | null;  // FK → transactions.PaymentMethod
  paymentterm_id_id?: number | null;  // FK → transactions.PaymentTerm
  prefs: Record<string, any>;
  reconciled: boolean;
  reference_number?: string;  // max_length=100
  refs?: Record<string, any>;
  security_level?: number;
  status: string;  // choices: , pending, processing, completed, failed, cancelled, refunded, partially_refunded | max_length=20
  version: number;  // read-only
}

export interface CreatePaymentRequest {
  ida?: string;  // max_length=40
  amount: number | string;
  contact_id_id: number | null;  // FK → core.Contact
  dt_payment: string;
  dt_processed?: string | null;
  dt_reconciliation?: string | null;
  fee_amount?: number | string;
  gateway?: string;  // choices: , manual, stripe, paypal | max_length=20
  gateway_response?: Record<string, any>;
  id_gateway_payment_intent?: string;  // max_length=255
  id_gateway_transaction?: string;  // max_length=255
  invoice_id_id?: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  notes?: string;
  paymentmethod_id_id?: number | null;  // FK → transactions.PaymentMethod
  paymentterm_id_id?: number | null;  // FK → transactions.PaymentTerm
  reconciled?: boolean;
  reference_number?: string;  // max_length=100
  status?: string;  // choices: , pending, processing, completed, failed, cancelled, refunded, partially_refunded | max_length=20
}

export interface UpdatePaymentRequest {
  id: number | string;
  ida?: string;  // max_length=40
  amount?: number | string;
  contact_id_id?: number | null;  // FK → core.Contact
  dt_payment?: string;
  dt_processed?: string | null;
  dt_reconciliation?: string | null;
  fee_amount?: number | string;
  gateway?: string;  // choices: , manual, stripe, paypal | max_length=20
  gateway_response?: Record<string, any>;
  id_gateway_payment_intent?: string;  // max_length=255
  id_gateway_transaction?: string;  // max_length=255
  invoice_id_id?: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  notes?: string;
  paymentmethod_id_id?: number | null;  // FK → transactions.PaymentMethod
  paymentterm_id_id?: number | null;  // FK → transactions.PaymentTerm
  reconciled?: boolean;
  reference_number?: string;  // max_length=100
  status?: string;  // choices: , pending, processing, completed, failed, cancelled, refunded, partially_refunded | max_length=20
}

// ── PaymentApplication ──
// Django: transactions.PaymentApplication  table: payment_applications
// wcapi model_name: "payment_application"

export interface PaymentApplicationRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  amount: number | string;
  applied_at?: string;  // read-only
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  invoice_id_id: number | null;  // FK → transactions.Invoice
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  notes?: string;
  payment_id_id: number | null;  // FK → transactions.Payment
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreatePaymentApplicationRequest {
  ida?: string;  // max_length=40
  amount: number | string;
  invoice_id_id: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  notes?: string;
  payment_id_id: number | null;  // FK → transactions.Payment
}

export interface UpdatePaymentApplicationRequest {
  id: number | string;
  ida?: string;  // max_length=40
  amount?: number | string;
  invoice_id_id?: number | null;  // FK → transactions.Invoice
  is_active?: boolean;
  notes?: string;
  payment_id_id?: number | null;  // FK → transactions.Payment
}

// ── PaymentMethod ──
// Django: transactions.PaymentMethod  table: payment_methods
// wcapi model_name: "payment_method"

export interface PaymentMethodRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  description?: string;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name: string;  // max_length=100
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreatePaymentMethodRequest {
  ida?: string;  // max_length=40
  description?: string;
  is_active?: boolean;
  name: string;  // max_length=100
}

export interface UpdatePaymentMethodRequest {
  id: number | string;
  ida?: string;  // max_length=40
  description?: string;
  is_active?: boolean;
  name?: string;  // max_length=100
}

// ── PaymentTerm ──
// Django: transactions.PaymentTerm  table: payment_terms
// wcapi model_name: "payment_term"

export interface PaymentTermRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  days: number;
  description?: string;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name: string;  // max_length=100
  prefs: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  version: number;  // read-only
}

export interface CreatePaymentTermRequest {
  ida?: string;  // max_length=40
  days?: number;
  description?: string;
  is_active?: boolean;
  name: string;  // max_length=100
}

export interface UpdatePaymentTermRequest {
  id: number | string;
  ida?: string;  // max_length=40
  days?: number;
  description?: string;
  is_active?: boolean;
  name?: string;  // max_length=100
}

// ── Project ──
// Django: transactions.Project  table: projects
// wcapi model_name: "project"

export interface ProjectRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  attention: string;  // choices: , low, normal, high, critical | max_length=16
  burndown: number;
  category?: string;  // max_length=128
  comments: Record<string, any>;
  data?: Record<string, any>;
  dt_created: number;  // read-only
  dt_kanban?: string | null;
  dt_modified: number;  // read-only
  health_rating: number;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  logistics: Record<string, any>;
  metadata: Record<string, any>;
  name?: string;  // max_length=255
  objective: Record<string, any>;
  prefs: Record<string, any>;
  priority: number;
  profit: number | string;
  profit_velocity: number;
  refs: Record<string, any>;
  security_level?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks: Record<string, any>;
  version: number;  // read-only
}

export interface CreateProjectRequest {
  ida?: string;  // max_length=40
  attention?: string;  // choices: , low, normal, high, critical | max_length=16
  burndown?: number;
  category?: string;  // max_length=128
  data?: Record<string, any>;
  dt_kanban?: string | null;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active?: boolean;
  logistics?: Record<string, any>;
  name?: string;  // max_length=255
  objective?: Record<string, any>;
  priority?: number;
  profit?: number | string;
  profit_velocity?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status?: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks?: Record<string, any>;
}

export interface UpdateProjectRequest {
  id: number | string;
  ida?: string;  // max_length=40
  attention?: string;  // choices: , low, normal, high, critical | max_length=16
  burndown?: number;
  category?: string;  // max_length=128
  data?: Record<string, any>;
  dt_kanban?: string | null;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active?: boolean;
  logistics?: Record<string, any>;
  name?: string;  // max_length=255
  objective?: Record<string, any>;
  priority?: number;
  profit?: number | string;
  profit_velocity?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status?: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks?: Record<string, any>;
}

// ── ProjectLinks ──
// Django: transactions.Project  table: projects
// wcapi model_name: "project_links"

export interface ProjectLinksRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  attention: string;  // choices: , low, normal, high, critical | max_length=16
  burndown: number;
  category?: string;  // max_length=128
  comments: Record<string, any>;
  data?: Record<string, any>;
  dt_created: number;  // read-only
  dt_kanban?: string | null;
  dt_modified: number;  // read-only
  health_rating: number;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  logistics: Record<string, any>;
  metadata: Record<string, any>;
  name?: string;  // max_length=255
  objective: Record<string, any>;
  prefs: Record<string, any>;
  priority: number;
  profit: number | string;
  profit_velocity: number;
  refs: Record<string, any>;
  security_level?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks: Record<string, any>;
  version: number;  // read-only
}

export interface CreateProjectLinksRequest {
  ida?: string;  // max_length=40
  attention?: string;  // choices: , low, normal, high, critical | max_length=16
  burndown?: number;
  category?: string;  // max_length=128
  data?: Record<string, any>;
  dt_kanban?: string | null;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active?: boolean;
  logistics?: Record<string, any>;
  name?: string;  // max_length=255
  objective?: Record<string, any>;
  priority?: number;
  profit?: number | string;
  profit_velocity?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status?: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks?: Record<string, any>;
}

export interface UpdateProjectLinksRequest {
  id: number | string;
  ida?: string;  // max_length=40
  attention?: string;  // choices: , low, normal, high, critical | max_length=16
  burndown?: number;
  category?: string;  // max_length=128
  data?: Record<string, any>;
  dt_kanban?: string | null;
  id_contact?: number | null;
  intent?: string;  // max_length=255
  is_active?: boolean;
  logistics?: Record<string, any>;
  name?: string;  // max_length=255
  objective?: Record<string, any>;
  priority?: number;
  profit?: number | string;
  profit_velocity?: number;
  situation?: string;
  slug?: string | null;  // max_length=180
  status?: string;  // choices: , draft, active, onhold, blocked, done, canceled | max_length=32
  tasks?: Record<string, any>;
}

// ── Proposal ──
// Django: transactions.Proposal  table: proposals
// wcapi model_name: "proposal"

export interface ProposalRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateProposalRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateProposalRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── ProposalLine ──
// Django: transactions.ProposalLine  table: proposal_lines
// wcapi model_name: "proposal_line"

export interface ProposalLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  proposal_id?: number | null;  // FK → transactions.Proposal
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateProposalLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  proposal_id?: number | null;  // FK → transactions.Proposal
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

export interface UpdateProposalLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  proposal_id?: number | null;  // FK → transactions.Proposal
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

// ── PurchaseOrder ──
// Django: transactions.Purchase  table: purchases
// wcapi model_name: "purchase_order"

export interface PurchaseOrderRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreatePurchaseOrderRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdatePurchaseOrderRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── PurchaseOrderLine ──
// Django: transactions.PurchaseLine  table: purchase_lines
// wcapi model_name: "purchase_order_line"

export interface PurchaseOrderLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=50
  purchase_id: number | null;  // FK → transactions.Purchase
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
}

export interface CreatePurchaseOrderLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  purchase_id: number | null;  // FK → transactions.Purchase
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

export interface UpdatePurchaseOrderLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  purchase_id?: number | null;  // FK → transactions.Purchase
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

// ── PurchaseReceipt ──
// Django: transactions.Receipt  table: receipt
// wcapi model_name: "purchase_receipt"

export interface PurchaseReceiptRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  dt_received?: string;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  notes?: string;
  prefs: Record<string, any>;
  purchase_id?: number | null;  // FK → transactions.Purchase
  refs: Record<string, any>;
  security_level?: number;
  source_type: string;  // choices: purchase_receipt, workorder_completion, inventory_adjustment | max_length=30
  version: number;  // read-only
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}

export interface CreatePurchaseReceiptRequest {
  ida?: string;  // max_length=40
  is_active?: boolean;
  notes?: string;
  purchase_id?: number | null;  // FK → transactions.Purchase
  source_type?: string;  // choices: purchase_receipt, workorder_completion, inventory_adjustment | max_length=30
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}

export interface UpdatePurchaseReceiptRequest {
  id: number | string;
  ida?: string;  // max_length=40
  is_active?: boolean;
  notes?: string;
  purchase_id?: number | null;  // FK → transactions.Purchase
  source_type?: string;  // choices: purchase_receipt, workorder_completion, inventory_adjustment | max_length=30
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}

// ── Requisition ──
// Django: transactions.Requisition  table: requisitions
// wcapi model_name: "requisition"

export interface RequisitionRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  metadata: Record<string, any>;
  name: string;  // max_length=128
  prefs: Record<string, any>;
  purpose: string;  // max_length=128
  refs: Record<string, any>;
  security_level?: number;
  status?: string;  // max_length=50
  version: number;  // read-only
}

export interface CreateRequisitionRequest {
  ida?: string;  // max_length=40
  is_active?: boolean;
  name?: string;  // max_length=128
  purpose?: string;  // max_length=128
  status?: string;  // max_length=50
}

export interface UpdateRequisitionRequest {
  id: number | string;
  ida?: string;  // max_length=40
  is_active?: boolean;
  name?: string;  // max_length=128
  purpose?: string;  // max_length=128
  status?: string;  // max_length=50
}

// ── RequisitionLine ──
// Django: transactions.RequisitionLine  table: requisition_lines
// wcapi model_name: "requisition_line"

export interface RequisitionLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  requisition_id_id: number | null;  // FK → transactions.Requisition
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateRequisitionLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  requisition_id_id: number | null;  // FK → transactions.Requisition
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

export interface UpdateRequisitionLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  requisition_id_id?: number | null;  // FK → transactions.Requisition
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

// ── SalesOrder ──
// Django: transactions.Order  table: orders
// wcapi model_name: "sales_order"

export interface SalesOrderRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateSalesOrderRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateSalesOrderRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── SalesOrderLine ──
// Django: transactions.OrderLine  table: order_lines
// wcapi model_name: "sales_order_line"

export interface SalesOrderLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  order_id: number | null;  // FK → transactions.Order
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
}

export interface CreateSalesOrderLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  order_id: number | null;  // FK → transactions.Order
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

export interface UpdateSalesOrderLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  order_id?: number | null;  // FK → transactions.Order
  physical?: Record<string, any>;
  price?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
}

// ── Transaction ──
// Django: transactions.Order  table: orders
// wcapi model_name: "transaction"

export interface TransactionRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateTransactionRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateTransactionRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── WorkOrder ──
// Django: transactions.WorkOrder  table: work_orders
// wcapi model_name: "work_order"

export interface WorkOrderRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  comments: Record<string, any>;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  metadata: Record<string, any>;
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  refs: Record<string, any>;
  security_level?: number;
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
  version: number;  // read-only
}

export interface CreateWorkOrderRequest {
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

export interface UpdateWorkOrderRequest {
  id: number | string;
  ida?: string;  // max_length=40
  address_full?: string | null;  // max_length=500
  attention?: string | null;  // max_length=255
  balance?: number | string | null;
  conditions_description?: string | null;  // max_length=255
  conditions_id?: number | null;
  contact_id?: number | null;  // FK → core.Contact
  cost?: Record<string, any>;
  customer_id?: number | null;  // FK → orgs.OrgBase
  email?: string | null;  // max_length=254
  finance?: Record<string, any>;
  flow?: Record<string, any>;
  is_active?: boolean;
  manufacturer_id?: number | null;  // FK → orgs.OrgBase
  parent_id?: number | null;
  parent_model?: string | null;  // choices: proposal, sales_order, invoice, purchase_order, workorder, requisition | max_length=20
  phone?: string | null;  // max_length=50
  price_level?: string | null;  // max_length=30
  priority?: string | null;  // max_length=32
  sell?: Record<string, any>;
  source?: Record<string, any>;
  status?: string;  // choices: , planned, released, in_progress, hold, complete, canceled | max_length=32
  terms?: string | null;  // max_length=30
  terms_fk_id?: number | null;  // FK → transactions.PaymentTerm
  total?: number | string | null;
  totals?: Record<string, any>;
  vendor_id?: number | null;  // FK → orgs.OrgBase
}

// ── WorkOrderLine ──
// Django: transactions.WorkOrderLine  table: work_order_lines
// wcapi model_name: "work_order_line"

export interface WorkOrderLineRecord {
  id?: number;  // read-only
  uuid?: string | null;  // read-only | max_length=32
  ida?: string;  // max_length=40
  actions?: Record<string, any>;
  comments: Record<string, any>;
  cost?: Record<string, any>;
  dt_created: number;  // read-only
  dt_modified: number;  // read-only
  health_rating: number;
  is_active: boolean;
  is_archived: boolean;
  is_deleted: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  metadata: Record<string, any>;
  physical?: Record<string, any>;
  prefs: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  refs: Record<string, any>;
  security_level?: number;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  version: number;  // read-only
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}

export interface CreateWorkOrderLineRequest {
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}

export interface UpdateWorkOrderLineRequest {
  id: number | string;
  ida?: string;  // max_length=40
  cost?: Record<string, any>;
  is_active?: boolean;
  item?: Record<string, any>;
  item_fk_id?: number | null;  // FK → products.Item
  physical?: Record<string, any>;
  price_level?: string | null;  // max_length=50
  quantity?: Record<string, any>;
  status?: string | null;  // max_length=50
  tax?: Record<string, any>;
  workorder_id?: number | null;  // FK → transactions.WorkOrder
}
