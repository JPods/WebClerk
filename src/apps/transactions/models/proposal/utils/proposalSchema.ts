import { z } from 'zod';

export const proposalSchema = z.object({
  proposal_no: z.string().min(1, 'Proposal number is required'),
});

export type ProposalFormData = z.infer<typeof proposalSchema>;