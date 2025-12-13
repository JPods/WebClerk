import * as z from "zod";

export const baseTransactionSchema = z.object({
  id_transaction: z.string().optional(),
  dt_created: z.number().optional(),
  dt_updated: z.number().optional(),
  customer_id: z.number().min(1, "Customer ID is required"),
  total: z.number(),
  tax: z.number(),
  discount: z.number(),
  metadata: z.any().optional(),
  prefs: z.any().optional(),
  refs: z.any().optional(),
});