import * as z from "zod";

export const addressSchema = z.object({
  address1: z.string().min(1, "Address1 is required"),
  address2: z.string().min(1, "Address2 is required"),
  address_type: z.string().min(1, "Address Type is required"),
  full: z.string().min(1, "Full is required"),
  city: z.string().min(1, "City is required"),
  state: z.string().min(1, "State is required"),
  zip: z.string().min(1, "ZIP code is required"),
  country: z.string().min(1, "Country is required"),
  latitude: z.union([z.string(), z.number()]).transform((val) => String(val)),
  longitude: z.union([z.string(), z.number()]).transform((val) => String(val)),
});
