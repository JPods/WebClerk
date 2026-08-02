import React, { useCallback } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { normalizeEmail } from '@/utils/fieldFormatters';

export default function EmailField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  const href = value ? `mailto:${value}` : undefined;

  const handleBlur = useCallback(() => {
    const norm = normalizeEmail(String(value ?? ''));
    if (norm !== value) onChange(norm);
  }, [value, onChange]);

  return (
    <BaseField props={props} labelColor="actionable" labelHref={href}>
      <input className="db-input" type="email" value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
        onBlur={handleBlur}
        disabled={disabled} />
    </BaseField>
  );
}
