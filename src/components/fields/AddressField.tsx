import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function AddressField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  const v = String(value ?? '');
  const href = v ? `https://maps.google.com/?q=${encodeURIComponent(v)}` : undefined;
  return (
    <BaseField props={props} labelColor="actionable" labelHref={href}>
      <input className="db-input" value={v}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
