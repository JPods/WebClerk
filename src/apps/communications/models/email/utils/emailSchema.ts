import * as z from "zod";

export const emailSchema = z.object({
  email: z
    .string()
    .email("Invalid from email")
    .min(1, "From email is required"),
  name: z.string().min(1, "Name is required"),
  attention: z.string().optional(),
  opt_out: z.string().optional(),
  is_primary: z.boolean(),
  is_verified: z.boolean(),
});
