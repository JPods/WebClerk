import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function BooleanField(props: FieldWidgetProps) {
  const { name, value, onChange, disabled, label } = props;
  return (
    <div className={`db-field ${props.className || ''}`} data-wc={`field-${name}`} data-wc-field={name}>
      <label className="db-boolean-label">
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} disabled={disabled} />
        <span>{label || name}</span>
      </label>
      {props.error && <div className="db-field-error">{props.error}</div>}
    </div>
  );
}
