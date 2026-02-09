import * as z from "zod";

export const employeeSchema = z.object({
  display_name: z.string().min(1, "Name is required"),
<<<<<<< HEAD
  org_type: z.string().default("Employee").optional(),
  status: z.string().min(1, "Status is required"),
  version: z.number().default(1).optional(),
=======
  org_type: z.string().default("employee"),
  status: z.string().optional(),
  version: z.number().default(1),
>>>>>>> d1a222c84b298f91fbac4235e31af26d947219dc
  is_active: z.boolean().default(false),
  // New scalar fields from wc3
  attention: z.string().nullable().optional(),
  contact_id: z.number().nullable().optional(),
  email: z.string().email().nullable().optional().or(z.literal("")),
  phone: z.string().nullable().optional(),
  price_level: z.string().nullable().optional(),
});
