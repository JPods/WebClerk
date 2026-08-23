/**
 * printLayoutTypes.ts — JSON schema for print_layout Setting records.
 *
 * Alice composes these section types to draft print layouts from user-uploaded
 * PDF/image examples. Users tweak field mappings in the DataBrowser.
 *
 * Stored in Setting.config with purpose='print_layout', parent_model='order'.
 */

// ---------------------------------------------------------------------------
// Field reference — dot-notation path into the record
// ---------------------------------------------------------------------------

export interface PrintField {
  field: string;        // dot-notation: "config.ship_to.company", "totals.subtotal"
  label?: string;       // display label; defaults to field name if omitted
  format?: 'text' | 'currency' | 'date' | 'number' | 'percent';
  align?: 'left' | 'right' | 'center';
  width?: string;       // CSS width: "40%", "120px"
  style?: string;       // "bold" | "italic" | "bold italic"
}

// ---------------------------------------------------------------------------
// Section types — closed set that Alice knows how to compose
// ---------------------------------------------------------------------------

export interface CompanyHeaderSection {
  type: 'company_header';
  logo?: boolean;
  show_address?: boolean;
  show_contact?: boolean;
}

export interface AddressBlocksSection {
  type: 'address_blocks';
  columns: {
    title: string;
    fields: PrintField[];
  }[];
}

export interface MetaRowSection {
  type: 'meta_row';
  fields: PrintField[];
}

export interface CommentsSection {
  type: 'comments';
  source: string;       // dot-notation field: "comments.public"
  label?: string;
}

export interface LineItemsSection {
  type: 'line_items';
  columns: PrintField[];
  show_footer_totals?: boolean;
  /** SVG row height in points — used to clone and offset line panel <g> groups */
  row_height?: number;
  /** SVG group ID for the line panel template row (cloned per line item) */
  svg_panel_id?: string;
}

export interface TotalsSection {
  type: 'totals';
  rows: (PrintField & { bold?: boolean })[];
  left_text?: string;   // "Thank you for your order."
}

export interface ConditionsSection {
  type: 'conditions';
  source: string;       // "conditions_description"
}

export interface SignatureSection {
  type: 'signature';
  preamble?: string;
  blocks: {
    label: string;
    lines: string[];    // ["Signature", "Date"]
  }[];
}

/** Body detail — non-repeating fields (attention, company, address, phone) */
export interface DetailFieldsSection {
  type: 'detail_fields';
  fields: PrintField[];
}

export interface FooterSection {
  type: 'footer';
  fields: PrintField[];
}

/** List report — renders passed-in rows (from db.list) as a grouped table */
export interface DataTableSection {
  type: 'data_table';
  /** Column definitions — same PrintField format as line_items */
  columns: PrintField[];
  /** Field to group rows by (e.g. 'customer_id', 'status') — optional */
  group_by?: string;
  /** Label for group headers (e.g. 'Customer', 'Status') */
  group_label?: string;
  /** Show subtotals per group for currency/number columns */
  group_subtotals?: boolean;
  /** Show grand totals at bottom */
  grand_totals?: boolean;
}

/** Conditional text — first matching rule wins (top-down).
 *  Rules reference config paths; renderer resolves against record data.
 *  Example: statement dunning messages based on aging buckets. */
export interface ConditionalTextSection {
  type: 'conditional_text';
  /** Dot-path into report config where rules are stored (e.g. "statement.comments") */
  source: string;
}

export interface ConditionalTextRule {
  when?: string;      // expression: "aging.past_61 > 0"
  default?: boolean;  // true = fallback if no other rule matches
  text: string;
  style?: string;     // "bold" | "italic"
}

export type PrintLayoutSection =
  | CompanyHeaderSection
  | AddressBlocksSection
  | MetaRowSection
  | DetailFieldsSection
  | CommentsSection
  | LineItemsSection
  | TotalsSection
  | ConditionsSection
  | SignatureSection
  | FooterSection
  | DataTableSection
  | ConditionalTextSection;

// ---------------------------------------------------------------------------
// Top-level layout
// ---------------------------------------------------------------------------

export interface PrintLayout {
  model: string;
  family?: 'sell' | 'exec';
  paper?: 'letter' | 'legal' | 'a4';
  title?: string;        // "Order", "Invoice", "Purchase Order"
  version?: number;
  sections: PrintLayoutSection[];
  /** Repeat company header on every printed page */
  repeat_header?: boolean;
  /** Repeat footer on every printed page */
  repeat_footer?: boolean;
  /** Page break between groups (data_table group_by) */
  page_break_between_groups?: boolean;

  // --- Line panel pagination (runtime config — user can change these) ---
  /** Number of line item rows on page 1 (header takes space) */
  lines_page_1?: number;
  /** Number of line item rows on following pages */
  lines_following?: number;
  /** Max description lines before truncation with ellipsis (default 2).
   *  Each wrapped line consumes a slot from the line count budget.
   *  Set to 1 for strict truncate behavior. */
  max_description_lines?: number;

  // --- Standard footer/header offerings (user toggles these) ---
  /** Show "Page X of Y" in footer bottom-right */
  show_page_numbers?: boolean;
  /** Show domain name in footer bottom-center */
  show_domain?: boolean;

  // --- Text rendering ---
  /** Format for rich text fields (comments, conditions, terms).
   *  'markdown' = stored as markdown, rendered to HTML at print time.
   *  'plain' = no formatting (default for backward compatibility).
   *  Rendered HTML injected into SVG via <foreignObject>. */
  text_format?: 'markdown' | 'plain';

  // --- SVG template ---
  /** SVG template string — designed externally, IDs map to field paths */
  svg_template?: string;
  /** SVG template for following pages (if different from page 1) */
  svg_template_following?: string;
}
