/**
 * DtWidget — the one tool for every dt_ a person enters: a popup calendar and clock.
 *
 * Stored UTC, shown local (Bill, 2026-11-03: "we never store by date or time, always by dt").
 * In: epoch ms, epoch seconds, an ISO instant, a datetime-local string or a bare date.
 * Out: the UTC instant as ISO text, which an epoch column converts and a DateTimeField reads.
 * A day with no clock is 23:59:59.999 local that day (the standing date-only rule).
 * Shown (view, print): the local date and time.
 *
 * The field is a button that reads the local moment; it opens one popup (Bill, 2026-11-07:
 * "I would like a popup to select dates and times"): a month grid, an hour and a minute
 * list, Now / End of day / Clear. Every pick is written at once; Done only closes.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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

/** The six weeks a month grid shows, Sunday first; days outside the month are dimmed. */
export function monthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - first.getDay());
  return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DOW = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const HOURS = Array.from({ length: 24 }, (_, h) => pad(h));
const MINUTES = Array.from({ length: 12 }, (_, m) => pad(m * 5));

const popup: React.CSSProperties = {
  position: 'fixed', zIndex: 9999, width: 272, padding: 8,
  background: 'var(--db-surface, #fff)', color: 'var(--db-text, #111)',
  border: '1px solid var(--db-border, #d1d5db)', borderRadius: 6,
  boxShadow: '0 8px 24px rgba(0,0,0,0.18)', fontSize: 13, lineHeight: 1.2,
};
const btn: React.CSSProperties = {
  border: '1px solid transparent', background: 'transparent', color: 'inherit',
  borderRadius: 4, padding: '4px 0', cursor: 'pointer', font: 'inherit', width: '100%',
};
const small: React.CSSProperties = {
  ...btn, width: 'auto', padding: '3px 8px', border: '1px solid var(--db-border, #d1d5db)', whiteSpace: 'nowrap',
};

interface PickerProps { anchor: DOMRect; value: Date | null; onPick: (dt: string | null) => void; onClose: () => void; }

/** The popup: a month grid, an hour and a minute list, Now / End of day / Clear, Done. */
const DtPicker: React.FC<PickerProps> = ({ anchor, value, onPick, onClose }) => {
  const ref = useRef<HTMLDivElement>(null);
  const today = new Date();
  const shown = value ?? today;
  const [year, setYear] = useState(shown.getFullYear());
  const [month, setMonth] = useState(shown.getMonth());
  const [pos, setPos] = useState<{ left: number; top: number }>({ left: anchor.left, top: anchor.bottom + 4 });

  useLayoutEffect(() => {
    const h = ref.current?.offsetHeight ?? 320;
    const below = anchor.bottom + 4 + h <= window.innerHeight;
    setPos({
      left: Math.max(4, Math.min(anchor.left, window.innerWidth - 276)),
      top: below ? anchor.bottom + 4 : Math.max(4, anchor.top - 4 - h),
    });
  }, [anchor]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const click = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    document.addEventListener('keydown', key);
    document.addEventListener('mousedown', click);
    return () => { document.removeEventListener('keydown', key); document.removeEventListener('mousedown', click); };
  }, [onClose]);

  const day = localDay(value);
  const clock = localClock(value);
  const pickDay = (d: Date) => {
    setYear(d.getFullYear()); setMonth(d.getMonth());
    onPick(localToDt(localDay(d), clock));
  };
  const pickClock = (hh: string, mm: string) => onPick(localToDt(day || localDay(today), `${hh}:${mm}`));
  const now = () => { const n = new Date(); setYear(n.getFullYear()); setMonth(n.getMonth()); onPick(localToDt(localDay(n), localClock(n))); };
  const endOfDay = () => onPick(localToDt(day || localDay(today), ''));
  const step = (n: number) => { const d = new Date(year, month + n, 1); setYear(d.getFullYear()); setMonth(d.getMonth()); };
  const [hh, mm] = clock ? clock.split(':') : ['', ''];
  const minutes = mm && !MINUTES.includes(mm) ? [...MINUTES, mm].sort() : MINUTES;
  const isSame = (a: Date, b: Date | null) => !!b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

  return createPortal(
    <div ref={ref} style={{ ...popup, left: pos.left, top: pos.top }} role="dialog" aria-label="Pick a date and time" data-wc-dt-picker>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <button type="button" style={{ ...btn, width: 28 }} onClick={() => step(-12)} title="Previous year">«</button>
        <button type="button" style={{ ...btn, width: 28 }} onClick={() => step(-1)} title="Previous month">‹</button>
        <span style={{ fontWeight: 600 }}>{MONTHS[month]} {year}</span>
        <button type="button" style={{ ...btn, width: 28 }} onClick={() => step(1)} title="Next month">›</button>
        <button type="button" style={{ ...btn, width: 28 }} onClick={() => step(12)} title="Next year">»</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 1, textAlign: 'center' }}>
        {DOW.map(d => <span key={d} style={{ color: 'var(--db-text-dim, #6b7280)', fontSize: 11, padding: '2px 0' }}>{d}</span>)}
        {monthGrid(year, month).map(d => {
          const inMonth = d.getMonth() === month;
          const picked = isSame(d, value);
          return (
            <button key={d.getTime()} type="button" onClick={() => pickDay(d)} aria-pressed={picked}
              style={{
                ...btn,
                color: picked ? '#fff' : inMonth ? 'inherit' : 'var(--db-text-dim, #9ca3af)',
                background: picked ? 'var(--db-accent, #2563eb)' : 'transparent',
                borderColor: !picked && isSame(d, today) ? 'var(--db-accent, #2563eb)' : 'transparent',
              }}>
              {d.getDate()}
            </button>
          );
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
        <span style={{ color: 'var(--db-text-dim, #6b7280)' }}>Time</span>
        <select value={hh} onChange={e => pickClock(e.target.value, mm || '00')} className={s} aria-label="Hour" style={{ fontSize: 'inherit' }}>
          <option value="" disabled>hh</option>
          {HOURS.map(h => <option key={h} value={h}>{h}</option>)}
        </select>
        <span>:</span>
        <select value={mm} onChange={e => pickClock(hh || '00', e.target.value)} className={s} aria-label="Minute" style={{ fontSize: 'inherit' }}>
          <option value="" disabled>mm</option>
          {minutes.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <span style={{ flex: 1 }} />
        <button type="button" style={small} onClick={now}>Now</button>
        <button type="button" style={small} onClick={endOfDay} title="23:59 local">End of day</button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
        <button type="button" style={small} onClick={() => onPick(null)}>Clear</button>
        <button type="button" style={{ ...small, background: 'var(--db-accent, #2563eb)', color: '#fff', borderColor: 'transparent' }} onClick={onClose}>Done</button>
      </div>
    </div>,
    document.body,
  );
};

export const DtWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, className, mode,
}) => {
  const local = dtToLocal(value);
  const anchorRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState<DOMRect | null>(null);
  const close = useCallback(() => setOpen(null), []);

  if (mode === 'print' || disabled) {
    const text = local ? formatDt(local.getTime(), 'datetime') : '—';
    const cls = className ? `${className} ${mode === 'print' ? '' : 'db-input--readonly'}` : 'text-[inherit]';
    return <span className={cls} style={{ display: 'inline-block' }} title={local ? local.toISOString() : undefined}>{text}</span>;
  }
  const cls = className || s;
  return (
    <>
      <button ref={anchorRef} type="button" name={name} className={cls} data-wc-dt={name}
        style={{ width: '100%', textAlign: 'left', cursor: 'pointer', color: local ? undefined : 'var(--db-text-dim, #6b7280)' }}
        title={local ? `${local.toISOString()} — click to change` : 'Click to pick a date and time'}
        onClick={e => setOpen(e.currentTarget.getBoundingClientRect())}>
        {local ? formatDt(local.getTime(), 'datetime') : 'Pick a date…'}
      </button>
      {open && <DtPicker anchor={open} value={local} onPick={onChange} onClose={close} />}
    </>
  );
};

/** A system stamp: shown local, never typed. */
export const DtStamp: React.FC<WidgetProps> = (props) => <DtWidget {...props} disabled />;
