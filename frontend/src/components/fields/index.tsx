/**
 * Fields — the DataBrowser form's labeled frame around the one widget registry.
 *
 * BaseField draws the label (color by type, Shift-for-Help, Cmd+click action, Cmd+Shift+click
 * behavior override), the error and the grid span; the widget inside comes from
 * components/widgets — the same component the transaction form draws beside its own label.
 * One widget per type (Bill, 2026-11-03); this file holds only the frame and the dispatch.
 */

import './fields.css';
import BaseField from './BaseField';
import { WIDGETS, TextWidget, urlHref, addressHref, geoHref, type WidgetProps } from '@/components/widgets';

export { default as BaseField } from './BaseField';

/** Label color by behavior type (fields.css .db-label--*). */
const LABEL_COLOR: Record<string, string> = {
  select: 'select', lookup: 'lookup',
  readonly: 'readonly', timestamp: 'readonly', masked: 'readonly',
  email: 'actionable', phone: 'actionable', url: 'actionable', address: 'actionable', geo: 'actionable',
};

/** The input class the DataBrowser form gives each widget. */
const INPUT_CLASS: Record<string, string> = {
  currency: 'db-input db-input--mono db-input--right',
  number: 'db-input db-input--mono',
  geo: 'db-input db-input--mono',
  select: 'db-input db-input--select',
  textarea: 'db-input db-input--textarea',
  json: 'db-input db-input--mono db-input--textarea',
  readonly: 'db-input db-input--readonly',
  masked: 'db-input db-input--readonly',
};

const SPAN2 = new Set(['textarea', 'json', 'json-tree']);

/** What a click on the label opens, by type. */
function labelHrefFor(type: string, props: WidgetProps): string | undefined {
  const v = props.value;
  switch (type) {
    case 'email': return v ? `mailto:${v}` : undefined;
    case 'phone': return v ? `tel:${v}` : undefined;
    case 'url': return urlHref(v);
    case 'address': return addressHref(v);
    case 'geo': return geoHref(props.name, v, props.pair, props.record);
    default: return undefined;
  }
}

/** The widget component for a behavior type; text when unknown. */
export function getWidget(typeName: string): React.ComponentType<WidgetProps> {
  return WIDGETS[typeName] || TextWidget;
}

export interface FieldProps extends WidgetProps {
  type: string;
  labelHref?: string;
}

/** A labeled field: BaseField around the registry's widget. */
export function Field({ type, labelHref, ...props }: FieldProps) {
  if (type === 'hidden') return null;
  const Widget = getWidget(type);
  const href = labelHref || labelHrefFor(type, props);
  const suffix = type === 'lookup' && props.model
    ? <span className="db-label-hint">{`→ ${props.model}`}</span> : undefined;
  // The lookup's model is the related model; the frame's model (Shift-for-Help) is the record's.
  const frameProps = { ...props, span2: props.span2 ?? SPAN2.has(type) };
  return (
    <BaseField props={frameProps} labelColor={LABEL_COLOR[type] || 'default'} labelHref={href} labelSuffix={suffix}
      model={type === 'lookup' ? (props.record as any)?._model : undefined}>
      <Widget {...props} className={INPUT_CLASS[type] || 'db-input'} />
    </BaseField>
  );
}

/**
 * Render a field from a behavior config object. The Setting record for each model provides
 * the behavior per field, which drives widget selection.
 *
 * @param name - field name
 * @param value - current value
 * @param behavior - from Setting.config.behaviors[name] (selectlists folded in)
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

  // Determine widget type — schema behavior.type is authoritative (PJPV)
  const declaredType = isI18n ? '' : behavior.type;
  const autoType = declaredType
    || (typeof effectiveValue === 'boolean' ? 'boolean' : '')
    || (isJson && !isI18n ? 'json' : '')
    || (isLong ? 'textarea' : '')
    || (name.startsWith('dt_') ? 'timestamp' : '')   // undeclared dt_: shown, not typed — declare it in field_behaviors
    || (typeof effectiveValue === 'number' ? 'number' : '');
  const typeName = autoType || 'text';

  // PJPV: log undeclared fields in development — they need schema declarations
  if (!declaredType && typeName === 'text' && effectiveValue != null && effectiveValue !== ''
    && process.env.NODE_ENV === 'development') {
    console.warn(`[PJPV] Undeclared field behavior: ${name} — rendering as text. Add to Pydantic schema.`);
  }

  // For i18n objects, wrap onChange to preserve the key
  const effectiveOnChange = isI18n && objKey
    ? (v: unknown) => onChange({ ...(value as object), [objKey]: v })
    : onChange;

  const props: FieldProps = {
    type: typeName,
    name: isI18n && objKey ? `${name}.${objKey}` : name,
    value: effectiveValue,
    onChange: effectiveOnChange,
    error: opts?.error,
    disabled: opts?.disabled,
    span2: opts?.span2,
    model: opts?.model,
    record: opts?.record,
    behavior,
  };

  // Type-specific props from behavior
  if (typeName === 'select') { props.options = behavior.options || []; if (behavior.allow_custom) props.allowCustom = true; }
  if (typeName === 'lookup') { props.model = behavior.model || ''; props.displayField = behavior.display; }
  if (typeName === 'geo') { props.pair = behavior.pair; }
  if (typeName === 'json' || typeName === 'json-tree') { props.rows = opts?.rowSize; }
  if (typeName === 'json-tree') { props.readOnly = behavior.readOnly; }

  // label_href behavior: resolve a dot-path from the record to make the label a link
  if (behavior.label_href && opts?.record) {
    const href = behavior.label_href.split('.').reduce((o: any, k: string) => o?.[k], opts.record);
    if (typeof href === 'string' && href) props.labelHref = href;
  }

  return <Field key={name} {...props} />;
}
