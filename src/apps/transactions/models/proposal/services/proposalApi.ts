import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';
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
  return saveRecord('proposal', data);
};

export const updateProposal = async (id: number, data: UpdateProposalRequest): Promise<{ status: number; data: Proposal }> => {
  return saveRecord('proposal', { ...data, id });
};

export const deleteProposal = async (id: number): Promise<{ status: number; data: any }> => {
  return deleteRecord('proposal', id);
};

// Proposal Actions - Note: Backend action endpoint may need implementation
export const convertProposalToOrder = async (_id: number): Promise<{ status: number; data: any }> => {
  // This may need to be implemented in backend or use direct API call
  // For now, return placeholder
  return { status: 200, data: { message: 'Conversion not yet implemented' } };
};

// Proposal Lines API - Note: Backend may not have line endpoints yet
export const fetchProposalLines = async (_proposalId: number): Promise<{ status: number; data: { results: ProposalLine[]; total: number } }> => {
  // Placeholder - backend may need line endpoints
  return { status: 200, data: { results: [], total: 0 } };
};

export const fetchProposalLine = async (_proposalId: number, _lineId: number): Promise<{ status: number; data: ProposalLine }> => {
  // Placeholder
  return { status: 200, data: {} as ProposalLine };
};

export const createProposalLine = async (_proposalId: number, _data: CreateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  // Placeholder
  return { status: 200, data: {} as ProposalLine };
};

export const updateProposalLine = async (_proposalId: number, _lineId: number, _data: UpdateProposalLineRequest): Promise<{ status: number; data: ProposalLine }> => {
  // Placeholder
  return { status: 200, data: {} as ProposalLine };
};

export const deleteProposalLine = async (_proposalId: number, _lineId: number): Promise<{ status: number; data: any }> => {
  // Placeholder
  return { status: 200, data: {} };
};