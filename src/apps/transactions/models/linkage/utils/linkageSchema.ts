import * as z from "zod";

export const linkageSchema = z.object({
  source_type: z.string().min(1, "Source type is required"),
  source_id: z.number().min(1, "Source ID is required"),
  target_type: z.string().min(1, "Target type is required"),
  target_id: z.number().min(1, "Target ID is required"),
  relationship_metadata: z.any().optional(),
});