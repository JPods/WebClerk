import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

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