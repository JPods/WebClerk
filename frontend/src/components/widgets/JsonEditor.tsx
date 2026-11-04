/** JsonEditor — the floating split pane (code left, tree right) every JSON widget opens. */
import { useCallback, useEffect, useRef, useState } from "react";
import { JsonTree } from "./JsonTreeWidget";

export function JsonEditor({ name, data, onChange, onClose }: {
  name: string; data: any; onChange: (v: any) => void; onClose: () => void;
}) {
  const [code, setCode] = useState(() => JSON.stringify(data, null, 2));
  const [treeData, setTreeData] = useState(data);
  const [error, setError] = useState("");
  const overlayRef = useRef<HTMLDivElement>(null);

  const handleCodeChange = useCallback((text: string) => {
    setCode(text);
    try { setTreeData(JSON.parse(text)); setError(""); } catch (e: any) { setError(e.message); }
  }, []);
  const handleTreeChange = useCallback((next: any) => { setTreeData(next); setCode(JSON.stringify(next, null, 2)); setError(""); }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div ref={overlayRef} className="db-json-overlay" onClick={e => { if (e.target === overlayRef.current) onClose(); }}>
      <div className="db-json-editor">
        <div className="db-json-editor-titlebar">
          <div className="db-json-editor-title">
            <span>{name}</span>
            {error && <span className="db-json-editor-error">{error}</span>}
          </div>
          <div className="db-json-editor-actions">
            <button onClick={() => { if (!error) { onChange(treeData); onClose(); } }} disabled={!!error} className="db-json-editor-save">Save</button>
            <button onClick={onClose} className="db-json-editor-close">Close</button>
          </div>
        </div>
        <div className="db-json-editor-body">
          <div className="db-json-editor-code">
            <div className="db-json-editor-pane-label">Code</div>
            <textarea className="db-json-editor-textarea" value={code} onChange={e => handleCodeChange(e.target.value)} spellCheck={false} />
          </div>
          <div className="db-json-editor-tree">
            <div className="db-json-editor-pane-label">Tree</div>
            <div className="db-json-editor-tree-scroll">
              {error ? <div className="db-json-editor-tree-empty">Fix the JSON to see the tree</div>
                : <JsonTree data={treeData} onChange={handleTreeChange} defaultExpanded maxHeight="none" style={{ border: "none", background: "transparent" }} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
