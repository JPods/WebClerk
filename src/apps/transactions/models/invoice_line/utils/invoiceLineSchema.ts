import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const invoiceLineSchema = baseLineItemSchema.extend({
  invoice_id: z.number().min(1, "Invoice ID is required"),
});