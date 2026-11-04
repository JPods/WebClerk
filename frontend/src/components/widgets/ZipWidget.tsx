import { useState } from "react";
import type { WidgetProps } from "./types";
import { normalizeZip, formatZip } from "@/utils/fieldFormatters";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const ZipWidget: React.FC<WidgetProps> = ({ name, value, onChange, disabled, className, mode }) => {
  const [draft, setDraft] = useState<string | null>(null);
  const normalized = String(value ?? "");
  const displayed = formatZip(normalized, "US");
  if (mode === "print") return <span className="text-[inherit]">{displayed || "—"}</span>;
  return (
    <input type="text" name={name} value={draft ?? displayed} className={className || s} disabled={disabled}
      placeholder="74135"
      onFocus={() => setDraft(displayed)}
      onChange={e => setDraft(e.target.value)}
      onBlur={() => { const norm = normalizeZip(draft ?? displayed, "US"); setDraft(null); if (norm !== normalized) onChange(norm); }} />
  );
};
