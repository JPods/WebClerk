import { getRecords, saveRecord, deleteRecord } from '../../../../api/wcapi';

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchWorkorders = async (params?: any) => {
  const res = await getRecords('tx_workorders', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createWorkorder = async (data: any) => {
  return saveRecord('tx_workorders', data);
};

export const updateWorkorder = async (id: number, data: any) => {
  return saveRecord('tx_workorders', { ...data, id });
};

export const deleteWorkorder = async (id: number) => {
  return deleteRecord('tx_workorders', id);
};