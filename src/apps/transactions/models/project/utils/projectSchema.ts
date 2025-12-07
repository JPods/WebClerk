import * as z from "zod";

export const projectSchema = z.object({
  id_project: z.string().optional(),
  dt_created: z.string().optional(),
  dt_updated: z.string().optional(),
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  status: z.string().min(1, "Status is required"),
  dt_start: z.string().min(1, "Start date is required"),
  dt_end: z.string().min(1, "End date is required"),
});