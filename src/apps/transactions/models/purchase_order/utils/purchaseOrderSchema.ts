import * as z from "zod";
import { baseTransactionSchema } from '../../base/utils/baseSchema';

export const purchaseOrderSchema = baseTransactionSchema.extend({
  purchase_order_no: z.string().optional(),
});