import React, { useState, useCallback } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { normalizePhone, formatPhone } from '@/utils/fieldFormatters';

export default function PhoneField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;

  // Display formatted, edit raw
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const normalized = String(value ?? '');
  const displayed = formatPhone(normalized, 'local', 'US');
  const href = normalized ? `tel:${normalized}` : undefined;

  const handleFocus = useCallback(() => {
    setEditing(true);
    setEditValue(displayed);
  }, [displayed]);

  const handleBlur = useCallback(() => {
    setEditing(false);
    const norm = normalizePhone(editValue);
    if (norm !== normalized) {
      onChange(norm);
    }
  }, [editValue, normalized, onChange]);

  return (
    <BaseField props={props} labelColor="actionable" labelHref={href}>
      <input className="db-input" type="tel"
        value={editing ? editValue : displayed}
        onChange={(e) => setEditValue(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder="405.555.1234"
      />
    </BaseField>
  );
}
