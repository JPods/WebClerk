import * as z from "zod";

export const exchangeTransactionSchema = z.object({
  from_currency: z.string().min(1, "From currency is required"),
  to_currency: z.string().min(1, "To currency is required"),
  amount: z.number().min(0, "Amount must be positive"),
  rate: z.number().min(0, "Rate must be positive"),
  date: z.string().min(1, "Date is required"),
  status: z.string().min(1, "Status is required"),
});