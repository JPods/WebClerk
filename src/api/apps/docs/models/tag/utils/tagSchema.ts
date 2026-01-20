import * as z from "zod";

export const tagSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z.string().min(1, "Slug is required"),
  description: z.string().optional(),
  color: z.string().optional(),
  category: z.string().optional(),
});