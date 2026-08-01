import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const DateWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, min, max, className, mode,
}) => {
  if (mode === "print") {
    if (!value) return <span className="text-xs">—</span>;
    try {
      return <span className="text-xs">{new Date(value).toLocaleDateString()}</span>;
    } catch {
      return <span className="text-xs">{value}</span>;
    }
  }
  return (
    <input
      type="date"
      name={name}
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      min={min as string}
      max={max as string}
      className={className || s}
    />
  );
};
