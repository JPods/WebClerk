/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Unified Organization API Service
 * Handles all org CRUD operations via the wcapi SDK.
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
import type {
  Organization,
  OrgType,
  OrgListParams,
  OrgListResponse,
  OrgCreateRequest,
  OrgUpdateRequest,
} from '../types/orgTypes';

// --- Core API methods ---

export const orgApi = {
  /**
   * List organizations with optional filtering.
   * Uses org_type as model_name (e.g. "employee", "customer").
   */
  list: async (params: OrgListParams = {}): Promise<OrgListResponse> => {
    const modelName = params.org_type || 'organization';
    const { org_type: _drop, search, ...rest } = params;
    const queryParams: Record<string, any> = { ...rest };
    if (search) queryParams.q = search;

    const data = await getRecords(modelName, queryParams);
    return {
      results: (data.results ?? []) as Organization[],
      count: data.total ?? 0,
      total: data.total,
      limit: data.limit ?? undefined,
      offset: data.offset,
    };
  },

  /**
   * Get single organization by ID.
   */
  get: async (id: number, orgType?: OrgType): Promise<Organization> => {
    const modelName = orgType || 'organization';
    const data = await getRecord(modelName, id);
    return (data?.record ?? {}) as Organization;
  },

  /**
   * Create new organization.
   */
  create: async (data: OrgCreateRequest): Promise<Organization> => {
    const modelName = data.org_type || 'organization';
    const { org_type: _drop, ...payload } = data;
    const result = await saveRecord(modelName, payload);
    return result as Organization;
  },

  /**
   * Update existing organization.
   */
  update: async (data: OrgUpdateRequest): Promise<Organization> => {
    const modelName = data.org_type || 'organization';
    const { org_type: _drop, ...payload } = data;
    const result = await saveRecord(modelName, payload);
    return result as Organization;
  },

  /**
   * Delete organization (soft delete).
   */
  delete: async (id: number, orgType?: OrgType): Promise<void> => {
    const modelName = orgType || 'organization';
    await deleteRecord(modelName, id);
  },
};

// Default export for generic use
export default orgApi;
