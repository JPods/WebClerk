import { z } from "zod";

import { baseTransactionSchema } from "../../base/utils/baseSchema";

export const workOrderSchema = baseTransactionSchema.extend({
	workorder_no: z.string().min(1, "Workorder number is required"),
});