import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function DateField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  // Accept ISO string or epoch ms
  const dateStr = value
    ? (typeof value === 'number' ? new Date(value).toISOString().slice(0, 10) : String(value).slice(0, 10))
    : '';
  return (
    <BaseField props={props}>
      <input className="db-input" type="date" value={dateStr}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
