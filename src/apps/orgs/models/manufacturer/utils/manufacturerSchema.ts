import * as z from "zod";

export const manufacturerSchema = z.object({
  name: z.string().min(1, "Name is required"),
  address: z.string().min(1, "Address is required"),
  phone: z.string().min(1, "Phone is required"),
  email: z.string().email("Invalid email"),
  website: z.string().url().optional().or(z.literal("")),
  manufacturer_code: z.string().min(1, "Manufacturer code is required"),
});