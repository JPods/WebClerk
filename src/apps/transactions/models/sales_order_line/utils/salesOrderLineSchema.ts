import * as z from "zod";

export const salesOrderLineSchema = z.object({
  sales_order_id: z.number().min(1, "Sales order ID is required"),
  item_id: z.number().min(1, "Item ID is required"),
  quantity: z.number().min(1, "Quantity must be at least 1"),
  unit_price: z.number().min(0, "Unit price must be non-negative"),
  line_total: z.number().min(0, "Line total must be non-negative"),
});