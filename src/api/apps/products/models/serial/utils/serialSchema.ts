import * as z from "zod";

export const serialSchema = z.object({
  serial_number: z.string().min(1, "Serial number is required"),
  item_id: z.string().min(1, "Item ID is required"),
  status: z.string().min(1, "Status is required"),
  description: z.string().optional(),
});