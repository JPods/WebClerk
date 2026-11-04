import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const GeoWidget: React.FC<WidgetProps> = ({ name, value, onChange, disabled, className, mode }) => {
  if (mode === "print") return <span className="text-[inherit]">{value ?? "—"}</span>;
  return (
    <input type="number" step="any" name={name} value={value != null ? String(value) : ""} className={className || s}
      disabled={disabled} onChange={e => onChange(parseFloat(e.target.value) || 0)} />
  );
};

/** The map a latitude/longitude pair opens. */
export function geoHref(name: string, value: unknown, pair?: string, record?: Record<string, any>): string | undefined {
  const lat = name === "latitude" ? value : record?.[pair || ""];
  const lng = name === "longitude" ? value : record?.[pair || ""];
  return lat && lng ? `https://maps.google.com/?q=${lat},${lng}` : undefined;
}
