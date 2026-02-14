/**
 * Manufacturer Types — matches wc3 OrgBase (proxy: org_type="manufacturer")
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

export interface ManufacturerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateManufacturerRequest {
  display_name: string;
  status?: string;
  org_type?: "manufacturer";
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

export interface ManufacturerApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  display_name: string;
  status: string;
  org_type: "manufacturer";
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

export interface UpdateManufacturerRequest extends Partial<CreateManufacturerRequest> {
  id: number;
  version?: number;
}

export type ManufacturerType = Organization & { org_type: "manufacturer" };
