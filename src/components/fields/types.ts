/**
 * Shared props contract for all field widgets.
 * Any widget can be pointed at any appropriate field or task.
 */

export interface FieldWidgetProps {
  name: string;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  disabled?: boolean;
  label?: string;          // override display label (defaults to name)
  className?: string;      // outer wrapper class for layout control
  span2?: boolean;         // span full width in grid layouts
}

/** Extended props for select-type widgets */
export interface SelectFieldProps extends FieldWidgetProps {
  options: { value: string; label: string }[];
}

/** Extended props for lookup (FK) widgets */
export interface LookupFieldProps extends FieldWidgetProps {
  model: string;           // related model name for display/search
  displayField?: string;   // field to show (default: display_name)
}

/** Extended props for number-type widgets */
export interface NumberFieldProps extends FieldWidgetProps {
  step?: number;
  min?: number;
  max?: number;
}

/** Extended props for geo widgets */
export interface GeoFieldProps extends FieldWidgetProps {
  pair?: string;           // name of the paired lat/lng field
  record?: Record<string, unknown>;
}
