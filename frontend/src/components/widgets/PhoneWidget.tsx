import { useState } from "react";
import type { WidgetProps } from "./types";
import { normalizePhone, formatPhone } from "@/utils/fieldFormatters";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

/** Shown formatted, edited raw, stored normalized. */
export const PhoneWidget: React.FC<WidgetProps> = ({ name, value, onChange, disabled, className, mode }) => {
  const [draft, setDraft] = useState<string | null>(null);
  const normalized = String(value ?? "");
  const displayed = formatPhone(normalized);
  if (mode === "print") return <span className="text-[inherit]">{displayed || "—"}</span>;
  return (
    <input type="tel" name={name} value={draft ?? displayed} className={className || s} disabled={disabled}
      placeholder="405.555.1234"
      onFocus={() => setDraft(displayed)}
      onChange={e => setDraft(e.target.value)}
      onBlur={() => { const norm = normalizePhone(draft ?? displayed); setDraft(null); if (norm !== normalized) onChange(norm); }} />
  );
};
