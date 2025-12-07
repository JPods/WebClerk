import * as z from "zod";
import { baseTransactionSchema } from '../../base/utils/baseSchema';

export const invoiceSchema = baseTransactionSchema.extend({
  invoice_no: z.string(),
});