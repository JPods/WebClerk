/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchWorkOrderLines = async (params?: any) => {
  const res = await getRecords('workorderline', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createWorkOrderLine = async (data: any) => {
  return saveRecord('workorderline', data);
};

export const updateWorkOrderLine = async (id: number, data: any) => {
  return saveRecord('workorderline', { ...data, id });
};

export const deleteWorkOrderLine = async (id: number) => {
  return deleteRecord('workorderline', id);
};