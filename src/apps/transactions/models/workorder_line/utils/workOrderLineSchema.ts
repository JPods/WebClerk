/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const workOrderLineSchema = baseLineItemSchema.extend({
  workorder_id: z.number().min(1, "Work order ID is required"),
});