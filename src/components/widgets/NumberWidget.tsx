import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const NumberWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, min, max, step, className, mode,
}) => {
  if (mode === "print") return <span className="text-[inherit]">{value ?? "—"}</span>;
  return (
    <input
      type="number"
      name={name}
      value={value ?? ""}
      onChange={e => onChange(Number(e.target.value))}
      disabled={disabled}
      min={min as number}
      max={max as number}
      step={step}
      className={className || s}
    />
  );
};
