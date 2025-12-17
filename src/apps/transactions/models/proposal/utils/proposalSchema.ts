import * as z from "zod";

// Valid status values
const validStatuses = ["planned", "sent", "accepted", "rejected", "cancelled"] as const;

// Price structure schema
const priceSchema = z
  .object({
    sell: z.number().min(0, "Sell price must be non-negative"),
    cost: z.number().min(0, "Cost price must be non-negative").optional(),
  })
  .optional();

// Proposal schema with comprehensive validation (now aligned to legacy Vue proposal form)
export const proposalSchema = z
  .object({
    // Basic fields
    ida: z.string().max(50, "Proposal ID must be 50 characters or less").optional().or(z.literal("")),
    status: z.enum(validStatuses, {
      errorMap: () => ({ message: `Status must be one of: ${validStatuses.join(", ")}` }),
    }).default("planned"),
    priority: z.string().max(32, "Priority must be 32 characters or less").optional().or(z.literal("")),
    price_level: z.string().max(50, "Price level must be 50 characters or less").optional().or(z.literal("")),

    // Customer/Vendor - required for creation
    id_customer: z
      .number({ invalid_type_error: "Please select a customer" })
      .int()
      .positive("Please select a customer")
      .optional(),
    id_manufacturer: z.coerce.number().int().min(0, "Manufacturer ID must be non-negative").optional(),
    id_vendor: z.number().int().positive("Vendor ID must be a positive integer").optional().nullable(),

    // Contact and address fields
    company: z.string().min(1, "Company is required"),
    attention: z.string().min(1, "Attention is required"),
    address1: z.string().min(1, "Address1 is required"),
    address2: z.string().optional(),
    city: z.string().min(1, "City is required"),
    state: z.string().min(2, "State is required"),
    zip: z.string().min(1, "Zip is required"),
    email: z.string().email("Invalid email").optional(),
    phoneCell: z.string().optional(),
    phone: z.string().optional(),

    // Actioning and sales metadata
    actionBy: z.string().optional(),
    action: z.string().optional(),
    actionDate: z.string().optional(),
    actionTime: z.string().optional(),
    salesNameId: z.string().optional(),
    orderedBy: z.string().optional(),
    contractDetailTag: z.string().optional(),
    terms: z.string().optional(),
    typeSale: z.string().optional(),
    taxJuris: z.string().optional(),
    adSource: z.string().optional(),

    // Commentary and extended details
    addComment: z.string().optional(),
    comment: z.string().optional(),
    contractDetail: z.string().optional(),

    // JSON fields with structure validation
    cost: z.record(z.any()).optional(),
    sell: z.record(z.any()).optional(),
    finance: z.record(z.any()).optional(),
    flow: z.record(z.any()).optional(),
    source: z.record(z.any()).optional(),
    action: z.record(z.any()).optional(),

    // Timestamps (readonly) - can be string or number (timestamps)
    dt_created: z.union([z.string(), z.number()]).optional(),
    dt_modified: z.union([z.string(), z.number()]).optional(),
    version: z.number().optional(),
    id: z.number().optional(),
  })
  .refine(
    (data) => {
      if (data.id_customer && data.id_vendor && data.id_customer === data.id_vendor) {
        return false;
      }
      return true;
    },
    {
      message: "Customer and vendor cannot be the same entity",
      path: ["id_vendor"],
    }
  );

// Proposal Line schema
export const proposalLineSchema = z
  .object({
    description: z
      .string()
      .min(1, "Description is required")
      .max(255, "Description must be 255 characters or less"),
    quantity: z.coerce.number().positive("Quantity must be greater than zero"),
    price: priceSchema,
    discount_amount: z.coerce.number().min(0, "Discount cannot be negative").optional().default(0),
    extended_price: z.number().optional(),
    item_name: z.string().optional().or(z.literal("")),
    unit_cost: z.number().optional(),
    line_margin: z.number().optional(),
    item_id: z.coerce.number().optional().nullable(),
    parent: z.coerce.number().optional().nullable(),
    id: z.number().optional(),
  })
  .refine(
    (data) => {
      if (data.price?.sell && data.quantity && data.discount_amount) {
        const extended = data.quantity * data.price.sell;
        if (data.discount_amount > extended) {
          return false;
        }
      }
      return true;
    },
    {
      message: "Discount amount cannot exceed the extended price",
      path: ["discount_amount"],
    }
  );

// Type exports
export type ProposalFormData = z.infer<typeof proposalSchema>;
export type ProposalLineFormData = z.infer<typeof proposalLineSchema>;