import * as z from "zod";

export const glAccountSchema = z.object({
  code: z.string().min(1, "Code is required"),
  name: z.string().min(1, "Name is required"),
  type: z.string().min(1, "Type is required"),
  balance: z.number().optional(),
  category: z.string().optional(),
  division: z.string().optional(),
  used_for: z.string().optional(),
  account_debit: z.number().optional(),
  account_credit: z.number().optional(),
  comment: z.string().optional(),
});