import * as z from "zod";

export const actionSchema = z.object({
  priority: z.string().min(1,"Priority is required"),
  difficulty: z.string().min(1,"Difficulty is required"),
  hours: z.coerce.number().min(1,"Hours is required"),
  percent: z.coerce.number().min(1,"Percent is required"),
  status: z.string().optional(),
  quality: z.string().optional(),
  description: z.string().optional(),
});

export const contactSchema = z.object({
  name_first: z.string().min(1,"First Name is required"),
  name_last: z.string().min(1,"Last Name is required"),
  name_middle: z.string().min(1,"Middle Name is required"),
  email: z.string().min(1,"Email is required").email("Invalid email format"),
  company: z.string().min(1,"Company is required"),
});
