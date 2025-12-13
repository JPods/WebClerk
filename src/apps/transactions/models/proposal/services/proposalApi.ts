import { getRecords } from '../../../../../api/wcapi';
import { patchAction } from '../../../../../api/userProfile';
import {
  Proposal,
  CreateProposalRequest,
  UpdateProposalRequest
} from '../types/proposalType';
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
  const res = await getRecords('proposal', { id });
  return { status: 200, data: res.results?.[0] || {} as Proposal };
};

export const createProposal = async (data: CreateProposalRequest): Promise<{ status: number; data: Proposal }> => {
  const payload = {
    model_name: 'proposal',
    ...data,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const updateProposal = async (id: number, data: UpdateProposalRequest): Promise<{ status: number; data: Proposal }> => {
  const payload = {
    model_name: 'proposal',
    ...data,
    id,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const deleteProposal = async (id: number): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: 'proposal',
    id,
    method: 'delete',
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

// Proposal Actions - Note: Backend action endpoint may need implementation
export const convertProposalToOrder = async (_id: number): Promise<{ status: number; data: any }> => {
  // This may need to be implemented in backend or use direct API call
  // For now, return placeholder
  return { status: 200, data: { message: 'Conversion not yet implemented' } };
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
  return { status: res?.status || 200, data: res?.data || res };
};

export const updateProposalLine = async (proposalId: number, lineId: number, data: UpdateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  const payload = {
    model_name: 'proposal_line',
    ...data,
    parent: proposalId,
    id: lineId,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const deleteProposalLine = async (_proposalId: number, lineId: number): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: 'proposal_line',
    id: lineId,
    method: 'delete',
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};