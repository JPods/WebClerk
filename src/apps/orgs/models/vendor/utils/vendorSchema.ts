import * as z from "zod";

export const vendorSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
  org_type: z.string().default("customer").optional(),
  status: z.string().min(1, "Phone is required"),
  version: z.number().default(1).optional(),
  is_active: z.boolean().default(false),
});
