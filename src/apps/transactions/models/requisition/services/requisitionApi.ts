import { getRecords, saveRecord, deleteRecord } from '../../../../api/wcapi';

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchRequisitions = async (params?: any) => {
  const res = await getRecords('tx_requisitions', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createRequisition = async (data: any) => {
  return saveRecord('tx_requisitions', data);
};

export const updateRequisition = async (id: number, data: any) => {
  return saveRecord('tx_requisitions', { ...data, id });
};

export const deleteRequisition = async (id: number) => {
  return deleteRecord('tx_requisitions', id);
};