import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const salesOrderLineSchema = baseLineItemSchema.extend({
  salesorder_id: z.number().min(1, "Sales order ID is required"),
});