import * as z from "zod";

export const phoneSchema = z.object({
  number: z.string().min(1, "Phone number is required"),
  type: z.string().min(1, "Type is required"),
  country_code: z.string().min(1, "Country code is required"),
});