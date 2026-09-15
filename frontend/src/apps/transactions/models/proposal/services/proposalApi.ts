/* LastChecked: 2026-08-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import apiClient from "@/api/axios";
import { Proposal } from '../types/proposalType';
import { ProposalFormData } from "../utils/proposalSchema";
import {
  ProposalLine,
  CreateProposalLineRequest,
  UpdateProposalLineRequest
} from '../types/proposalLineType';

export const fetchProposals = async (params?: any): Promise<{ status: number; data: { results: Proposal[]; total: number } }> => {
  const res = await getRecords('proposal', params);
  return { status: 200, data: { results: res.results || [], total: res.total || 0 } };
};

export const fetchProposal = async (id: number): Promise<{ status: number; data: Proposal }> => {
  const res = await getRecord('proposal', id);
  const record = (res as any)?.record ?? res;
  return { status: 200, data: (record as Proposal) || ({} as Proposal) };
};

export const createProposal = async (data: Partial<ProposalFormData>): Promise<{ status: number; data: Proposal }> => {
  const res = await saveRecord('proposal', { ...data });
  const record = res?.record ?? res;
  return { status: 200, data: record as Proposal };
};

export const updateProposal = async (id: number, data: Partial<ProposalFormData>): Promise<{ status: number; data: Proposal }> => {
  const res = await saveRecord('proposal', { ...data, id });
  const record = res?.record ?? res;
  return { status: 200, data: record as Proposal };
};

export const deleteProposal = async (id: number): Promise<{ status: number; data: any }> => {
  const res = await deleteRecord('proposal', id);
  return { status: 200, data: res };
};

// Custom ViewSet action — not routable through wcapi CRUD
export const convertProposalToOrder = async (id: number): Promise<{ status: number; data: any }> => {
  try {
    const res = await apiClient.post(`/tx/proposals/${id}/convert-to-order/`);
    return { status: res.status, data: res.data };
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const res2 = await apiClient.post(`/api/tx/proposals/${id}/convert-to-order/`);
      return { status: res2.status, data: res2.data };
    }
    throw err;
  }
};

// Proposal Lines API
export const fetchProposalLines = async (proposalId: number): Promise<{ status: number; data: { results: ProposalLine[]; total: number } }> => {
  const res = await getRecords('proposal_line', { parent: proposalId });
  return { status: 200, data: { results: res.results || [], total: res.total || 0 } };
};

export const fetchProposalLine = async (proposalId: number, lineId: number): Promise<{ status: number; data: ProposalLine }> => {
  const res = await getRecords('proposal_line', { parent: proposalId, id: lineId });
  return { status: 200, data: res.results?.[0] || {} as ProposalLine };
};

export const createProposalLine = async (proposalId: number, data: CreateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  const res = await saveRecord('proposal_line', { ...data, parent: proposalId });
  const record = res?.record ?? res;
  return { status: 200, data: record as ProposalLine };
};

export const updateProposalLine = async (proposalId: number, lineId: number, data: UpdateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  const res = await saveRecord('proposal_line', { ...data, parent: proposalId, id: lineId });
  const record = res?.record ?? res;
  return { status: 200, data: record as ProposalLine };
};

export const deleteProposalLine = async (_proposalId: number, lineId: number): Promise<{ status: number; data: any }> => {
  const res = await deleteRecord('proposal_line', lineId);
  return { status: 200, data: res };
};
