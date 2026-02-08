import * as z from "zod";

export const customerSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
  org_type: z.string().default("customer"),
  status: z.string().min(1, "Phone is required"),
  version: z.number().default(1),
  is_active: z.boolean().default(false),
  contacts: z.string().optional(),
  addresses: z.string().optional(),
  domains: z.string().optional(),
  phones: z.string().optional(),
  emails: z.string().optional(),
  docs: z.string().optional(),
  connections: z.string().optional(),
  relations: z.string().optional(),
  financial: z.string().optional(),
  data: z.string().optional(),
  metrics: z.string().optional(),
  gl_accounts: z.string().optional(),
});
