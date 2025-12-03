import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';


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