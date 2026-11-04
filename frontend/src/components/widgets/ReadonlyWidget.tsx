import type { WidgetProps } from "./types";
import { formatDt } from "@/utils/fieldFormatters";
import { nameOf } from "./LookupWidget";

/** A value shown and never typed. A record reference shows its name; a dt_ shows local time. */
export const ReadonlyWidget: React.FC<WidgetProps> = ({ name, value, className }) => {
  const display = value === null || value === undefined || value === "" ? "—"
    : typeof value === "object"
      ? nameOf(value) || JSON.stringify(value)
    : (name.startsWith("dt_") && (typeof value === "number" || /^\d{4}-\d{2}-\d{2}T/.test(String(value))))
      ? formatDt(value, "datetime", name)
    : String(value);
  return (
    <span className={className || "text-[inherit] text-gray-600 dark:text-gray-300"}
      style={className ? { display: "inline-block" } : undefined}>{display}</span>
  );
};
