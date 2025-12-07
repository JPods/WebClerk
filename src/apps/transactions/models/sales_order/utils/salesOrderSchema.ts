import * as z from "zod";
import { baseTransactionSchema } from '../../base/utils/baseSchema';

export const salesOrderSchema = baseTransactionSchema.extend({
  sales_order_no: z.string().optional(),
});