import { z } from 'zod';

export const requisitionSchema = z.object({
  id_requisition: z.string().optional(),
  dt_created: z.string().optional(),
  dt_updated: z.string().optional(),
  requisition_no: z.string().min(1, 'Requisition number is required'),
});

export type RequisitionFormData = z.infer<typeof requisitionSchema>;