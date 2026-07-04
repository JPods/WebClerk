import React from 'react';
import type { SelectFieldProps } from './types';
import BaseField from './BaseField';

export default function SelectField(props: SelectFieldProps) {
  const { value, onChange, disabled, options } = props;
  return (
    <BaseField props={props} labelColor="select">
      <select className="db-input db-input--select" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        <option value="">--</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </BaseField>
  );
}
