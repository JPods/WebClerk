import { useState } from "react";
import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60 text-right";

/** Money entered or applied shows .00 (Bill, 2026-11-03): to the cent until focused, what was
 *  typed while typing, money again on blur. */
export const CurrencyWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, className, mode,
}) => {
  const [draft, setDraft] = useState<string | null>(null);
  const fmt = (v: any) => {
    const n = typeof v === "number" ? v : parseFloat(v);
    if (isNaN(n)) return "—";
    return n.toLocaleString(undefined, { style: "currency", currency: "USD", minimumFractionDigits: 2 });
  };

  if (mode === "print") return <span className="text-[inherit]">{fmt(value)}</span>;
  const n = typeof value === "number" ? value : parseFloat(value);
  const shown = draft ?? (isNaN(n) ? "" : n.toFixed(2));
  return (
    <input
      type="number"
      name={name}
      value={shown}
      onFocus={() => setDraft(value == null || value === "" ? "" : String(value))}
      onChange={e => { setDraft(e.target.value); onChange(Number(e.target.value)); }}
      onBlur={() => setDraft(null)}
      disabled={disabled}
      step={0.01}
      min={0}
      className={className || s}
    />
  );
};
