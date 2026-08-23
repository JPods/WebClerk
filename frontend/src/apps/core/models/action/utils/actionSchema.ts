/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const actionSchema = z.object({
  path: z.string().optional(),
  type: z.string().optional(),
  comment: z.any().optional(),
  refs: z.any().optional(),
  prefs: z.any().optional(),
  metadata: z.any().optional(),
});