export interface Envelope<T=unknown> {
  status: string;
  data?: T;
  message?: string;
  error?: { code: string; details?: any };
  [k: string]: any;
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers||{}) },
    ...init,
  });
  const contentType = res.headers.get('content-type') || '';
  let body: any = null;
  if (contentType.includes('application/json')) {
    body = await res.json();
  } else {
    body = await res.text();
  }
  if (body && typeof body === 'object' && 'status' in body) {
    const env = body as Envelope<T>;
    if (env.status !== 'success') {
      const err = new Error(env.message || 'API error');
      (err as any).code = env.error?.code;
      (err as any).details = env.error?.details;
      throw err;
    }
    return env.data as T;
  }
  return body as T;
}

export const api = {
  listModelNames(): Promise<string[]> {
    // assuming an endpoint listing allowed model_names
    return request<string[]>('/wcapi/model-names/');
  },
  listEndpoints(): Promise<string[]> {
    return request<string[]>('/wcapi/endpoints/');
  },
  getFields(modelName: string): Promise<string[]> {
    return request<string[]>(`/wcapi/model-fields/?model_name=${encodeURIComponent(modelName)}`);
  }
};
