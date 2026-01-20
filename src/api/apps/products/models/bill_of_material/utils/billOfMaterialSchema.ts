import * as z from "zod";

export const billOfMaterialSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  product_id: z.string().min(1, "Product ID is required"),
  components: z.string().min(1, "Components are required"),
});