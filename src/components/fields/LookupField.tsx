import React from 'react';
import type { LookupFieldProps } from './types';
import BaseField from './BaseField';

export default function LookupField(props: LookupFieldProps) {
  const { value, onChange, disabled, model, displayField } = props;
  return (
    <BaseField props={props} labelColor="lookup"
      labelSuffix={<span className="db-label-hint">{`→ ${model}`}</span>}>
      <input className="db-input" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled}
        placeholder={`${model} ID`} />
    </BaseField>
  );
}
