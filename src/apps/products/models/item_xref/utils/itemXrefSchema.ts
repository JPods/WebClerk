import * as z from "zod";

export const itemXrefSchema = z.object({
  item_id_1: z.string().min(1, "Item ID 1 is required"),
  item_id_2: z.string().min(1, "Item ID 2 is required"),
  relationship_type: z.string().min(1, "Relationship type is required"),
  description: z.string().optional(),
});