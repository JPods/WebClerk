/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback } from 'react';
import { getRecords, getRecord, saveRecord } from '../api/wcapi';

export function useWCAPI() {
  const get = useCallback(async (model: string, params?: any) => {
    if (params?.id) {
      const result = await getRecord(model, params.id);
      return result;
    }
    const result = await getRecords(model, params);
    return result;
  }, []);

  const create = useCallback(async (model: string, data: any) => {
    const result = await saveRecord(model, data);
    return result;
  }, []);

  const update = useCallback(async (model: string, id: number, data: any) => {
    const result = await saveRecord(model, { ...data, id });
    return result;
  }, []);

  return { get, create, update };
}