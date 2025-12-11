import * as z from "zod";

export const contactSchema = z
  .object({
    password: z.string().min(1, "Password"),
    cnf_password: z
      .string()
      .min(1, "Enter the same password as before, for verification."),
    email: z.string().min(1, "Primary email address for login"),
    name_first: z.string().min(1, "First name is required"),
    name_last: z.string().min(1, "Last name is required"),
    name_middle: z.string().optional(),
    name_prefix: z.string().optional(),
    name_suffix: z.string().optional(),
    role: z.string().optional(),
    company: z.string().optional(),
    title: z.string().optional(),
    department: z.string().optional(),
    is_active: z.boolean().default(false),
    is_staff: z.boolean().default(false),
  })
  .refine((data) => data.password === data.cnf_password, {
    message: "Passwords do not match",
    path: ["cnf_password"], // error shows under confirm-password field
  });

export const updateContactSchema = z
  .object({
    password: z.string().optional(),
    cnf_password: z.string().optional(),
    email: z.string().min(1, "Primary email address for login"),
    name_first: z.string().min(1, "First name is required"),
    name_last: z.string().min(1, "Last name is required"),
    name_middle: z.string().optional(),
    name_prefix: z.string().optional(),
    name_suffix: z.string().optional(),
    role: z.string().optional(),
    company: z.string().optional(),
    title: z.string().optional(),
    department: z.string().optional(),
    is_active: z.boolean().default(false),
    is_staff: z.boolean().default(false),
  })
  .refine(
    (data) => {
      // If user enters password, confirm password must match
      if (data.password || data.cnf_password) {
        return data.password === data.cnf_password;
      }
      return true;
    },
    {
      message: "Passwords do not match",
      path: ["cnf_password"],
    }
  );
