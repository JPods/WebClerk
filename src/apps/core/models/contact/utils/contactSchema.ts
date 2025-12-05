import * as z from "zod";

export const contactSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  cnf_password: z.string().min(8, "Confirm password must be at least 8 characters"),
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  name_middle: z.string().optional(),
  name_prefix: z.string().optional(),
  name_suffix: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  department: z.string().optional(),
  role: z.string().optional(),
  is_active: z.boolean().optional().default(false),
  is_staff: z.boolean().optional().default(false),
  path: z.string().optional(),
  type: z.string().optional(),
  comment: z.any().optional(),
  refs: z.any().optional(),
  prefs: z.any().optional(),
  metadata: z.any().optional(),
}).refine((data) => data.password === data.cnf_password, {
  message: "Passwords don't match",
  path: ["cnf_password"],
});
