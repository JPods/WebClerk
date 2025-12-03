import { z } from 'zod';

export const invoiceSchema = z.object({
  invoice_no: z.string().min(1, 'Invoice number is required'),
});

export type InvoiceFormData = z.infer<typeof invoiceSchema>;