/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { z } from "zod";

import { baseTransactionSchema } from "../../base/utils/baseSchema";

export const workOrderSchema = baseTransactionSchema.extend({
	workorder_no: z.string().min(1, "Workorder number is required"),
});