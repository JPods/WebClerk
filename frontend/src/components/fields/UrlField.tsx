import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function UrlField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  const v = String(value ?? '');
  const href = v.startsWith('http') ? v : v ? `https://${v}` : undefined;
  return (
    <BaseField props={props} labelColor="actionable" labelHref={href}>
      <input className="db-input" type="url" value={v}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
