import type { WidgetProps } from "./types";

export const CheckboxWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, mode,
}) => {
  if (mode === "print") return <span className="text-xs">{value ? "Yes" : "No"}</span>;
  return (
    <input
      type="checkbox"
      name={name}
      checked={Boolean(value)}
      onChange={e => onChange(e.target.checked)}
      disabled={disabled}
      className="h-4 w-4 rounded border-gray-300 text-indigo-600 dark:border-gray-600 dark:bg-gray-700"
    />
  );
};
