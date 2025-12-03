import * as z from "zod";

export const customerSchema = z.object({
  name: z.string().min(1, "Name is required"),
  address: z.string().min(1, "Address is required"),
  phone: z.string().min(1, "Phone is required"),
  email: z.string().email("Invalid email"),
  website: z.string().url().optional().or(z.literal("")),
  customer_number: z.string().min(1, "Customer number is required"),
});