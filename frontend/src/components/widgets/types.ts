/**
 * Widget type definitions — the one contract every field widget implements.
 *
 * A widget is the bare input (or its print/read text). The transaction form (FieldRow) draws
 * its own label beside it; the DataBrowser form wraps it in BaseField (components/fields),
 * which draws the label, help, error and admin override. One widget per type, two frames.
 */

export interface WidgetOption {
  value: string | number;
  label: string;
}

export interface WidgetProps {
  /** Field name from schema */
  name: string;
  /** Current value */
  value: any;
  /** Called when value changes */
  onChange: (value: any) => void;
  /** Disabled state (view mode) */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Select/radio options */
  options?: WidgetOption[];
  /** Select: a typed value beside the list */
  allowCustom?: boolean;
  /** Min value (number/date) */
  min?: number | string;
  /** Max value (number/date) */
  max?: number | string;
  /** Step (number) */
  step?: number;
  /** Number of rows (textarea, json) */
  rows?: number;
  /** Full record data — for widgets that need context */
  record?: Record<string, any>;
  /** Model name — for lookup widgets; the field's model for Shift-for-Help */
  model?: string;
  /** Lookup: the field of the found record the value stores — its id (default) or its ida (terms). */
  valueField?: 'id' | 'ida';
  /** Display field — for lookup widgets */
  displayField?: string;
  /** Geo: the paired latitude/longitude field */
  pair?: string;
  /** json-tree: no editing */
  readOnly?: boolean;
  /** CSS class for the input (the DataBrowser form passes db-input) */
  className?: string;
  /** Render mode: screen (interactive) or print (static) */
  mode?: "screen" | "print";
  /** Frame props read by BaseField, not the widget */
  label?: string;
  error?: string;
  span2?: boolean;
  behavior?: Record<string, unknown>;
}

/** Widget registration entry */
export interface WidgetRegistryEntry {
  component: React.ComponentType<WidgetProps>;
  /** Default print renderer — returns string for PDF/print output */
  printValue?: (value: any, props: WidgetProps) => string;
}
