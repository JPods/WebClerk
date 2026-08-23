/**
 * ContactLookup — text input with click-to-view contact card.
 * Shows the assigned name. Click label to open contact popup.
 */
import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const ContactLookup: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, className, mode, record,
}) => {
  if (mode === "print") return <span className="text-[inherit]">{value || "—"}</span>;

  // Future: add autocomplete dropdown, contact card popup on click
  return (
    <input
      type="text"
      name={name}
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      placeholder="Search contacts..."
      className={className || s}
    />
  );
};
