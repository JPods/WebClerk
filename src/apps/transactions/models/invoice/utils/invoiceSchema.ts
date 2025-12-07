import * as z from "zod";
import { baseTransactionSchema } from '../../base/utils/baseSchema';
import { baseLineItemSchema } from '../../base/utils/baseLineItemSchema';

// Valid invoice status values
const validInvoiceStatuses = ['draft', 'sent', 'paid', 'overdue', 'cancelled'] as const;

// Invoice Line schema
export const invoiceLineSchema = baseLineItemSchema.extend({
  // Required fields
  description: z.string().min(1, "Description is required").max(255, "Description must be 255 characters or less"),
  quantity: z.number().positive("Quantity must be greater than zero"),

  // Price and tax fields
  unit_price: z.number().min(0, "Unit price must be non-negative"),
  tax_rate: z.number().min(0, "Tax rate must be non-negative").max(1, "Tax rate cannot exceed 100%"),
  discount_amount: z.number().min(0, "Discount cannot be negative"),

  // Calculated fields
  line_total: z.number().min(0, "Line total must be non-negative"),

  // Optional fields
  item_name: z.string().optional(),

  // IDs
  item_id: z.number().optional(),
  parent: z.number().optional(),
  id: z.number().optional(),
}).refine((data) => {
  // Validate discount doesn't exceed line total
  const extended = data.quantity * data.unit_price;
  if (data.discount_amount && data.discount_amount > extended) {
    return false;
  }
  return true;
}, {
  message: "Discount amount cannot exceed the extended price",
  path: ["discount_amount"]
});

// Enhanced invoice schema
export const invoiceSchema = baseTransactionSchema.extend({
  // Override base id_transaction to be number
  id_transaction: z.number().optional(),

  // Invoice-specific fields
  invoice_no: z.string().min(1, "Invoice number is required"),
  status: z.enum(validInvoiceStatuses, {
    errorMap: () => ({ message: `Status must be one of: ${validInvoiceStatuses.join(', ')}` })
  }),

  // Customer/Vendor references (enhancing base)
  vendor_id: z.number().min(0, "Vendor ID must be non-negative").optional(),

  // Date fields
  invoice_date: z.string().optional(), // ISO date string
  due_date: z.string().optional(), // ISO date string
  payment_terms: z.string().max(100, "Payment terms must be 100 characters or less").optional(),

  // Financial summary fields
  subtotal: z.number().min(0, "Subtotal must be non-negative").optional(),
  tax_amount: z.number().min(0, "Tax amount must be non-negative").optional(),
  total_amount: z.number().min(0, "Total amount must be non-negative").optional(),
  paid_amount: z.number().min(0, "Paid amount must be non-negative"),
  balance: z.number().optional(),

  // Line items
  line_items: z.array(invoiceLineSchema),

  // Additional invoice-specific fields
  payment_method: z.string().max(50, "Payment method must be 50 characters or less").optional(),
  notes: z.string().max(1000, "Notes must be 1000 characters or less").optional(),

  // Priority and other fields (from proposal inspiration)
  priority: z.string().max(32, "Priority must be 32 characters or less").optional(),
}).refine((data) => {
  // Business rule: due date after invoice date
  if (data.invoice_date && data.due_date) {
    const invoiceDate = new Date(data.invoice_date);
    const dueDate = new Date(data.due_date);
    if (dueDate <= invoiceDate) {
      return false;
    }
  }
  return true;
}, {
  message: "Due date must be after invoice date",
  path: ["due_date"]
}).refine((data) => {
  // Business rule: balance = total - paid
  if (data.total_amount !== undefined && data.paid_amount !== undefined) {
    const calculatedBalance = data.total_amount - data.paid_amount;
    if (data.balance !== undefined && data.balance !== calculatedBalance) {
      return false;
    }
  }
  return true;
}, {
  message: "Balance must equal total amount minus paid amount",
  path: ["balance"]
}).refine((data) => {
  // Cross-field validation: customer and vendor cannot be the same
  if (data.customer_id && data.vendor_id && data.customer_id === data.vendor_id) {
    return false;
  }
  return true;
}, {
  message: "Customer and vendor cannot be the same entity",
  path: ["vendor_id"]
});

// Type exports
export type InvoiceFormData = z.infer<typeof invoiceSchema>;
export type InvoiceLineFormData = z.infer<typeof invoiceLineSchema>;