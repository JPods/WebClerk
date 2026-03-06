import * as z from "zod";

// Valid status values for sales orders
const validStatuses = [
  "planned",
  "released",
  "in_progress",
  "hold",
  "complete",
  "canceled",
] as const;

// Price structure schema
const nonNaNNumber = z.coerce
  .number()
  .refine((value) => Number.isFinite(value), {
    message: "Value must be a valid number",
  });

const priceSchema = z
  .object({
    sell: nonNaNNumber,
    cost: nonNaNNumber.optional(),
  })
  .optional();

const quantitySchema = z.union([
  z.coerce.number().positive("Quantity must be greater than zero"),
  z
    .object({
      staged: z.coerce
        .number()
        .min(0, "Quantity staged must be non-negative")
        .optional(),
      active: z.coerce
        .number()
        .min(0, "Quantity active must be non-negative")
        .optional(),
      remaining: z.coerce
        .number()
        .min(0, "Quantity remaining must be non-negative")
        .optional(),
    })
    .passthrough()
    .refine(
      (value) => {
        const staged =
          typeof value.staged === "number" ? value.staged : undefined;
        return staged === undefined || staged > 0;
      },
      { message: "Quantity must be greater than zero" }
    ),
]);

// Order Line schema - permissive to allow any line data
export const orderLineSchema = z.record(z.any()).optional();

// Order schema with comprehensive validation
export const orderSchema = z
  .object({
    // Contact and address fields
    company: z
      .string()
      .max(255, "Company must be 255 characters or less")
      .optional(),
    attention: z
      .string()
      .max(255, "Attention must be 255 characters or less")
      .optional(),
    address1: z
      .string()
      .max(255, "Address1 must be 255 characters or less")
      .optional(),
    address2: z
      .string()
      .max(255, "Address2 must be 255 characters or less")
      .optional(),
    city: z.string().max(100, "City must be 100 characters or less").optional(),
    state: z.string().max(64, "State must be 64 characters or less").optional(),
    zip: z.string().max(32, "Zip must be 32 characters or less").optional(),
    email: z.string().optional(),  // No email format validation - allow any string
    phoneCell: z
      .string()
      .max(64, "Cell phone must be 64 characters or less")
      .optional(),
    phone: z.string().max(64, "Phone must be 64 characters or less").optional(),

    // Workflow / assignment fields
    actionBy: z.string().optional(),
    action: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    actionDate: z.string().optional(),
    actionTime: z.string().optional(),
    salesNameID: z
      .string()
      .max(128, "salesNameID must be 128 characters or less")
      .optional(),
    orderedBy: z
      .string()
      .max(128, "orderedBy must be 128 characters or less")
      .optional(),
    contractDetailTag: z
      .string()
      .max(128, "contractDetailTag must be 128 characters or less")
      .optional(),
    terms: z
      .string()
      .max(128, "terms must be 128 characters or less")
      .optional(),
    typeSale: z
      .string()
      .max(128, "typeSale must be 128 characters or less")
      .optional(),
    taxJuris: z
      .string()
      .max(128, "taxJuris must be 128 characters or less")
      .optional(),
    adSource: z
      .string()
      .max(128, "adSource must be 128 characters or less")
      .optional(),

    // Commenting
    addComment: z
      .string()
      .max(2000, "Add comment must be 2000 characters or less")
      .optional(),
    comment: z
      .string()
      .max(4000, "Comment must be 4000 characters or less")
      .optional(),
    contractDetail: z
      .string()
      .max(4000, "Contract detail must be 4000 characters or less")
      .optional(),

    // Base transaction fields
    id_transaction: z.string().optional(),
    dt_created: z.union([z.string(), z.number()]).optional(),
    dt_updated: z.union([z.string(), z.number()]).optional(),
    customer_id: z.coerce.number().min(1, "Customer ID is required"),
    total: z.coerce.number().optional(),
    tax: z.coerce.number().optional(),
    discount: z.coerce.number().optional(),
    metadata: z
      .union([z.string(), z.record(z.any()), z.undefined()])
      .optional(),
    prefs: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    refs: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),

    // Order specific fields
    ida: z.string().optional(),
    order_no: z.string().optional(),
    status: z
      .enum(validStatuses, {
        errorMap: () => ({
          message: `Status must be one of: ${validStatuses.join(", ")}`,
        }),
      })
      .optional(),
    priority: z
      .string()
      .max(32, "Priority must be 32 characters or less")
      .nullable()
      .optional(),
    price_level: z
      .string()
      .max(50, "Price level must be 50 characters or less")
      .nullable()
      .optional(),

    // Customer/Vendor references
    manufacturer_id: z.coerce
      .number()
      .int()
      .min(0, "Manufacturer ID must be non-negative")
      .optional(),
    vendor_id: z.coerce
      .number()
      .int()
      .min(0, "Vendor ID must be non-negative")
      .optional(),

    // Financial summary fields
    subtotal: z.coerce.number().optional(),

    // JSON fields with structure validation - accept string, object, or undefined
    // Matches base_transaction_model.py JSON fields
    totals: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    cost: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    sell: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    finance: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    flow: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),
    source: z.union([z.string(), z.record(z.any()), z.undefined()]).optional(),

    // Line items
    lines: z.array(orderLineSchema).optional(),

    // Date fields
    dt_modified: z.union([z.string(), z.number()]).optional(),
    due_date: z.string().optional(),
    valid_until: z.string().optional(),
    version: z.coerce.number().optional(),
  })
  .refine(
    (data) => {
      // Cross-field validation: customer and vendor cannot be the same
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
export type OrderFormData = z.infer<typeof orderSchema>;
export type OrderLineFormData = z.infer<typeof orderLineSchema>;
