import * as z from "zod";

export const warehouseSchema = z.object({
  name: z.string().min(1, "Name is required"),
  location: z.string().min(1, "Location is required"),
  capacity: z.number().min(0, "Capacity must be positive"),
  manager: z.string().min(1, "Manager is required"),
});