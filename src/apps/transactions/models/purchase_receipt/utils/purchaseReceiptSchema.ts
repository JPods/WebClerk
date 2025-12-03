import * as z from "zod";

export const purchaseReceiptSchema = z.object({
  purchase_order_id: z.number().min(1, "Purchase order ID is required"),
  receipt_date: z.string().min(1, "Receipt date is required"),
  received_by: z.string().min(1, "Received by is required"),
  notes: z.string().optional(),
});