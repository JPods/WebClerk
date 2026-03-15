/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { z } from "zod";

export const templateSchema = z.object({
  purpose: z.string().optional(),
  name: z.string().optional(),
  data: z.string().min(1, "Data is required"),
});

export type TemplateFormData = z.infer<typeof templateSchema>;