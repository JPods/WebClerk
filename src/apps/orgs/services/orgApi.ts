/**
 * Unified Organization API Service
 * Handles all org CRUD operations via wcapi endpoints
 */
import apiClient from '@/api/axios';
import { PostLoginURL } from '@/routes/network';
import type {
  Organization,
  OrgType,
  OrgListParams,
  OrgListResponse,
  OrgCreateRequest,
  OrgUpdateRequest,
} from '../types/orgTypes';

// --- Response unwrapper ---
const unwrap = <T>(response: unknown): T => {
  if (!response) return {} as T;
  const res = response as { data?: { data?: T } };
  if (res.data?.data) return res.data.data;
  if (res.data) return res.data as T;
  return response as T;
};

// --- Core API methods ---

export const orgApi = {
  /**
   * List organizations with optional filtering
   * Uses the org_type as model_name (e.g., model_name=employee)
   */
  list: async (params: OrgListParams = {}): Promise<OrgListResponse> => {
    const queryParams = new URLSearchParams();
    // Use org_type as model_name (employee, customer, vendor, etc.)
    const modelName = params.org_type || 'organization';
    queryParams.set('model_name', modelName);
    
    if (params.status) queryParams.set('status', params.status);
    if (params.is_active !== undefined) queryParams.set('is_active', String(params.is_active));
    if (params.search) queryParams.set('q', params.search);
    if (params.limit) queryParams.set('limit', String(params.limit));
    if (params.offset) queryParams.set('offset', String(params.offset));
    if (params.ordering) queryParams.set('ordering', params.ordering);
    
    const res = await apiClient.get(`${PostLoginURL.allTypes}${queryParams.toString()}`);
    return unwrap<OrgListResponse>(res);
  },

  /**
   * Get single organization by ID
   */
  get: async (id: number, orgType?: OrgType): Promise<Organization> => {
    const modelName = orgType || 'organization';
    const res = await apiClient.get(`${PostLoginURL.allTypes}model_name=${modelName}&id=${id}`);
    const data = unwrap<{ record?: Organization; results?: Organization[] }>(res);
    return data.record || (data.results?.[0] as Organization) || ({} as Organization);
  },

  /**
   * Create new organization
   * Uses org_type as model_name for the API call
   */
  create: async (data: OrgCreateRequest): Promise<Organization> => {
    const modelName = data.org_type || 'organization';
    const res = await apiClient.post(PostLoginURL.allSave, {
      ...data,
      model_name: modelName,
    });
    return unwrap<Organization>(res);
  },

  /**
   * Update existing organization
   * Uses org_type as model_name for the API call
   */
  update: async (data: OrgUpdateRequest): Promise<Organization> => {
    const modelName = data.org_type || 'organization';
    const res = await apiClient.post(PostLoginURL.allSave, {
      ...data,
      model_name: modelName,
    });
    return unwrap<Organization>(res);
  },

  /**
   * Delete organization (soft delete)
   */
  delete: async (id: number, orgType?: OrgType): Promise<void> => {
    const modelName = orgType || 'organization';
    await apiClient.post(PostLoginURL.allSave, {
      model_name: modelName,
      id,
      is_deleted: true,
      is_active: false,
    });
  },
};

// --- Type-specific convenience APIs ---

const createTypedApi = (orgType: OrgType) => ({
  list: (params: Omit<OrgListParams, 'org_type'> = {}) => 
    orgApi.list({ ...params, org_type: orgType }),
    
  get: (id: number) => orgApi.get(id, orgType),
  
  create: (data: Omit<OrgCreateRequest, 'org_type'>) => 
    orgApi.create({ ...data, org_type: orgType }),
    
  update: (data: OrgUpdateRequest) => orgApi.update({ ...data, org_type: orgType }),
  
  delete: (id: number) => orgApi.delete(id, orgType),
});

export const customerApi = createTypedApi('customer');
export const vendorApi = createTypedApi('vendor');
export const employeeApi = createTypedApi('employee');
export const repApi = createTypedApi('rep');
export const manufacturerApi = createTypedApi('manufacturer');

// Default export for generic use
export default orgApi;
