/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

const priceObject = z.object({
  base: z.number().nonnegative().optional(),
  msrp: z.number().nonnegative().optional(),
  retail: z.number().nonnegative().optional(),
  wholesale: z.number().nonnegative().optional(),
  distributor: z.number().nonnegative().optional(),
  sample: z.number().nonnegative().optional(),
  qty_breaks: z.array(z.any()).optional(),
  currency: z.string().optional(),
  history: z.array(z.any()).optional(),
}).partial();

export const itemSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  // price may be a simple number or an object with optional fields
  price: z.union([z.number().min(0, "Price must be positive"), priceObject]).optional(),
  category: z.string().min(1, "Category is required"),
});
