import * as z from "zod";

export const actionSchema = z.object({
  priority: z.string().optional(),
  difficulty: z.string().optional(),
  hours: z.coerce.number().optional(),
  percent: z.number().optional(),
  status: z.string().optional(),
  quality: z.string().optional(),
  description: z.string().optional(),
//   comment: z.string().optional(),
 });
