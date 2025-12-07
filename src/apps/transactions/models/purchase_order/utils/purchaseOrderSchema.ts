import * as z from "zod";
import { baseTransactionSchema } from '../../base/utils/baseSchema';
import { baseLineItemSchema } from '../../base/utils/baseLineItemSchema';

// Valid status values for purchase orders
const validPOStatuses = ['draft', 'approved', 'rejected', 'received', 'closed'] as const;

// Price structure schema (adapted for PO - focus on cost)
const poPriceSchema = z.object({
  cost: z.number().min(0, "Cost price must be non-negative"),
  sell: z.number().min(0, "Sell price must be non-negative").optional(),
}).optional();

// Purchase Order Line schema
export const purchaseOrderLineSchema = baseLineItemSchema.extend({
  // Required fields
  description: z.string().min(1, "Description is required").max(255, "Description must be 255 characters or less"),
  quantity: z.number().positive("Quantity must be greater than zero"),

  // Price structure
  price: poPriceSchema,

  // Optional fields
  discount_amount: z.number().min(0, "Discount cannot be negative"),

  // Readonly fields (for validation of existing data)
  extended_price: z.number().optional(),
  unit_cost: z.number().optional(),
  line_margin: z.number().optional(),

  // IDs
  item_id: z.number().optional(),
  parent: z.number().optional(),
  id: z.number().optional(),
}).refine((data) => {
  // Validate discount doesn't exceed extended price
  if (data.price?.cost && data.quantity && data.discount_amount) {
    const extended = data.quantity * data.price.cost;
    if (data.discount_amount > extended) {
      return false;
    }
  }
  return true;
}, {
  message: "Discount amount cannot exceed the extended price",
  path: ["discount_amount"]
});

// Purchase Order schema with comprehensive validation
export const purchaseOrderSchema = baseTransactionSchema.extend({
  // Basic fields
  purchase_order_no: z.string().max(50, "Purchase Order No must be 50 characters or less").optional(),
  status: z.enum(validPOStatuses, {
    errorMap: () => ({ message: `Status must be one of: ${validPOStatuses.join(', ')}` })
  }).optional(),

  // Vendor/Supplier reference
  id_vendor: z.number().int().positive("Vendor ID must be a positive integer"),

  // Date fields
  order_date: z.string().optional(), // ISO date string
  required_date: z.string().optional(), // ISO date string
  approval_date: z.string().optional(), // ISO date string

  // PO-specific fields
  shipping_terms: z.string().max(255, "Shipping terms must be 255 characters or less").optional(),
  payment_terms: z.string().max(255, "Payment terms must be 255 characters or less").optional(),

  // Line items
  line_items: z.array(purchaseOrderLineSchema).optional(),

  // Financial summary fields
  subtotal: z.number().min(0, "Subtotal must be non-negative").optional(),

  // JSON fields with structure validation (adapted from proposal)
  finance: z.record(z.any()).optional(),
  flow: z.record(z.any()).optional(),
  source: z.record(z.any()).optional(),
  action: z.record(z.any()).optional(),
}).refine((data) => {
  // Business rule: required date must be after order date
  if (data.order_date && data.required_date) {
    const orderDate = new Date(data.order_date);
    const requiredDate = new Date(data.required_date);
    if (requiredDate <= orderDate) {
      return false;
    }
  }
  return true;
}, {
  message: "Required date must be after order date",
  path: ["required_date"]
}).refine((data) => {
  // Approval workflow: if status is approved, approval_date should be set
  if (data.status === 'approved' && !data.approval_date) {
    return false;
  }
  return true;
}, {
  message: "Approval date is required when status is approved",
  path: ["approval_date"]
});

// Type exports
export type PurchaseOrderFormData = z.infer<typeof purchaseOrderSchema>;
export type PurchaseOrderLineFormData = z.infer<typeof purchaseOrderLineSchema>;