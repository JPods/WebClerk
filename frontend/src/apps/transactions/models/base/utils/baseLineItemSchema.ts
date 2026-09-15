/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const baseLineItemSchema = z.object({
  item_id: z.number().min(1, "Item ID is required"),
  quantity: z.number().min(0, "Quantity must be non-negative"),
  unit_price: z.number().min(0, "Unit price must be non-negative"),
  line_total: z.number().min(0, "Line total must be non-negative"),
  description: z.string().optional(),
});