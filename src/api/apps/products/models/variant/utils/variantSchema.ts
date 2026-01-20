import * as z from "zod";

export const variantSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  item_id: z.string().min(1, "Item ID is required"),
  attributes: z.string().min(1, "Attributes are required"),
});