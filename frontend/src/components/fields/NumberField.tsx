import React from 'react';
import type { NumberFieldProps } from './types';
import BaseField from './BaseField';

export default function NumberField(props: NumberFieldProps) {
  const { value, onChange, disabled, step = 1, min, max } = props;
  return (
    <BaseField props={props}>
      <input className="db-input db-input--mono" type="number" step={step} min={min} max={max}
        value={value != null ? value : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} disabled={disabled} />
    </BaseField>
  );
}
