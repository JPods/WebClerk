/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";

export const documentSchema = z.object({
  // Core identifiers
  name: z.string().optional(),
  slug: z.string().optional(),
  status: z.string().optional(),
  
  // Content fields
  description: z.string().optional(),
  body: z.string().optional(),
  comment: z.string().optional(),
  
  // Classification
  model_name: z.string().optional(),
  confidential: z.string().optional(),
  
  // Technical metadata
  mime_type: z.string().optional(),
  checksum: z.string().optional(),
  size_bytes: z.number().nullable().optional(),
  retention_period: z.number().nullable().optional(),
  sequence: z.number().nullable().optional(),
  count_accessed: z.number().nullable().optional(),
  
  // JSON fields
  data: z.any().optional(),
  copyright: z.any().optional(),
  path: z.any().optional(),
});