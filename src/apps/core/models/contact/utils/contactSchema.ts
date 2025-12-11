import * as z from "zod";

<<<<<<< HEAD
export const contactSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters").optional(),
  cnf_password: z.string().min(8, "Confirm password must be at least 8 characters").optional(),
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  name_middle: z.string().optional(),
  name_prefix: z.string().optional(),
  name_suffix: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  department: z.string().optional(),
  role: z.string().optional(),
  is_active: z.boolean(),
  is_staff: z.boolean(),
  path: z.string().optional(),
  type: z.string().optional(),
  comment: z.any().optional(),
  refs: z.any().optional(),
  prefs: z.any().optional(),
  metadata: z.any().optional(),
}).refine((data) => {
  if (data.password || data.cnf_password) {
    return data.password === data.cnf_password;
  }
  return true;
}, {
  message: "Passwords don't match",
  path: ["cnf_password"],
});
=======
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
>>>>>>> 8caefded00f0f1f364dc56d7cb7810006013ecea
