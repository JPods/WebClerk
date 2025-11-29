import * as z from "zod";

export const contactSchema = z.object({
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  name_middle: z.string().optional(),
  refs: z.string().optional(),
  prefs: z.string().optional(),
  metadata: z.string().optional(),
  status: z.string().default("active"),
});
