import * as z from "zod";

export const serviceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  cost: z.number().min(0, "Cost must be positive"),
  date: z.string().min(1, "Date is required"),
});