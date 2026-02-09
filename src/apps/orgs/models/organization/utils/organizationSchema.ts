import * as z from "zod";

export const organizationSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
  org_type: z.string().default("other"),
  status: z.string().optional(),
  version: z.number().default(1),
  is_active: z.boolean().default(false),
  // New scalar fields from wc3
  attention: z.string().nullable().optional(),
  contact_id: z.number().nullable().optional(),
  email: z.string().email().nullable().optional().or(z.literal("")),
  phone: z.string().nullable().optional(),
  price_level: z.string().nullable().optional(),
});
