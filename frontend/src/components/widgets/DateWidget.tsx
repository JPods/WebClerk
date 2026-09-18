import type { WidgetProps } from "./types";
import { formatDt, formatDtInput } from '@/utils/fieldFormatters';

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

/** Convert epoch ms, epoch seconds, or ISO string to YYYY-MM-DD for <input type="date"> */
function toDateInputValue(val: unknown): string {
  if (!val) return '';
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
  // Epoch ms or seconds
  if (typeof val === 'number' || (typeof val === 'string' && /^\d{10,}$/.test(val))) {
    const n = typeof val === 'number' ? val : parseInt(val, 10);
    const d = new Date(n > 1e12 ? n : n * 1000);
    if (!isNaN(d.getTime())) return formatDtInput(n);
  }
  // ISO string
  if (typeof val === 'string') {
    const d = new Date(val);
    if (!isNaN(d.getTime())) return d.toISOString().slice(0, 10);
  }
  return '';
}

export const DateWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, min, max, className, mode,
}) => {
  if (mode === "print") {
    if (!value) return <span className="text-[inherit]">—</span>;
    try {
      return <span className="text-[inherit]">{formatDt(value, 'date')}</span>;
    } catch {
      return <span className="text-[inherit]">{value}</span>;
    }
  }
  return (
    <input
      type="date"
      name={name}
      value={toDateInputValue(value)}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      min={min as string}
      max={max as string}
      className={className || s}
    />
  );
};
