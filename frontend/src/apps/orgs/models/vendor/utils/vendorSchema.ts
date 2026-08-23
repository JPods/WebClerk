/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const vendorSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
  org_type: z.string().default("vendor"),
  status: z.string().optional(),
  version: z.number().default(1),
  is_active: z.boolean().default(false),
  // New scalar fields from wc3
  attention: z.string().nullable().optional(),
  contact_id: z.number().nullable().optional(),
  email: z.string().email().nullable().optional().or(z.literal("")),
  phone: z.string().nullable().optional(),
  price_level: z.string().nullable().optional(),
  terms: z.string().nullable().optional(),
  terms_id: z.number().nullable().optional(),
  address_full: z.string().nullable().optional(),
  // JSON aspect fields
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
