/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import * as z from "zod";
import { baseTransactionSchema } from "../../base/utils/baseSchema";
import { baseLineItemSchema } from "../../base/utils/baseLineItemSchema";

// Valid invoice status values
const validInvoiceStatuses = [
  "draft",
  "sent",
  "paid",
  "overdue",
  "cancelled",
] as const;

// Invoice Line schema
export const invoiceLineSchema = baseLineItemSchema
  .extend({
    description: z
      .string()
      .min(1, "Description is required")
      .max(255, "Description must be 255 characters or less"),
    quantity: z.number().positive("Quantity must be greater than zero"),
    unit_price: z.number().min(0, "Unit price must be non-negative"),
    tax_rate: z
      .number()
      .min(0, "Tax rate must be non-negative")
      .max(1, "Tax rate cannot exceed 100%"),
    discount_amount: z.number().min(0, "Discount cannot be negative"),
    line_total: z.number().min(0, "Line total must be non-negative"),
    item_name: z.string().optional(),
    item_id: z.number().optional(),
    parent: z.number().optional(),
    id: z.number().optional(),
  })
  .refine(
    (data) => {
      const extended = data.quantity * data.unit_price;
      return !(data.discount_amount && data.discount_amount > extended);
    },
    {
      message: "Discount amount cannot exceed the extended price",
      path: ["discount_amount"],
    }
  );

// Base transaction with invoice-safe defaults (legacy invoice form does not capture these fields directly)
const baseInvoiceTransactionSchema = baseTransactionSchema.extend({
  id_transaction: z.number().optional(),
  customer_id: z.number().int().nonnegative().optional(),
  total: z.number().nonnegative().optional(),
  tax: z.number().nonnegative().optional(),
  discount: z.number().nonnegative().optional(),
});

// Enhanced invoice schema with legacy (Vue) invoice form fields
export const invoiceSchema = baseInvoiceTransactionSchema
  .extend({
    ida: z.string().min(1, "Invoice number is required"),
    status: z.enum(validInvoiceStatuses, {
      errorMap: () => ({
        message: `Status must be one of: ${validInvoiceStatuses.join(", ")}`,
      }),
    }),
    vendor_id: z.number().optional(),
    manufacturer_id: z.number().optional(),
    price_level: z.string().optional(),

    // Contact and addressing (ported from vue2020 InvoiceForm)
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
    salesName: z.string().optional(),
    salesNameID: z.string().optional(),
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

    // Date and finance fields (kept optional)
    invoice_date: z.string().optional(),
    due_date: z.string().optional(),
    payment_terms: z
      .string()
      .max(100, "Payment terms must be 100 characters or less")
      .optional(),
    subtotal: z.number().nonnegative().optional(),
    tax_amount: z.number().nonnegative().optional(),
    total: z.number().nonnegative().optional(),
    balance: z.number().optional(),
    totals: z.any().optional(),

    payment_method: z
      .string()
      .max(50, "Payment method must be 50 characters or less")
      .optional(),
    notes: z
      .string()
      .max(1000, "Notes must be 1000 characters or less")
      .optional(),
    priority: z
      .string()
      .max(32, "Priority must be 32 characters or less")
      .optional(),

    // JSON fields
    cost: z.any().optional(),
    sell: z.any().optional(),
    finance: z.any().optional(),
    flow: z.any().optional(),
    source: z.any().optional(),
    subtotals: z.any().optional(),

    // Line items
    lines: z.any().default([]),

    // Timestamps
    dt_created: z.any().optional(),
    dt_updated: z.any().optional(),
    dt_modified: z.any().optional(),

    // Additional fields
    valid_until: z.any().optional(),
    version: z.any().optional(),
  })
  .refine(
    (data) => {
      if (data.invoice_date && data.due_date) {
        const invoiceDate = new Date(data.invoice_date);
        const dueDate = new Date(data.due_date);
        return dueDate > invoiceDate;
      }
      return true;
    },
    {
      message: "Due date must be after invoice date",
      path: ["due_date"],
    }
  )
  .refine(
    (data) => {
      // Balance validation uses totals envelope when available
      const total = data.totals?.total;
      const received = data.totals?.received ?? 0;
      const balance = data.totals?.balance;
      if (total !== undefined && balance !== undefined) {
        return Math.abs(balance - (total - received)) < 0.01;
      }
      return true;
    },
    {
      message: "Balance must equal total minus received",
      path: ["balance"],
    }
  )
  .refine(
    (data) => {
      if (
        data.customer_id &&
        data.vendor_id &&
        data.customer_id === data.vendor_id
      ) {
        return false;
      }
      return true;
    },
    {
      message: "Customer and vendor cannot be the same entity",
      path: ["vendor_id"],
    }
  );

// Type exports
export type InvoiceFormData = z.infer<typeof invoiceSchema>;
export type InvoiceLineFormData = z.infer<typeof invoiceLineSchema>;
