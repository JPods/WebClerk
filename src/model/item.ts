// TypeScript interfaces for Item model, matching Django schema as closely as possible.
// Extend as needed for richer typing and API integration.

export interface ItemQuantity {
  [key: string]: number | null;
}

export interface ItemPrice {
  [key: string]: number | null;
}

export interface ItemCost {
  [key: string]: number | null;
}

export interface ItemFlags {
  serialized?: boolean;
  [key: string]: boolean | string | number | undefined;
}

export interface ItemCatalog {
  [key: string]: any;
}

export interface Item {
  id: number;
  name: string;
  sku: string;
  description?: string;
  kind?: string;
  uom?: string;
  base_uom?: string;
  row_version?: number;
  quantity?: ItemQuantity;
  price?: ItemPrice;
  cost?: ItemCost;
  flags?: ItemFlags;
  tax_code?: string | object;
  catalog?: ItemCatalog;
  specification_id?: string;
  stats?: object;
  // Add more fields as needed for org_time, serial, bill_of_material, etc.
}
