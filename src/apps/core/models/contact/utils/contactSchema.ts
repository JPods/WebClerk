import * as z from "zod";
import * as z from "zod";
export const emailRefSchema = z.object({
  id: z.number(),
  name: z.string(),
  address: z.string().email(),
});

export const phoneRefSchema = z.object({
  id: z.number(),
  name: z.string(),
  number: z.string(),
});
export const locationRefSchema = z.object({
  id: z.number(),
});
export const refsSchema = z.object({
  tags: z.array(z.string()).default([]),
  categories: z.array(z.string()).default([]),
  keywords: z.array(z.string()).default([]),
  related_ids: z.array(z.string()).default([]),
  depends_on: z.record(z.any()).default({}),
  links: z.object({
    rep: z.array(z.string()).default([]),
    item: z.array(z.string()).default([]),
    email: z.array(emailRefSchema).default([]),
    phone: z.array(phoneRefSchema).default([]),
    order: z.array(z.string()).default([]),
    domain: z.array(z.string()).default([]),
    contact: z.array(z.string()).default([]),
    customer: z.array(z.string()).default([]),
    document: z.array(z.string()).default([]),
    location: z.array(locationRefSchema).default([]),
    manufacturer: z.array(z.string()).default([]),
    project: z.array(z.string()).default([]),
    vendor: z.array(z.string()).default([]),
  }),
});

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
    refs: refsSchema.optional(),
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
    refs: refsSchema.optional(),
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
