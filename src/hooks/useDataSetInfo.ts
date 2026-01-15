/**
 * useDataSetInfo Hook
 * 
 * React hook to fetch and validate data set information between frontend and backend.
 * Automatically logs warnings if data sets don't match.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  DataSetInfo,
  SystemInfo,
  getFrontendDataSet,
  fetchBackendSystemInfo,
  validateDataSetMatch,
  logDataSetInfo,
} from '../utils/dataSetInfo';
import { NetworkInfo } from '../routes/network';

export interface UseDataSetInfoResult {
  frontend: DataSetInfo;
  backend: SystemInfo | null;
  isLoading: boolean;
  error: string | null;
  isMatch: boolean | null;
  message: string;
  refresh: () => Promise<void>;
}

export function useDataSetInfo(autoFetch: boolean = true): UseDataSetInfoResult {
  const [frontend] = useState<DataSetInfo>(getFrontendDataSet);
  const [backend, setBackend] = useState<SystemInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInfo = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const info = await fetchBackendSystemInfo(NetworkInfo.API_URL);
      setBackend(info);
      
      // Log to console for debugging
      logDataSetInfo(frontend, info);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch system info';
      setError(errorMessage);
      console.error('Failed to fetch backend system info:', errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [frontend]);

  useEffect(() => {
    if (autoFetch) {
      fetchInfo();
    }
  }, [autoFetch, fetchInfo]);

  // Calculate match status (safely handle missing data_set)
  const validation = backend?.data_set
    ? validateDataSetMatch(frontend, backend.data_set)
    : { isMatch: null, message: backend ? 'Backend data_set missing' : 'Backend info not loaded' };

  return {
    frontend,
    backend,
    isLoading,
    error,
    isMatch: validation.isMatch,
    message: validation.message,
    refresh: fetchInfo,
  };
}

export default useDataSetInfo;
