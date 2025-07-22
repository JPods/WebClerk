import * as z from "zod";

export const actionSchema = z.object({
  priority: z.string().min(1,"Priority is required"),
  difficulty: z.string().min(1,"Difficulty is required"),
  hours: z.coerce.number().min(1,"Hours is required"),
  percent: z.coerce.number().min(1,"Percent is required"),
  status: z.string().optional(),
  quality: z.string().optional(),
  description: z.string().optional(),
//   comment: z.string().optional(),
 });
