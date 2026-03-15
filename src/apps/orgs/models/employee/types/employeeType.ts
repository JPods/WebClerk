/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Employee Types — matches wc3 OrgBase (proxy: org_type="employee")
 * @see webClerk3/apps/orgs/models/base.py
 * @see webClerk3/apps/orgs/models/proxies.py
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

export interface EmployeeAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateEmployeeRequest {
  display_name: string;
  status?: string;
  org_type?: "employee";
  is_active?: boolean;
  attention?: string;
  email?: string;
  phone?: string;
  price_level?: string;
  contact_id?: number | null;
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
  refs?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

export interface EmployeeApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  display_name: string;
  status: string;
  org_type: "employee";
  is_active: boolean;
  version: number;
  attention?: string;
  email?: string;
  phone?: string;
  price_level?: string;
  contact_id?: number | null;
  dt_created?: number;
  dt_modified?: number;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
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
  refs?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  stats?: Record<string, unknown>;
  relationship_stats?: Record<string, unknown>;
}

export interface UpdateEmployeeRequest extends Partial<CreateEmployeeRequest> {
  id: number;
  version?: number;
}

export type EmployeeType = Organization & { org_type: "employee" };
