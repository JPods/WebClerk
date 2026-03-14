/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useState, useCallback } from 'react';

export interface WCAPIResponse<T = any> {
  results?: T[];
  record?: T;
  count?: number;
  total?: number;
  limit?: number;
  offset?: number;
  detail?: string;
}

export interface WCAPIError {
  detail: string;
}

export const useWCAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const makeRequest = useCallback(async <T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<WCAPIResponse<T> | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData: WCAPIError = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data: WCAPIResponse<T> = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const get = useCallback(<T = any>(
    modelName: string,
    params: Record<string, any> = {}
  ): Promise<WCAPIResponse<T> | null> => {
    const queryString = new URLSearchParams({
      model_name: modelName,
      ...params,
    }).toString();

    return makeRequest<T>(`/wcapi/get/?${queryString}`);
  }, [makeRequest]);

  const create = useCallback(<T = any>(
    modelName: string,
    data: Record<string, any>
  ): Promise<WCAPIResponse<T> | null> => {
    return makeRequest<T>(`/wcapi/create/?model_name=${modelName}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }, [makeRequest]);

  const update = useCallback(<T = any>(
    modelName: string,
    id: number,
    data: Record<string, any>
  ): Promise<WCAPIResponse<T> | null> => {
    return makeRequest<T>(`/wcapi/update/?model_name=${modelName}&id=${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }, [makeRequest]);

  const remove = useCallback(<T = any>(
    modelName: string,
    id: number
  ): Promise<WCAPIResponse<T> | null> => {
    return makeRequest<T>(`/wcapi/delete/?model_name=${modelName}&id=${id}`, {
      method: 'DELETE',
    });
  }, [makeRequest]);

  return {
    loading,
    error,
    get,
    create,
    update,
    remove,
  };
};