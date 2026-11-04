import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { normalizeEpochMs, parseDatetimeInput } from '@/utils/fieldFormatters';

export default function DateField(props: FieldWidgetProps) {
  const { value, onChange, disabled, behavior } = props;
  const includeTime = behavior?.include_time === true;

  // Accept ISO string or epoch ms → the LOCAL date or datetime-local string. Stored UTC, shown
  // local (Bill, 2026-11-03); slicing an ISO string gave the UTC day (1041-cash: 10/25 for 10/24).
  const pad = (n: number) => String(n).padStart(2, '0');
  const local = (d: Date) => includeTime
    ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
    : `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  let inputValue = '';
  if (value) {
    if (typeof value === 'number') {
      inputValue = local(new Date(normalizeEpochMs(value)));
    } else {
      const s = String(value);
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) inputValue = s;            // a bare date has no zone
      else { const d = new Date(s); inputValue = isNaN(d.getTime()) ? s.slice(0, includeTime ? 16 : 10) : local(d); }
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
