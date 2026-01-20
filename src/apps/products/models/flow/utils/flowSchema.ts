import * as z from "zod";

export const flowSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  steps: z.string().min(1, "Steps are required"),
});