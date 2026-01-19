import * as z from "zod";

export const actionSchema = z.object({
  action_en: z.string().min(1, "action_en is required"),
  description_en: z.string().optional(),
  kanban_column: z.string().min(1, "kanban_column is required"),
  priority: z.enum(["low", "medium", "high", "critical"], {
    errorMap: () => ({ message: "priority must be selected" }),
  }),
  difficulty: z.coerce.number().min(1, "difficulty is required"),
  status: z.string().optional(),
  assignee: z.string().optional(),
  dt_start: z.string().optional(),
  dt_end: z.string().optional(),
  dt_deadline: z.string().optional(),
});

export const contactSchema = z.object({
  name_first: z.string().min(1, "name_first is required"),
  name_last: z.string().min(1, "name_last is required"),
  name_middle: z.string().optional(),
  email: z
    .string()
    .min(1, "email is required")
    .email("email must be valid"),
  phone: z.string().min(1, "phone is required"),
  company: z.string().optional(),
});
