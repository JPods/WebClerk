/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const orgItemSchema = z.object({
  org_id: z.string().min(1, "Org ID is required"),
  item_id: z.string().min(1, "Item ID is required"),
  quantity: z.number().min(0, "Quantity must be positive"),
  description: z.string().optional(),
});