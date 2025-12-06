import * as z from "zod";

export const baseTransactionSchema = z.object({
  id_transaction: z.string().optional(),
  dt_created: z.string().optional(),
  dt_updated: z.string().optional(),
  customer_id: z.string().min(1, "Customer ID is required"),
  total: z.number().min(0, "Total must be non-negative"),
  tax: z.number().min(0, "Tax must be non-negative").optional().default(0),
  discount: z.number().min(0, "Discount must be non-negative").optional().default(0),
  metadata: z.any().optional(),
  prefs: z.any().optional(),
  refs: z.any().optional(),
});