import React from "react";
import type { WidgetProps } from "./types";

const s = "w-full px-1.5 py-0.5 text-[inherit] border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

/** One select for every form. Options come from the model's selectlists (one source). A blank
 *  row clears. Cmd/Ctrl+click toggles a value into a comma list. allowCustom adds a typed value.
 *  An object value (assigned_to: {"en": "Bill"}) is compared and returned as its JSON. */
export const SelectWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, options = [], allowCustom, className, mode,
}) => {
  const isObjectValue = typeof value === "object" && value !== null;
  const currentVal = isObjectValue ? JSON.stringify(value) : String(value ?? "");
  const inList = options.some(o => String(o.value) === currentVal);
  const emit = (raw: string) => {
    if (isObjectValue) { try { onChange(JSON.parse(raw)); } catch { onChange(raw); } return; }
    const opt = options.find(o => String(o.value) === raw);   // keep a numeric option numeric
    onChange(opt ? opt.value : raw);
  };

  if (mode === "print") {
    const match = options.find(o => String(o.value) === currentVal);
    return <span className="text-[inherit]">{match?.label || currentVal || "—"}</span>;
  }
  const cls = className || s;

  if (allowCustom) {
    return (
      <span style={{ display: 'inline-flex', gap: 4, width: '100%' }}>
        <select name={name} className={cls} style={{ flex: 1 }}
          value={inList ? currentVal : "__custom__"}
          onChange={e => { if (e.target.value !== "__custom__") emit(e.target.value); }}
          disabled={disabled}>
          <option value="">--</option>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          {!inList && currentVal && <option value="__custom__">{currentVal}</option>}
          <option value="__custom__">other...</option>
        </select>
        {(!inList || currentVal === "") && (
          <input className={cls} style={{ flex: 1 }} value={currentVal}
            onChange={e => emit(e.target.value)} placeholder="type here" disabled={disabled} />
        )}
      </span>
    );
  }

  const selectedValues = currentVal ? currentVal.split(",").map(v => v.trim()).filter(Boolean) : [];
  const handleClick = (e: React.MouseEvent<HTMLSelectElement>) => {
    if (!(e.metaKey || e.ctrlKey)) return;
    const select = e.currentTarget;
    const clicked = select.options[select.selectedIndex]?.value;
    if (!clicked) return;
    const idx = selectedValues.indexOf(clicked);
    const next = idx >= 0 ? selectedValues.filter(v => v !== clicked) : [...selectedValues, clicked];
    emit(next.join(", "));
    e.preventDefault();
  };

  return (
    <select
      name={name}
      value={currentVal}
      onClick={handleClick}
      onChange={e => emit(e.target.value)}
      disabled={disabled}
      className={cls}
    >
      <option value="">--</option>
      {options.map(o => {
        const picked = selectedValues.length > 1 && selectedValues.includes(String(o.value));
        return <option key={o.value} value={o.value} style={picked ? { fontWeight: "bold" } : undefined}>{picked ? "✓ " : ""}{o.label}</option>;
      })}
    </select>
  );
};
