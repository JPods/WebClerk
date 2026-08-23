import React, { useState, useCallback } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { normalizeZip, formatZip } from '@/utils/fieldFormatters';

export default function ZipField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;

  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const normalized = String(value ?? '');
  const displayed = formatZip(normalized, 'US');

  const handleFocus = useCallback(() => {
    setEditing(true);
    setEditValue(displayed);
  }, [displayed]);

  const handleBlur = useCallback(() => {
    setEditing(false);
    const norm = normalizeZip(editValue, 'US');
    if (norm !== normalized) onChange(norm);
  }, [editValue, normalized, onChange]);

  return (
    <BaseField props={props}>
      <input className="db-input" type="text"
        value={editing ? editValue : displayed}
        onChange={(e) => setEditValue(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder="74135"
      />
    </BaseField>
  );
}
