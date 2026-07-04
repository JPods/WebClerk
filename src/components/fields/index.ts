/**
 * Field widgets — reusable, self-contained, pointable at any field or task.
 *
 * Usage:
 *   Direct:   <CurrencyField name="total" value={invoice.total} onChange={setTotal} />
 *   Dynamic:  const Widget = getWidget('currency'); <Widget name="total" ... />
 *
 * The Setting record for each model (field_behaviors) contains the instructions
 * for which widget to use per field. Alice links these Settings so the object
 * for each field carries its own display/widget instructions.
 */

// Individual widgets — import directly for custom pages
export { default as TextField } from './TextField';
export { default as NumberField } from './NumberField';
export { default as CurrencyField } from './CurrencyField';
export { default as EmailField } from './EmailField';
export { default as PhoneField } from './PhoneField';
export { default as UrlField } from './UrlField';
export { default as AddressField } from './AddressField';
export { default as SelectField } from './SelectField';
export { default as LookupField } from './LookupField';
export { default as BooleanField } from './BooleanField';
export { default as DateField } from './DateField';
export { default as TimestampField } from './TimestampField';
export { default as JsonField } from './JsonField';
export { default as TextareaField } from './TextareaField';
export { default as ReadonlyField } from './ReadonlyField';
export { default as GeoField } from './GeoField';
export { default as BaseField } from './BaseField';

// Types
export type { FieldWidgetProps, SelectFieldProps, LookupFieldProps, NumberFieldProps, GeoFieldProps } from './types';

// ---------------------------------------------------------------------------
// Registry — maps type name to component for dynamic rendering
// ---------------------------------------------------------------------------

import TextField from './TextField';
import NumberField from './NumberField';
import CurrencyField from './CurrencyField';
import EmailField from './EmailField';
import PhoneField from './PhoneField';
import UrlField from './UrlField';
import AddressField from './AddressField';
import SelectField from './SelectField';
import LookupField from './LookupField';
import BooleanField from './BooleanField';
import DateField from './DateField';
import TimestampField from './TimestampField';
import JsonField from './JsonField';
import TextareaField from './TextareaField';
import ReadonlyField from './ReadonlyField';
import GeoField from './GeoField';

const WIDGET_REGISTRY: Record<string, React.ComponentType<any>> = {
  text: TextField,
  number: NumberField,
  currency: CurrencyField,
  email: EmailField,
  phone: PhoneField,
  url: UrlField,
  address: AddressField,
  select: SelectField,
  lookup: LookupField,
  boolean: BooleanField,
  date: DateField,
  timestamp: TimestampField,
  json: JsonField,
  textarea: TextareaField,
  readonly: ReadonlyField,
  geo: GeoField,
  masked: ReadonlyField,  // masked fields display as readonly
};

/**
 * Get the widget component for a given type name.
 * Returns TextField as fallback for unknown types.
 */
export function getWidget(typeName: string): React.ComponentType<any> {
  return WIDGET_REGISTRY[typeName] || TextField;
}

/**
 * Render a field dynamically from a behavior config object.
 * This is what DataBrowser calls — the Setting record for each model
 * provides the behavior object per field, which drives widget selection.
 *
 * @param name - field name
 * @param value - current value
 * @param behavior - from Setting.config.field_behaviors[name]
 * @param onChange - value change handler
 * @param opts - additional props (error, disabled, typeHint, record, etc.)
 */
export function renderField(
  name: string,
  value: unknown,
  behavior: Record<string, any>,
  onChange: (value: unknown) => void,
  opts?: { error?: string; disabled?: boolean; typeHint?: string; record?: Record<string, unknown>; span2?: boolean },
) {
  const typeName = opts?.typeHint || behavior.type || 'text';
  const Widget = getWidget(typeName);

  // Build props from behavior config
  const props: any = {
    name,
    value,
    onChange,
    error: opts?.error,
    disabled: opts?.disabled,
    span2: opts?.span2,
  };

  // Type-specific props from behavior
  if (typeName === 'select' && behavior.options) props.options = behavior.options;
  if (typeName === 'lookup') { props.model = behavior.model || ''; props.displayField = behavior.display; }
  if (typeName === 'geo') { props.pair = behavior.pair; props.record = opts?.record; }

  return <Widget key={name} {...props} />;
}
