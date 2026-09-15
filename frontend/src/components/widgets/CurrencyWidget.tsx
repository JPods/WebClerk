import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60 text-right";

export const CurrencyWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, className, mode,
}) => {
  const fmt = (v: any) => {
    const n = typeof v === "number" ? v : parseFloat(v);
    if (isNaN(n)) return "—";
    return n.toLocaleString(undefined, { style: "currency", currency: "USD", minimumFractionDigits: 2 });
  };

  if (mode === "print") return <span className="text-[inherit]">{fmt(value)}</span>;
  return (
    <input
      type="number"
      name={name}
      value={value ?? ""}
      onChange={e => onChange(Number(e.target.value))}
      disabled={disabled}
      step={0.01}
      min={0}
      className={className || s}
    />
  );
};
