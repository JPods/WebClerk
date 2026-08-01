import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const TextAreaWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, placeholder, rows = 2, className, mode,
}) => {
  if (mode === "print") return <span className="text-xs whitespace-pre-wrap">{value || "—"}</span>;
  return (
    <textarea
      name={name}
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
      rows={rows}
      className={className || s}
    />
  );
};
