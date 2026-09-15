/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const invoiceLineSchema = z.object({
  parent: z.number().optional(),
  item_id: z.number().optional(),
  description: z.string().optional(),
  quantity: z.number().optional(),
  unit_price: z.number().optional(),
  discount_amount: z.number().optional(),
  line_total: z.number().optional(),
});