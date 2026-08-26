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

import './fields.css';

// Individual widgets — import directly for custom pages
export { default as TextField } from './TextField';
export { default as NumberField } from './NumberField';
export { default as CurrencyField } from './CurrencyField';
export { default as EmailField } from './EmailField';
export { default as PhoneField } from './PhoneField';
export { default as UrlField } from './UrlField';
export { default as AddressField } from './AddressField';
export { default as ZipField } from './ZipField';
export { default as SelectField } from './SelectField';
export { default as LookupField } from './LookupField';
export { default as BooleanField } from './BooleanField';
export { default as DateField } from './DateField';
export { default as TimestampField } from './TimestampField';
export { default as JsonField, JsonTreeField } from './JsonField';
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
import JsonField, { JsonTreeField } from './JsonField';
import TextareaField from './TextareaField';
import ReadonlyField from './ReadonlyField';
import GeoField from './GeoField';
import ZipField from './ZipField';

// Hidden type renders nothing
function HiddenField() { return null; }

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
  'json-tree': JsonTreeField,
  textarea: TextareaField,
  readonly: ReadonlyField,
  geo: GeoField,
  zip: ZipField,
  masked: ReadonlyField,  // masked fields display as readonly
  hidden: HiddenField,
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
 * @param opts - additional props (error, disabled, record, etc.)
 */
export function renderField(
  name: string,
  value: unknown,
  behavior: Record<string, any>,
  onChange: (value: unknown) => void,
  opts?: {
    error?: string; disabled?: boolean;
    record?: Record<string, unknown>; span2?: boolean; model?: string;
    rowSize?: number; leaf?: { type: string; extract?: string };
  },
) {
  const isJson = typeof value === 'object' && value !== null;

  // i18n extraction — declared by leaf or detected from value
  const isI18n = behavior.type === 'i18n'
    || opts?.leaf?.type === 'i18n'
    || (isJson && !Array.isArray(value)
        && Object.keys(value as object).length > 0
        && Object.values(value as object).every(v => typeof v === 'string' || v === null)
        && (behavior.type === 'json' || !behavior.type));
  const objKey = isI18n && isJson ? Object.keys(value as object)[0] : null;
  const objValue = objKey ? (value as Record<string, string>)[objKey] || '' : null;
  const effectiveValue = isI18n && objKey ? objValue : value;
  const isLong = typeof effectiveValue === 'string' && (effectiveValue as string).length > 100;

  // Determine widget type — schema behavior.type is authoritative
  const typeName = (isI18n ? '' : behavior.type)
    || (typeof effectiveValue === 'boolean' ? 'boolean' : '')
    || (isJson && !isI18n ? 'json' : '')
    || (isLong ? 'textarea' : '')
    || ((typeof effectiveValue === 'number' && !name.startsWith('dt_')) ? 'number' : '')
    || 'text';
  const Widget = getWidget(typeName);

  // For i18n objects, wrap onChange to preserve the key
  const effectiveOnChange = isI18n && objKey
    ? (v: unknown) => onChange({ ...(value as object), [objKey]: v })
    : onChange;

  // Build props from behavior config
  const props: any = {
    name: isI18n && objKey ? `${name}.${objKey}` : name,
    value: effectiveValue,
    onChange: effectiveOnChange,
    error: opts?.error,
    disabled: opts?.disabled,
    span2: opts?.span2,
    model: opts?.model,
  };

  // Type-specific props from behavior
  if (typeName === 'select' && behavior.options) {
    props.options = behavior.options;
    if (behavior.allow_custom) props.allowCustom = true;
  }
  if (typeName === 'lookup') { props.model = behavior.model || ''; props.displayField = behavior.display; }
  if (typeName === 'geo') { props.pair = behavior.pair; props.record = opts?.record; }
  if (typeName === 'json' || typeName === 'json-tree') { props.rows = opts?.rowSize; }
  if (typeName === 'json-tree') { props.readOnly = behavior.readOnly; }

  return <Widget key={name} {...props} />;
}
