import * as z from "zod";

// Valid status values for sales orders
const validStatuses = ['draft', 'confirmed', 'shipped', 'delivered', 'cancelled'] as const;

// Price structure schema
const priceSchema = z.object({
  sell: z.number().min(0, "Sell price must be non-negative"),
  cost: z.number().min(0, "Cost price must be non-negative").optional(),
}).optional();

// Sales Order Line schema
export const salesOrderLineSchema = z.object({
  // Required fields
  description: z.string().min(1, "Description is required").max(255, "Description must be 255 characters or less"),
  quantity: z.number().positive("Quantity must be greater than zero"),

  // Price structure
  price: priceSchema,

  // Optional fields
  discount_amount: z.number().min(0, "Discount cannot be negative"),

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

// Sales Order schema with comprehensive validation
export const salesOrderSchema = z.object({
  // Contact and address fields
  company: z.string().max(255, "Company must be 255 characters or less").optional(),
  attention: z.string().max(255, "Attention must be 255 characters or less").optional(),
  address1: z.string().max(255, "Address1 must be 255 characters or less").optional(),
  address2: z.string().max(255, "Address2 must be 255 characters or less").optional(),
  city: z.string().max(100, "City must be 100 characters or less").optional(),
  state: z.string().max(64, "State must be 64 characters or less").optional(),
  zip: z.string().max(32, "Zip must be 32 characters or less").optional(),
  email: z.string().email("Invalid email").optional(),
  phoneCell: z.string().max(64, "Cell phone must be 64 characters or less").optional(),
  phone: z.string().max(64, "Phone must be 64 characters or less").optional(),

  // Workflow / assignment fields
  actionBy: z.string().max(128, "actionBy must be 128 characters or less").optional(),
  action: z.string().max(128, "action must be 128 characters or less").optional(),
  actionDate: z.string().optional(),
  actionTime: z.string().optional(),
  salesNameID: z.string().max(128, "salesNameID must be 128 characters or less").optional(),
  orderedBy: z.string().max(128, "orderedBy must be 128 characters or less").optional(),
  contractDetailTag: z.string().max(128, "contractDetailTag must be 128 characters or less").optional(),
  terms: z.string().max(128, "terms must be 128 characters or less").optional(),
  typeSale: z.string().max(128, "typeSale must be 128 characters or less").optional(),
  taxJuris: z.string().max(128, "taxJuris must be 128 characters or less").optional(),
  adSource: z.string().max(128, "adSource must be 128 characters or less").optional(),

  // Commenting
  addComment: z.string().max(2000, "Add comment must be 2000 characters or less").optional(),
  comment: z.string().max(4000, "Comment must be 4000 characters or less").optional(),
  contractDetail: z.string().max(4000, "Contract detail must be 4000 characters or less").optional(),

  // Base transaction fields
  id_transaction: z.string().optional(),
  dt_created: z.union([z.string(), z.number()]).optional(),
  dt_updated: z.union([z.string(), z.number()]).optional(),
  id_customer: z.coerce.number().min(1, "Customer ID is required"),
  total: z.coerce.number(),
  tax: z.coerce.number(),
  discount: z.coerce.number(),
  metadata: z.any().optional(),
  prefs: z.any().optional(),
  refs: z.any().optional(),

  // Sales order specific fields
  sales_order_no: z.string().optional(),
  status: z.enum(validStatuses, {
    errorMap: () => ({ message: `Status must be one of: ${validStatuses.join(', ')}` })
  }).optional(),
  priority: z.string().max(32, "Priority must be 32 characters or less").optional(),
  price_level: z.string().max(50, "Price level must be 50 characters or less").optional(),

  // Customer/Vendor references
  id_manufacturer: z.coerce.number().int().min(0, "Manufacturer ID must be non-negative").optional(),
  id_vendor: z.coerce.number().int().min(0, "Vendor ID must be non-negative").optional(),

  // Financial summary fields
  subtotal: z.coerce.number().optional(),

  // JSON fields with structure validation - accept string, object, or undefined
  cost: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
  sell: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
  finance: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
  flow: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
  source: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
  action: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),

  // Line items
  lines: z.array(salesOrderLineSchema).optional(),

  // Date fields
  dt_modified: z.union([z.string(), z.number()]).optional(),
  due_date: z.string().optional(),
  valid_until: z.string().optional(),
  version: z.coerce.number().optional(),
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

// Type exports
export type SalesOrderFormData = z.infer<typeof salesOrderSchema>;
export type SalesOrderLineFormData = z.infer<typeof salesOrderLineSchema>;