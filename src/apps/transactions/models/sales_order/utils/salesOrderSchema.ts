import { z } from 'zod';

export const salesOrderSchema = z.object({
  sales_order_no: z.string().min(1, 'Sales order number is required'),
});

export type SalesOrderFormData = z.infer<typeof salesOrderSchema>;