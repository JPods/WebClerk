import { z } from 'zod';

export const requisitionSchema = z.object({
  requisition_no: z.string().min(1, 'Requisition number is required'),
});

export type RequisitionFormData = z.infer<typeof requisitionSchema>;