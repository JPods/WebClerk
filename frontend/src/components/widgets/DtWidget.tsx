/**
 * DtWidget — the one tool for every dt_ a person enters: a local day and a local clock.
 *
 * Stored UTC, shown local (Bill, 2026-11-03: "we never store by date or time, always by dt").
 * In: epoch ms, epoch seconds, an ISO instant, a datetime-local string or a bare date.
 * Out: the UTC instant as ISO text, which an epoch column converts and a DateTimeField reads.
 * A day with no clock is 23:59:59.999 local that day (the standing date-only rule).
 * Shown (view, print): the local date and time.
 */
import { useEffect, useState } from 'react';
import type { WidgetProps } from './types';
import { formatDt, normalizeEpochMs } from '@/utils/fieldFormatters';

const s = "px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";
const pad = (n: number) => String(n).padStart(2, '0');

/** Any stored dt as a local Date; null when there is none. */
export function dtToLocal(value: unknown): Date | null {
  if (value == null || value === '' || value === 0) return null;
  if (typeof value === 'number') {
    const d = new Date(normalizeEpochMs(value));
    return isNaN(d.getTime()) ? null : d;
  }
  if (typeof value !== 'string') return null;
  const t = value.trim();
  if (/^-?\d{10,}$/.test(t)) return new Date(normalizeEpochMs(parseInt(t, 10)));
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return new Date(`${t}T23:59:59.999`);   // a bare day ends at 23:59 local
  const d = new Date(t);
  return isNaN(d.getTime()) ? null : d;
}

/** A local day (YYYY-MM-DD) and clock (HH:MM) as the UTC instant to store; null with no day. */
export function localToDt(day: string, clock: string): string | null {
  if (!day) return null;
  const d = new Date(`${day}T${clock || '23:59:59.999'}`);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

export function localDay(d: Date | null): string {
  return d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : '';
}

export function localClock(d: Date | null): string {
  return d ? `${pad(d.getHours())}:${pad(d.getMinutes())}` : '';
}

export const DtWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, className, mode,
}) => {
  const local = dtToLocal(value);
  const [day, setDay] = useState(localDay(local));
  const [clock, setClock] = useState(localClock(local));
  useEffect(() => { const d = dtToLocal(value); setDay(localDay(d)); setClock(localClock(d)); }, [value]);

  if (mode === 'print' || disabled) {
    const text = local ? formatDt(local.getTime(), 'datetime') : '—';
    const cls = className ? `${className} ${mode === 'print' ? '' : 'db-input--readonly'}` : 'text-[inherit]';
    return <span className={cls} style={{ display: 'inline-block' }} title={local ? local.toISOString() : undefined}>{text}</span>;
  }
  const cls = className || s;
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', width: '100%' }} data-wc-dt={name}>
      <input type="date" name={name} value={day} className={cls} style={{ flex: '1 1 auto', minWidth: 0 }}
        onChange={e => { setDay(e.target.value); onChange(localToDt(e.target.value, clock)); }} />
      <input type="time" name={`${name}__clock`} value={clock} className={cls} style={{ flex: '0 0 auto', width: '7.5em' }}
        disabled={!day} title={day ? 'Local time; blank is 23:59' : 'Pick the day first'}
        onChange={e => { setClock(e.target.value); onChange(localToDt(day, e.target.value)); }} />
    </span>
  );
};

/** A system stamp: shown local, never typed. */
export const DtStamp: React.FC<WidgetProps> = (props) => <DtWidget {...props} disabled />;
