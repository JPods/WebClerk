/** JsonWidget — a JSON value as text, with the floating editor a click away. */
import { useState } from "react";
import type { WidgetProps } from "./types";
import { JsonEditor } from "./JsonEditor";

const s = "w-full px-1.5 py-0.5 text-[inherit] font-mono border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";

export const JsonWidget: React.FC<WidgetProps> = ({ name, value, onChange, disabled, rows, className, mode }) => {
  const [editorOpen, setEditorOpen] = useState(false);
  const js = JSON.stringify(value ?? null, null, 2);
  if (mode === "print") return <pre style={{ fontSize: 9, fontFamily: "monospace", whiteSpace: "pre-wrap", margin: 0 }}>{js}</pre>;
  return (
    <span style={{ position: "relative", display: "block", width: "100%" }}>
      <textarea name={name} className={className || s} rows={rows || (js.length > 200 ? 8 : 3)} value={js}
        onChange={e => { try { onChange(JSON.parse(e.target.value)); } catch { /* typing */ } }} disabled={disabled} />
      {!disabled && (
        <button type="button" onClick={() => setEditorOpen(true)} title="Open in the editor"
          style={{ position: "absolute", top: 2, right: 6, fontSize: 11, background: "none", border: "none", cursor: "pointer", color: "var(--db-text-muted, #6c757d)" }}>⤢</button>
      )}
      {editorOpen && <JsonEditor name={name} data={value} onChange={onChange} onClose={() => setEditorOpen(false)} />}
    </span>
  );
};
