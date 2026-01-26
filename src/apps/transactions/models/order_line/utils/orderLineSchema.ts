import * as z from "zod";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

export const orderLineSchema = baseLineItemSchema.extend({
  order_id: z.number().min(1, "Order ID is required"),
});