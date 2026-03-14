/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { z } from "zod";

export const settingSchema = z.object({
  name: z.string().optional(),
  purpose: z.string().optional(),
  role: z.string().optional(),
  parent_model: z.string().optional(),
  data: z.any().optional(),
});

export type SettingFormData = z.infer<typeof settingSchema>;