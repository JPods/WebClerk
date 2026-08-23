/**
 * Widget type definitions — shared contract for all widgets.
 *
 * Every widget receives the same props. The renderer doesn't need to
 * know which widget it's rendering. This is the contract that makes
 * DynamicDetail, DataBrowser, and print renderers interchangeable.
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
  /** Min value (number/date) */
  min?: number | string;
  /** Max value (number/date) */
  max?: number | string;
  /** Step (number) */
  step?: number;
  /** Number of rows (textarea) */
  rows?: number;
  /** Full record data — for widgets that need context */
  record?: Record<string, any>;
  /** Model name — for lookup widgets */
  model?: string;
  /** Display field — for lookup widgets */
  displayField?: string;
  /** CSS class override */
  className?: string;
  /** Render mode: screen (interactive) or print (static) */
  mode?: "screen" | "print";
}

/** Widget registration entry */
export interface WidgetRegistryEntry {
  component: React.ComponentType<WidgetProps>;
  /** Default print renderer — returns string for PDF/print output */
  printValue?: (value: any, props: WidgetProps) => string;
}
