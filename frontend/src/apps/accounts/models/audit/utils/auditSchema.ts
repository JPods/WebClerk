/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const auditSchema = z.object({
  date: z.string().min(1, "Date is required"),
  action: z.string().min(1, "Action is required"),
  user: z.string().min(1, "User is required"),
  description: z.string().min(1, "Description is required"),
});