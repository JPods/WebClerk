import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function EmailField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  const href = value ? `mailto:${value}` : undefined;
  return (
    <BaseField props={props} labelColor="actionable" labelHref={href}>
      <input className="db-input" type="email" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
