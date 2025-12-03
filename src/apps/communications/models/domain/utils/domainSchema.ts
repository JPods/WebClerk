import * as z from "zod";

export const domainSchema = z.object({
  path: z.string().min(1, "Path is required"),
  type: z.string().min(1, "Type is required"),
  status: z.string().min(1, "Status is required"),
  metadata: z.string().optional(),
  comment: z.string().optional(),
  refs: z.string().optional(),
  prefs: z.string().optional(),
});