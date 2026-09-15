import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function TextField(props: FieldWidgetProps & { labelHref?: string }) {
  const { value, onChange, disabled, labelHref } = props;
  return (
    <BaseField props={props} labelHref={labelHref}>
      <input className="db-input" type="text" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
