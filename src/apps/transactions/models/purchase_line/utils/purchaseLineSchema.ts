import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const purchaseLineSchema = baseLineItemSchema.extend({
  purchase_id: z.number().min(1, "Purchase ID is required"),
});