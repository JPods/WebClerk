import * as z from "zod";

export const currencySchema = z.object({
  code: z.string().min(1, "Code is required"),
  name: z.string().min(1, "Name is required"),
  symbol: z.string().min(1, "Symbol is required"),
  rate: z.number().min(0, "Rate must be positive"),
});