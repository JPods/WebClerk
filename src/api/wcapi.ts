import apiClient from './axios';

// Basic API envelope type
export interface ApiEnvelope<T = any> {
  status: string;
  error?: any | null;
  code: number;
  message: string;
  data: T;
}

export interface ModelNamesPayload {
  model_names: string[];
  count: number;
}

export interface ModelDetailPayload {
  model: {
    model_name: string;
    fields?: Array<{ name: string; type?: string }>;
    [k: string]: any;
  };
}

export interface GetListPayload {
  model_name: string;
  results: any[];
  total: number;
  limit?: number | null;
  offset?: number;
}

export interface GetDetailPayload {
  model_name: string;
  record: any;
  related?: Record<string, any[]>;
}

export async function getModelNames() {
  try {
    const res = await apiClient.get<ApiEnvelope<ModelNamesPayload>>('/wcapi/model_name/list/');
    return res.data.data;
  } catch (err: any) {
    const status = err?.response?.status;
    if (status === 404) {
      // Fallback: some deployments mount API under /api
      const res2 = await apiClient.get<ApiEnvelope<ModelNamesPayload>>('/api/wcapi/model_name/list/');
      return res2.data.data;
    }
    // Bubble other errors (like 401) so caller can show a helpful message
    throw err;
  }
}

export async function getModelDetail(model_name: string) {
  try {
    const res = await apiClient.get<ApiEnvelope<ModelDetailPayload>>('/wcapi/model_name/detail/', { params: { model_name } });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<ModelDetailPayload>>('/api/wcapi/model_name/detail/', { params: { model_name } });
      return res2.data.data;
    }
    throw err;
  }
}

export async function getRecords(model_name: string, params?: any) {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>(`/wcapi/get/`, { params: { model_name, limit: 10, ...params } });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>(`/api/wcapi/get/`, { params: { model_name, limit: 10, ...params } });
      return res2.data.data;
    }
    throw err;
  }
}

export async function getRecord(model_name: string, id: number) {
  try {
    const res = await apiClient.get<ApiEnvelope<GetDetailPayload>>(`/wcapi/get/`, { params: { model_name, id } });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetDetailPayload>>(`/api/wcapi/get/`, { params: { model_name, id } });
      return res2.data.data;
    }
    throw err;
  }
}

export async function saveRecord(model_name: string, payload: any) {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>('/wcapi/save/', { model_name, ...payload });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>('/api/wcapi/save/', { model_name, ...payload });
      return res2.data.data;
    }
    throw err;
  }
}

export async function deleteRecord(model_name: string, id: number) {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>('/wcapi/save/', { model_name, id, method: 'delete' });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>('/api/wcapi/save/', { model_name, id, method: 'delete' });
      return res2.data.data;
    }
    throw err;
  }
}

// Local persistence for field selections per model
const LS_KEY = 'adminWorkbench.fieldSelections';
type FieldSelections = Record<string, { list: string[]; detail: string[] }>;

export function loadFieldSelections(): FieldSelections {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveFieldSelections(next: FieldSelections) {
  localStorage.setItem(LS_KEY, JSON.stringify(next));
}

// Settings API for workbench fields
export interface SettingRecord {
  id?: number;
  model_name: string;
  purpose: string;
  data: {
    list: string[];
    detail: string[];
  };
}

export async function getWorkbenchFieldsSetting(model_name: string): Promise<SettingRecord | null> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: { model_name: 'setting', model_name_filter: model_name, purpose: 'workbench_fields' }
    });
    const results = res.data.data.results || [];
    return results.length > 0 ? results[0] : null;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>('/api/wcapi/get/', {
        params: { model_name: 'setting', model_name_filter: model_name, purpose: 'workbench_fields' }
      });
      const results = res2.data.data.results || [];
      return results.length > 0 ? results[0] : null;
    }
    throw err;
  }
}

export async function getAllWorkbenchFieldsSettings(): Promise<SettingRecord[]> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: { model_name: 'setting', purpose: 'workbench_fields' }
    });
    return res.data.data.results || [];
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.get<ApiEnvelope<GetListPayload>>('/api/wcapi/get/', {
        params: { model_name: 'setting', purpose: 'workbench_fields' }
      });
      return res2.data.data.results || [];
    }
    throw err;
  }
}

export async function saveWorkbenchFieldsSetting(setting: SettingRecord) {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>('/wcapi/save/', { ...setting, model_name: 'setting' });
    return res.data.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post<ApiEnvelope<any>>('/api/wcapi/save/', { ...setting, model_name: 'setting' });
      return res2.data.data;
    }
    throw err;
  }
}
