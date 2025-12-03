import { z } from 'zod';

export const purchaseOrderSchema = z.object({
  purchase_order_no: z.string().min(1, 'Purchase order number is required'),
});

export type PurchaseOrderFormData = z.infer<typeof purchaseOrderSchema>;