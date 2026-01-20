import * as z from "zod";

export const bundleSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  data: z.string().min(1, "Data is required"),
  version: z.string().min(1, "Version is required"),
});