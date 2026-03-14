/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Item Types — matches wc3 Item (StatsMixin + BaseModel)
 * @see webClerk3/apps/products/models/item.py
 *
 * DB table: products_item
 */

/* ------------------------------------------------------------------ */
/*  Item JSONB sub-types                                               */
/* ------------------------------------------------------------------ */

export interface ItemFlags {
  back_order_allowed?: boolean;
  discountable?: boolean;
  linked?: boolean;
  not_tracked?: boolean;
  pacing?: boolean;
  print_suppressed?: boolean;
  serialized?: boolean;
  tally_by_type?: boolean;
}

export interface ItemPriceTier {
  level?: string;
  price?: number | null;
  currency?: string;
  [key: string]: unknown;
}

export interface ItemPrice {
  base?: number | null;
  msrp?: number | null;
  tiers?: ItemPriceTier[];
  qty_breaks?: unknown[];
  currency?: string;
  history?: unknown[];
}

export interface ItemCost {
  standard?: number | null;
  last?: number | null;
  avg?: number | null;
  landed?: number | null;
  currency?: string;
  components?: Record<string, unknown>;
  qty_breaks?: unknown[];
  history?: unknown[];
}

export interface ItemTaxCode {
  code?: string;
  jurisdiction?: string;
  category?: string;
  rate?: number | null;
  exemptions?: unknown[];
  jurisdiction_params?: unknown[];
}

export interface ItemCatalog {
  categories?: string[];
  attributes?: Record<string, unknown>;
  web?: Record<string, unknown>;
  flags?: Record<string, unknown>;
}

export interface ItemQuantity {
  on_hand?: number;
  allocated?: number;
  available?: number;
  on_so?: number;
  on_po?: number;
  on_p?: number;
  on_reciept?: number;
  on_in?: number;
  on_wo?: number;
  [key: string]: number | undefined;
}

export type ItemKind = "physical" | "service" | "bundle";

/* ------------------------------------------------------------------ */
/*  Component Props                                                    */
/* ------------------------------------------------------------------ */

export interface ItemAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

/* ------------------------------------------------------------------ */
/*  API Request / Response                                             */
/* ------------------------------------------------------------------ */

/** Fields accepted when creating an item via wcapi saveRecord */
export interface CreateItemRequest {
  name: string;
  sku?: string;
  qr_code?: string;
  kind?: ItemKind;
  uom?: string;
  base_uom?: string;
  description?: string;
  specification_id?: number | null;
  is_active?: boolean;
  // JSONB fields
  gls?: Record<string, unknown>;
  flags?: ItemFlags;
  price?: ItemPrice;
  cost?: ItemCost;
  tax_code?: ItemTaxCode;
  catalog?: ItemCatalog;
  quantity?: ItemQuantity;
  // BaseModel JSONB fields
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
}

/** Response shape from saveRecord / getRecord for an item */
export interface ItemApiTask {
  id: number;
  uuid?: string;
  ida?: string;
  name: string;
  sku?: string;
  qr_code?: string;
  kind: ItemKind;
  uom?: string;
  base_uom?: string;
  description?: string;
  specification_id?: number | null;
  row_version?: number;
  // Timestamps & lifecycle
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;
  security_level?: number;
  health_rating?: number;
  // JSONB fields
  gls?: Record<string, unknown>;
  flags?: ItemFlags;
  price?: ItemPrice;
  cost?: ItemCost;
  tax_code?: ItemTaxCode;
  catalog?: ItemCatalog;
  quantity?: ItemQuantity;
  // BaseModel JSONB fields
  refs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  prefs?: Record<string, unknown>;
  comments?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  // StatsMixin
  stats?: Record<string, unknown>;
}

/** Fields accepted for update (id + version required for concurrency) */
export interface UpdateItemRequest extends Partial<CreateItemRequest> {
  id: number;
  version?: number;
}