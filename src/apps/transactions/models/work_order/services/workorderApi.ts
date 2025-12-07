import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';


export const fetchWorkorders = async (params?: any) => {
  const res = await getRecords('workorder', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createWorkorder = async (data: any) => {
  return saveRecord('workorder', data);
};

export const updateWorkorder = async (id: number, data: any) => {
  return saveRecord('workorder', { ...data, id });
};

export const deleteWorkorder = async (id: number) => {
  return deleteRecord('workorder', id);
};