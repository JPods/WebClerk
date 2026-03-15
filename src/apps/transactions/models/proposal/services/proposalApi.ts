/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, getRecord } from '../../../../../api/wcapi';
import apiClient from '../../../../../api/axios';
import { patchAction } from '../../../../../api/userProfile';
import { Proposal } from '../types/proposalType';
import { ProposalFormData } from "../utils/proposalSchema";
import {
  ProposalLine,
  CreateProposalLineRequest,
  UpdateProposalLineRequest
} from '../types/proposalLineType';

type PatchActionResponse<T> = {
  status?: number;
  data?: T;
};

function normalizePatchResponse<T>(res: unknown): { status: number; data: T } {
  const maybe = (res ?? {}) as PatchActionResponse<T>;
  return {
    status: maybe.status ?? 200,
    data: (maybe.data ?? res) as T,
  };
}

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
  const payload = {
    model_name: 'proposal',
    ...data,
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<Proposal>(res);
};

export const updateProposal = async (id: number, data: Partial<ProposalFormData>): Promise<{ status: number; data: Proposal }> => {
  const payload = {
    model_name: 'proposal',
    ...data,
    id,
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<Proposal>(res);
};

export const deleteProposal = async (id: number): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: 'proposal',
    id,
    method: 'delete',
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<any>(res);
};

// Proposal Actions - Note: Backend action endpoint may need implementation
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

export const generateProposalPdf = async (_id: number): Promise<{ status: number; data: any }> => {
  // PDF generation - placeholder until backend endpoint is implemented
  return { status: 200, data: { message: 'PDF generation not yet implemented' } };
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
  const payload = {
    model_name: 'proposal_line',
    parent: proposalId,
    ...data,
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<ProposalLine>(res);
};

export const updateProposalLine = async (proposalId: number, lineId: number, data: UpdateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  const payload = {
    model_name: 'proposal_line',
    ...data,
    parent: proposalId,
    id: lineId,
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<ProposalLine>(res);
};

export const deleteProposalLine = async (_proposalId: number, lineId: number): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: 'proposal_line',
    id: lineId,
    method: 'delete',
  };
  const res = await patchAction(payload);
  return normalizePatchResponse<any>(res);
};