/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Customer Types — matches wc3 OrgBase (proxy: org_type="customer")
 * @see webClerk3/apps/orgs/models/base.py
 * @see webClerk3/apps/orgs/models/proxies.py
 *
 * Customer is a proxy model on OrgBase; it adds NO extra columns.
 * All fields come from OrgBase → BaseModel → CoreModel.
 */

import type {
  Organization,
  OrgFinancial,
  OrgContact,
  OrgLocation,
  OrgDomain,
  OrgPhone,
  OrgEmail,
  OrgRelations,
  OrgDoc,
  OrgMetrics,
} from "@/apps/orgs/types/orgTypes";

/* ------------------------------------------------------------------ */
/*  Component Props                                                    */
/* ------------------------------------------------------------------ */

export interface CustomerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onCancel?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

/* ------------------------------------------------------------------ */
/*  API Request / Response                                             */
/* ------------------------------------------------------------------ */

/** Minimal fields required to create a customer via wcapi saveRecord */
export interface CreateCustomerRequest {
  display_name: string;
  status?: string;
  org_type?: "customer";
  is_active?: boolean;
  // OrgBase scalar columns
  attention?: string;
  email?: string;
  phone?: string;
  price_level?: string;
  contact_id?: number | null;
  // Aspect JSONB fields
  contacts?: OrgContact[];
  addresses?: OrgLocation[];
  domains?: OrgDomain[];
  phones?: OrgPhone[];
  emails?: OrgEmail[];
  relations?: OrgRelations;
  financial?: OrgFinancial;
  docs?: OrgDoc[];
  connections?: Record<string, string>;
  data?: Record<string, unknown>;
  metrics?: OrgMetrics;
  gl_accounts?: Record<string, unknown>;
  // BaseModel JSONB fields
  refs?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

/** Response shape from saveRecord / getRecord for a customer */
export interface CustomerApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  display_name: string;
  status: string;
  org_type: "customer";
  is_active: boolean;
  version: number;
  // OrgBase scalar columns
  attention?: string;
  email?: string;
  phone?: string;
  price_level?: string;
  contact_id?: number | null;
  // Timestamps
  dt_created?: number;
  dt_modified?: number;
  // Lifecycle
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  // Aspect JSONB fields
  contacts?: OrgContact[];
  addresses?: OrgLocation[];
  domains?: OrgDomain[];
  phones?: OrgPhone[];
  emails?: OrgEmail[];
  relations?: OrgRelations;
  financial?: OrgFinancial;
  docs?: OrgDoc[];
  connections?: Record<string, string>;
  data?: Record<string, unknown>;
  metrics?: OrgMetrics;
  gl_accounts?: Record<string, unknown>;
  // BaseModel JSONB fields
  refs?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  // Mixin fields
  stats?: Record<string, unknown>;
  relationship_stats?: Record<string, unknown>;
}

/** Fields accepted for update (id + version required for concurrency) */
export interface UpdateCustomerRequest extends Partial<CreateCustomerRequest> {
  id: number;
  version?: number;
}

/**
 * Full customer record type — alias for Organization with org_type narrowed.
 * Prefer using Organization from orgTypes.ts directly when possible.
 */
export type CustomerType = Organization & { org_type: "customer" }
