import * as z from "zod";

export const notificationSchema = z.object({
  user_id: z.number().min(1, "User ID is required"),
  message: z.string().min(1, "Message is required"),
  type: z.string().min(1, "Type is required"),
  read: z.boolean(),
});