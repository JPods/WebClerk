import * as z from "zod";

export const reportSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  type: z.string().min(1, "Report type is required"),
  parameters: z.string().optional(),
  is_active: z.boolean(),
});