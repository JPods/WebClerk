import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const AddressWidget: React.FC<WidgetProps> = ({ name, value, onChange, disabled, className, mode }) => {
  const v = String(value ?? "");
  if (mode === "print") return <span className="text-[inherit]">{v || "—"}</span>;
  return <input type="text" name={name} value={v} className={className || s} disabled={disabled} onChange={e => onChange(e.target.value)} />;
};

/** The map a full address opens. */
export function addressHref(value: unknown): string | undefined {
  const v = String(value ?? "");
  return v ? `https://maps.google.com/?q=${encodeURIComponent(v)}` : undefined;
}
