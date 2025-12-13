import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const proposalLineSchema = baseLineItemSchema.extend({
  proposal_id: z.number().min(1, "Proposal ID is required"),
});