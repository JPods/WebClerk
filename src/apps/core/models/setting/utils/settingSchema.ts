import { z } from "zod";

export const settingSchema = z.object({
  name: z.string().optional(),
  purpose: z.string().optional(),
  role: z.string().optional(),
  model_target: z.string().optional(),
  data: z.any().optional(),
});

export type SettingFormData = z.infer<typeof settingSchema>;