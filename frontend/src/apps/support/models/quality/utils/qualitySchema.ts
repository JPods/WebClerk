/**
 * Zod schemas for quality record validation.
 * One base schema + type-specific extensions.
 */
import * as z from 'zod';

export const qualityBaseSchema = z.object({
  task: z.string().min(1, 'Title is required'),
  description: z.string().min(1, 'Description is required'),
  status: z.string().default('open'),
  priority: z.number().min(1).max(10).default(5),
  project_name: z.string().default('Quality'),
});

export const ncrSchema = qualityBaseSchema.extend({
  item_name: z.string().min(1, 'Item name is required'),
  actual_condition: z.string().min(1, 'Describe actual condition'),
  required_condition: z.string().min(1, 'Describe required condition'),
});

export const carSchema = qualityBaseSchema.extend({
  action_type: z.enum(['corrective', 'preventive', 'audit']),
  discrepancy: z.string().min(1, 'Describe the discrepancy'),
});

export const deviationSchema = qualityBaseSchema.extend({
  request_type: z.enum(['deviation', 'waiver']),
  justification: z.string().min(1, 'Justification is required'),
});

export const dcrSchema = qualityBaseSchema.extend({
  action_type: z.enum(['new', 'revision', 'cancellation', 'supersedes']),
  summary: z.string().min(1, 'Summary recommendation is required'),
});

export const requestSchema = qualityBaseSchema.extend({
  target_org: z.string().min(1, 'Target organization is required'),
  originator_name: z.string().min(1, 'Your name is required'),
  originator_email: z.string().email('Valid email required'),
});

export const QUALITY_SCHEMAS = {
  ncr: ncrSchema,
  car: carSchema,
  deviation: deviationSchema,
  dcr: dcrSchema,
  request: requestSchema,
} as const;
