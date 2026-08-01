/**
 * JsonTextWidget — for multilingual JSON fields like {en: "...", ar: "..."}.
 * Shows/edits the primary language (en). Expand for other languages later.
 */
import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const JsonTextWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, placeholder, className, mode,
}) => {
  // value is the extracted string (e.g. action.en), not the JSON object
  if (mode === "print") return <span className="text-xs">{value || "—"}</span>;
  return (
    <input
      type="text"
      name={name}
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
      className={className || s}
    />
  );
};
