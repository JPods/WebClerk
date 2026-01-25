import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const workOrderLineSchema = baseLineItemSchema.extend({
  workorder_id: z.number().min(1, "Work order ID is required"),
});