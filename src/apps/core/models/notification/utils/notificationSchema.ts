/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const notificationSchema = z.object({
  user_id: z.number().min(1, "User ID is required"),
  message: z.string().min(1, "Message is required"),
  type: z.string().min(1, "Type is required"),
  read: z.boolean(),
});