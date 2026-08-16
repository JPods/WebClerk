/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const fetchProposalLines = async (params?: any) => {
  const res = await getRecords('tx_proposal_lines', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createProposalLine = async (data: any) => {
  return saveRecord('tx_proposal_lines', data);
};

export const updateProposalLine = async (id: number, data: any) => {
  return saveRecord('tx_proposal_lines', { ...data, id });
};

export const deleteProposalLine = async (id: number) => {
  return deleteRecord('tx_proposal_lines', id);
};