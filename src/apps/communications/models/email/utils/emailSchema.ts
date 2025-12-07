import * as z from "zod";

export const emailSchema = z.object({
  email: z.string().email("Invalid email").min(1, "Email is required"),
  name: z.string().optional(),
  attention: z.string().optional(),
  type: z.string().optional(),
});