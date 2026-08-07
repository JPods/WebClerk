import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const SelectWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, options = [], className, mode,
}) => {
  if (mode === "print") {
    const match = options.find(o => String(o.value) === String(value));
    return <span className="text-[inherit]">{match?.label || value || "—"}</span>;
  }
  return (
    <select
      name={name}
      value={value ?? ""}
      onChange={e => {
        const raw = e.target.value;
        // Preserve numeric types
        const opt = options.find(o => String(o.value) === raw);
        onChange(opt ? opt.value : raw);
      }}
      disabled={disabled}
      className={className || s}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
};
