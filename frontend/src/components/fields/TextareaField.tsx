import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function TextareaField(props: FieldWidgetProps & { rows?: number }) {
  const { value, onChange, disabled, rows } = props;
  return (
    <BaseField props={{ ...props, span2: true }}>
      <textarea className="db-input db-input--textarea" rows={rows || 4} value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} disabled={disabled} />
    </BaseField>
  );
}
