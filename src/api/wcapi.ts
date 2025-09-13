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
  const res = await apiClient.get<ApiEnvelope<ModelNamesPayload>>('/wcapi/model_name/list/');
  return res.data.data;
}

export async function getModelDetail(model_name: string) {
  const res = await apiClient.get<ApiEnvelope<ModelDetailPayload>>('/wcapi/model_name/detail/', { params: { model_name } });
  return res.data.data;
}

export async function getRecords(model_name: string) {
  const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', { params: { model_name } });
  return res.data.data;
}

export async function getRecord(model_name: string, id: number) {
  const res = await apiClient.get<ApiEnvelope<GetDetailPayload>>('/wcapi/get/', { params: { model_name, id } });
  return res.data.data;
}

export async function saveRecord(model_name: string, payload: any) {
  const res = await apiClient.post<ApiEnvelope<any>>('/wcapi/save/', { model_name, ...payload });
  return res.data.data;
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
