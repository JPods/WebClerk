import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const purchaseOrderLineSchema = baseLineItemSchema.extend({
  purchase_order_id: z.number().min(1, "Purchase order ID is required"),
});