import * as z from "zod";

// Valid status values
const validStatuses = ['planned', 'sent', 'accepted', 'rejected', 'cancelled'] as const;

// Price structure schema
const priceSchema = z.object({
  sell: z.number().min(0, "Sell price must be non-negative"),
  cost: z.number().min(0, "Cost price must be non-negative").optional(),
}).optional();

// Proposal schema with comprehensive validation
export const proposalSchema = z.object({
  // Basic fields
  ida: z.string().max(50, "Proposal ID must be 50 characters or less").optional(),
  status: z.enum(validStatuses, {
    errorMap: () => ({ message: `Status must be one of: ${validStatuses.join(', ')}` })
  }).optional(),
  priority: z.string().max(32, "Priority must be 32 characters or less").optional(),
  price_level: z.string().max(50, "Price level must be 50 characters or less").optional(),

  // Customer/Vendor - required for creation
  id_customer: z.number().int().positive("Customer ID must be a positive integer"),
  id_manufacturer: z.number().int().min(0, "Manufacturer ID must be non-negative").optional(),
  id_vendor: z.number().int().min(0, "Vendor ID must be non-negative").optional(),

  // JSON fields with structure validation
  cost: z.record(z.any()).optional(),
  sell: z.record(z.any()).optional(),
  finance: z.record(z.any()).optional(),
  flow: z.record(z.any()).optional(),
  source: z.record(z.any()).optional(),
  action: z.record(z.any()).optional(),

  // Timestamps (readonly)
  dt_created: z.string().optional(),
  dt_modified: z.string().optional(),
  version: z.number().optional(),
}).refine((data) => {
  // Cross-field validation: customer and vendor cannot be the same
  if (data.id_customer && data.id_vendor && data.id_customer === data.id_vendor) {
    return false;
  }
  return true;
}, {
  message: "Customer and vendor cannot be the same entity",
  path: ["id_vendor"]
});

// Proposal Line schema
export const proposalLineSchema = z.object({
  // Required fields
  description: z.string().min(1, "Description is required").max(255, "Description must be 255 characters or less"),
  quantity: z.number().positive("Quantity must be greater than zero"),

  // Price structure
  price: priceSchema,

  // Optional fields
  discount_amount: z.number().min(0, "Discount cannot be negative").optional().default(0),

  // Readonly fields (for validation of existing data)
  extended_price: z.number().optional(),
  item_name: z.string().optional(),
  unit_cost: z.number().optional(),
  line_margin: z.number().optional(),

  // IDs
  item_id: z.number().optional(),
  parent: z.number().optional(),
  id: z.number().optional(),
}).refine((data) => {
  // Validate discount doesn't exceed extended price
  if (data.price?.sell && data.quantity && data.discount_amount) {
    const extended = data.quantity * data.price.sell;
    if (data.discount_amount > extended) {
      return false;
    }
  }
  return true;
}, {
  message: "Discount amount cannot exceed the extended price",
  path: ["discount_amount"]
});

// Type exports
export type ProposalFormData = z.infer<typeof proposalSchema>;
export type ProposalLineFormData = z.infer<typeof proposalLineSchema>;