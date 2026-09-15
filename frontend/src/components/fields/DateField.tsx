import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { normalizeEpochMs, parseDatetimeInput } from '@/utils/fieldFormatters';

export default function DateField(props: FieldWidgetProps) {
  const { value, onChange, disabled, behavior } = props;
  const includeTime = behavior?.include_time === true;

  // Accept ISO string or epoch ms → local date or datetime-local string
  let inputValue = '';
  if (value) {
    if (typeof value === 'number') {
      const ms = normalizeEpochMs(value);
      const d = new Date(ms);
      inputValue = includeTime
        ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
        : d.toISOString().slice(0, 10);
    } else {
      inputValue = String(value).slice(0, includeTime ? 16 : 10);
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    if (includeTime) {
      // datetime-local → epoch ms (UTC)
      onChange(v ? parseDatetimeInput(v) : 0);
    } else {
      onChange(v);
    }
  };

  return (
    <BaseField props={props}>
      <input className="db-input" type={includeTime ? 'datetime-local' : 'date'}
        value={inputValue} onChange={handleChange} disabled={disabled} />
    </BaseField>
  );
}
