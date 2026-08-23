import type { WidgetProps } from "./types";

export const ReadonlyWidget: React.FC<WidgetProps> = ({ value }) => {
  const display = value === null || value === undefined ? "—"
    : typeof value === "object" ? JSON.stringify(value)
    : String(value);
  return <span className="text-[inherit] text-gray-600 dark:text-gray-300">{display}</span>;
};
