import * as z from "zod";

/**
 * Converts empty-string / null / undefined → undefined for optional number inputs.
 * HTML <input type="number"> produces "" when cleared; this handles that gracefully.
 */
const optNum = z.preprocess(
  (v) => {
    if (v === "" || v === undefined || v === null) return undefined;
    const n = Number(v);
    return isNaN(n) ? undefined : n;
  },
  z.number().optional(),
);

/**
 * Full Item form schema.
 *
 * Covers every scalar DB column and every first-level key of each JSONB field.
 * Flat field names use an underscore prefix convention for JSONB sub-keys
 * (e.g. price_base → price.base, flag_discountable → flags.discountable).
 *
 * The submit handler in ItemDetail.tsx reconstructs the nested API payload.
 */
export const itemSchema = z.object({
  /* ── Scalar columns ─────────────────────────────────────────────── */
  name:             z.string().min(1, "Name is required"),
  sku:              z.string().optional().default(""),
  qr_code:          z.string().optional().default(""),
  kind:             z.string().optional().default("physical"),
  uom:              z.string().optional().default(""),
  base_uom:         z.string().optional().default(""),
  description:      z.string().optional().default(""),
  specification_id: optNum,
  is_active:        z.boolean().optional().default(true),

  /* ── price (JSONField) ──────────────────────────────────────────── */
  price_base:     optNum,
  price_msrp:     optNum,
  price_currency: z.string().optional().default("USD"),

  /* ── cost (JSONField) ───────────────────────────────────────────── */
  cost_standard: optNum,
  cost_last:     optNum,
  cost_avg:      optNum,
  cost_landed:   optNum,
  cost_currency: z.string().optional().default("USD"),

  /* ── quantity (JSONField) ───────────────────────────────────────── */
  qty_on_hand:    optNum,
  qty_allocated:  optNum,
  qty_available:  optNum,
  qty_on_so:      optNum,
  qty_on_po:      optNum,
  qty_on_p:       optNum,
  qty_on_reciept: optNum,
  qty_on_in:      optNum,
  qty_on_wo:      optNum,

  /* ── flags (JSONField) ──────────────────────────────────────────── */
  flag_back_order_allowed: z.boolean().optional().default(false),
  flag_discountable:       z.boolean().optional().default(false),
  flag_linked:             z.boolean().optional().default(false),
  flag_not_tracked:        z.boolean().optional().default(false),
  flag_pacing:             z.boolean().optional().default(false),
  flag_print_suppressed:   z.boolean().optional().default(false),
  flag_serialized:         z.boolean().optional().default(false),
  flag_tally_by_type:      z.boolean().optional().default(false),

  /* ── gls (JSONField) ────────────────────────────────────────────── */
  gls_inventory: z.string().optional().default(""),
  gls_cogs:      z.string().optional().default(""),
  gls_revenue:   z.string().optional().default(""),
  gls_variance:  z.string().optional().default(""),

  /* ── tax_code (JSONField) ───────────────────────────────────────── */
  tax_code_code:         z.string().optional().default(""),
  tax_code_jurisdiction: z.string().optional().default(""),
  tax_code_category:     z.string().optional().default(""),
  tax_code_rate:         optNum,

  /* ── catalog (JSONField) ────────────────────────────────────────── */
  catalog_categories:  z.string().optional().default(""),
  catalog_web_slug:    z.string().optional().default(""),
  catalog_web_title:   z.string().optional().default(""),
  catalog_web_short:   z.string().optional().default(""),
});

export type ItemFormValues = z.infer<typeof itemSchema>;