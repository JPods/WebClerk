import { getRecords, saveRecord, deleteRecord } from '../../../../api/wcapi';

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchProposals = async (params?: any) => {
  const res = await getRecords('tx_proposals', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createProposal = async (data: any) => {
  return saveRecord('tx_proposals', data);
};

export const updateProposal = async (id: number, data: any) => {
  return saveRecord('tx_proposals', { ...data, id });
};

export const deleteProposal = async (id: number) => {
  return deleteRecord('tx_proposals', id);
};