import * as z from "zod";

export const employeeSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
  org_type: z.string().default("Employee").optional(),
  status: z.string().min(1, "Status is required"),
  version: z.number().default(1).optional(),
  is_active: z.boolean().default(false),
});
