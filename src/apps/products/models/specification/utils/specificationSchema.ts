import * as z from "zod";

export const specificationSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  requirements: z.string().min(1, "Requirements are required"),
  version: z.string().min(1, "Version is required"),
});