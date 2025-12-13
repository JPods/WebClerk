import * as z from "zod";

export const matricsSchema = z.object({
  name: z.string().min(1, "Name is required"),
  value: z.number().min(0, "Value must be positive"),
  unit: z.string().min(1, "Unit is required"),
  description: z.string().optional(),
});