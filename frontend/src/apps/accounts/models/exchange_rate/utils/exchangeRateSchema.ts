/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const exchangeRateSchema = z.object({
  from_currency: z.string().min(1, "From currency is required"),
  to_currency: z.string().min(1, "To currency is required"),
  rate: z.number().min(0, "Rate must be positive"),
  date: z.string().min(1, "Date is required"),
});