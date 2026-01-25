import * as z from "zod";

export const purchaseReceiptSchema = z.object({
  id_purchase_receipt: z.string().optional(),
  dt_created: z.string().optional(),
  dt_updated: z.string().optional(),
  purchaseorder_id: z.number().min(1, "Purchase order ID is required"),
  receipt_date: z.string().min(1, "Receipt date is required"),
  received_by: z.string().min(1, "Received by is required"),
  notes: z.string().optional(),
});