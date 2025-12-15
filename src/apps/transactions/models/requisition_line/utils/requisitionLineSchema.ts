import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const requisitionLineSchema = baseLineItemSchema.extend({
  requisition_id: z.number().min(1, "Requisition ID is required"),
});