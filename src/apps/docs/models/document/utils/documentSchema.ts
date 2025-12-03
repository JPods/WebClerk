import * as z from "zod";

export const documentSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z.string().min(1, "Slug is required"),
  content: z.string().min(1, "Content is required"),
  summary: z.string().min(1, "Summary is required"),
  category: z.string().min(1, "Category is required"),
  status: z.string().min(1, "Status is required"),
  parent_id: z.number().nullable().optional(),
  doc_type: z.string().optional(),
  author_id: z.number().optional(),
});