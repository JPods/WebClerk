import apiClient from "../../../../../api/axios";

// Types for BOM data
export interface BOMComponent {
  id: number;
  sku: string;
  name: string;
  description?: string;
  uom?: string;
}

// Nested child BOM line (one level deep, lighter structure)
export interface BOMChildLine {
  id: number;
  component: BOMComponent;
  description: string;
  quantity: number | string;
  cost_snapshot: number | string | null;
  extended_cost: number | string | null;
  sequence: number;
  is_alternate: boolean;
  is_optional: boolean;
}

export interface BOMRefs {
  links: {
    bom: BOMChildLine[];
  };
}

export interface BOMLine {
  id: number;
  parent_item: BOMComponent;
  component: BOMComponent;
  description: string;
  quantity: number | string;
  cost_snapshot: number | string | null;
  extended_cost: number | string | null;
  scrap_factor: number | string;
  sequence: number;
  is_alternate: boolean;
  is_optional: boolean;
  component_child_count: number;
  refs: BOMRefs;
  revision: string;
  dt_effective_from: string | null;
  dt_effective_to: string | null;
}

export interface BOMListResponse {
  results: BOMLine[];
  total: number;
}

/**
 * Fetch BOM (Bill of Materials) children for a parent item
 */
export const fetchBOMLines = async (parentId: number): Promise<BOMListResponse> => {
  const response = await apiClient.get(`/api/products/items/${parentId}/bom/`);
  // Handle wrapped response
  if (response.data?.data) {
    return response.data.data;
  }
  return response.data;
};

/**
 * Recalculate BOM cost for a parent item
 */
export const recalcBOMCost = async (parentId: number): Promise<void> => {
  await apiClient.post(`/api/products/items/${parentId}/bom/recalc-cost/`);
};
