import * as z from "zod";

export const actionSchema = z.object({
  action_en: z.string().min(1, "Title is required"),
  description_en: z.string().optional(),
  kanban_column: z.string().min(1, "Column is required"),
  priority: z.enum(["low", "medium", "high", "critical"], {
    errorMap: () => ({ message: "Select a priority" }),
  }),
  difficulty: z.coerce.number().min(1, "Difficulty is required"),
  status: z.string().optional(),
  assignee: z.string().optional(),
  dt_start: z.string().optional(),
  dt_end: z.string().optional(),
  dt_due: z.string().optional(),
});

export const contactSchema = z.object({
  name_first: z.string().min(1,"First Name is required"),
  name_last: z.string().min(1,"Last Name is required"),
  name_middle: z.string().min(1,"Middle Name is required"),
  email: z.string().min(1,"Email is required").email("Invalid email format"),
  phone: z.string().min(1,"Phone is required"),
  company: z.string().min(1,"Company is required"),
});
