import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function TextField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  return (
    <BaseField props={props}>
      <input className="db-input" type="text" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
