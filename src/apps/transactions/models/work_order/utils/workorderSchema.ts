import { z } from 'zod';

export const workorderSchema = z.object({
  workorder_no: z.string().min(1, 'Workorder number is required'),
});

export type WorkorderFormData = z.infer<typeof workorderSchema>;