/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const orderLineSchema = baseLineItemSchema.extend({
  order_id: z.number().min(1, "Order ID is required"),
});