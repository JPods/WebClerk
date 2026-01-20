import * as z from "zod";

export const usageSchema = z.object({
  item_id: z.string().min(1, "Item ID is required"),
  quantity_used: z.number().min(0, "Quantity must be positive"),
  date_used: z.string().min(1, "Date used is required"),
  user_id: z.string().min(1, "User ID is required"),
  notes: z.string().optional(),
});