import * as z from "zod";

// Proposal schema matching backend ProposalSerializer
export const proposalSchema = z.object({
  // Basic fields
  ida: z.string().optional(),
  status: z.string().optional(),
  priority: z.string().optional(),
  price_level: z.string().optional(),

  // Customer/Vendor
  id_customer: z.number().optional(),
  id_manufacturer: z.number().optional(),
  id_vendor: z.number().optional(),

  // JSON fields
  cost: z.any().optional(),
  sell: z.any().optional(),
  finance: z.any().optional(),
  flow: z.any().optional(),
  source: z.any().optional(),
  action: z.any().optional(),

  // Timestamps (readonly)
  dt_created: z.string().optional(),
  dt_modified: z.string().optional(),
  version: z.number().optional(),
});