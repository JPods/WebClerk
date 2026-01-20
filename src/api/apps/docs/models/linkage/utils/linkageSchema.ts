import * as z from "zod";

export const linkageSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  source_model: z.string().min(1, "Source model is required"),
  source_id: z.number().min(1, "Source ID is required"),
  target_model: z.string().min(1, "Target model is required"),
  target_id: z.number().min(1, "Target ID is required"),
  link_type: z.string().min(1, "Link type is required"),
});