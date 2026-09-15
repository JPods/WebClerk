/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const phoneSchema = z.object({
  number: z.string().min(1, "Phone number is required"),
  name: z.string().min(1, "Name is required"),
  country_code: z.string().min(1, "Country code is required"),
  opt_out: z.boolean(),
  attention: z.string().min(1, "Attention is required"),
  format: z.string().min(1, "Format is required"),
});
