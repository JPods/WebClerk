import * as z from "zod";

export const emailSchema = z.object({
  subject: z.string().min(1, "Subject is required"),
  status: z.enum(["draft", "sent", "failed"], { required_error: "Status is required" }),
  from_email: z.string().email("Invalid from email").min(1, "From email is required"),
  to_email: z.string().email("Invalid to email").min(1, "To email is required"),
  body: z.string().min(1, "Body is required"),
});