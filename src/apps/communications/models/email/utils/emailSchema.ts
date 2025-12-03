import * as z from "zod";

export const emailSchema = z.object({
  subject: z.string().min(1, "Subject is required"),
  body: z.string().min(1, "Body is required"),
  from_email: z.string().email("Invalid email").min(1, "From email is required"),
  to_email: z.string().email("Invalid email").min(1, "To email is required"),
  status: z.string().min(1, "Status is required"),
});