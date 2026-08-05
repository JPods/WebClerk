/**
 * JSON Tree — free public JSON editor at webclerk.com/json-tree
 *
 * Paste JSON, explore as a tree, edit inline, format, validate, minify.
 * No login required. No data leaves the browser.
 * Side-by-side: code editor (left) + tree view (right).
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';

// ── Stats ────────────────────────────────────────────────────────────

function jsonStats(data: any): { keys: number; depth: number; arrays: number; size: string } {
  let keys = 0, depth = 0, arrays = 0;
  const walk = (v: any, d: number) => {
    if (d > depth) depth = d;
    if (v === null || typeof v !== 'object') return;
    if (Array.isArray(v)) { arrays++; v.forEach(item => walk(item, d + 1)); }
    else { const ks = Object.keys(v); keys += ks.length; ks.forEach(k => walk(v[k], d + 1)); }
  };
  walk(data, 0);
  const bytes = new Blob([JSON.stringify(data)]).size;
  const size = bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;
  return { keys, depth, arrays, size };
}

// ── Sample data ──────────────────────────────────────────────────────

const SAMPLE = {
  name: "WebClerk JSON Tree",
  version: "1.0",
  description: "Free JSON editor. Paste, explore, edit, format, validate.",
  features: ["tree view", "inline editing", "format", "minify", "validate", "dark mode"],
  example: {
    user: { id: 42, name: "Alice", active: true, roles: ["admin", "editor"] },
    settings: { theme: "dark", language: "en", notifications: { email: true, sms: false } },
    tags: ["open-source", "free", "no-login"],
  },
  links: { website: "webclerk.com", source: "bottom-up, locally governed" },
};

// ── Theme ────────────────────────────────────────────────────────────

const LIGHT = {
  bg: '#ffffff', surface: '#f8fafc', border: '#e2e8f0', text: '#0f172a',
  textMuted: '#64748b', textDim: '#94a3b8', primary: '#465fff', danger: '#dc2626',
  success: '#16a34a', inputBg: '#ffffff', surfaceAlt: '#f1f5f9',
  codeBg: '#f8fafc', codeText: '#334155',
};
const DARK = {
  bg: '#0f172a', surface: '#1e293b', border: '#334155', text: '#f1f5f9',
  textMuted: '#94a3b8', textDim: '#64748b', primary: '#60a5fa', danger: '#f87171',
  success: '#4ade80', inputBg: '#1e293b', surfaceAlt: '#334155',
  codeBg: '#1e293b', codeText: '#e2e8f0',
};

export default function JsonTreeApplet() {
  const [code, setCode] = useState(() => JSON.stringify(SAMPLE, null, 2));
  const [data, setData] = useState<any>(SAMPLE);
  const [error, setError] = useState('');
  const [dark, setDark] = useState(() => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false);
  const [splitPct, setSplitPct] = useState(45);
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const th = dark ? DARK : LIGHT;

  // Sync code → tree
  const parseCode = useCallback((text: string) => {
    setCode(text);
    try {
      const parsed = JSON.parse(text);
      setData(parsed);
      setError('');
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  // Sync tree → code
  const handleTreeChange = useCallback((newData: any) => {
    setData(newData);
    setCode(JSON.stringify(newData, null, 2));
    setError('');
  }, []);

  // Actions
  const doFormat = () => { try { setCode(JSON.stringify(JSON.parse(code), null, 2)); setError(''); } catch (e: any) { setError(e.message); } };
  const doMinify = () => { try { setCode(JSON.stringify(JSON.parse(code))); setError(''); } catch (e: any) { setError(e.message); } };
  const doValidate = () => { try { JSON.parse(code); setError(''); alert('Valid JSON'); } catch (e: any) { setError(e.message); } };
  const doCopy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  const doClear = () => { setCode(''); setData({}); setError(''); };
  const doSample = () => { const s = JSON.stringify(SAMPLE, null, 2); setCode(s); setData(SAMPLE); setError(''); };

  // Drag splitter
  const dragging = useRef(false);
  const onMouseDown = () => { dragging.current = true; };
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(Math.max(20, Math.min(80, pct)));
    };
    const onUp = () => { dragging.current = false; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  // File drop
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => parseCode(reader.result as string);
    reader.readAsText(file);
  };

  const stats = error ? null : jsonStats(data);

  const btnStyle: React.CSSProperties = {
    padding: '5px 12px', borderRadius: 5, fontSize: 12, fontWeight: 500, cursor: 'pointer',
    border: `1px solid ${th.border}`, background: th.surface, color: th.text,
    transition: 'background 150ms',
  };
  const btnPrimary: React.CSSProperties = { ...btnStyle, background: th.primary, color: '#fff', border: 'none' };

  return (
    <div style={{ minHeight: '100vh', background: th.bg, color: th.text, fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Header */}
      <header style={{ borderBottom: `1px solid ${th.border}`, padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16, background: th.surface }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
          <span style={{ color: th.primary }}>JSON</span> Tree
        </h1>
        <span style={{ fontSize: 11, color: th.textDim }}>Paste, explore, edit, format — free, no login, nothing leaves your browser</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          {stats && (
            <span style={{ fontSize: 10, color: th.textDim, fontFamily: 'monospace', marginRight: 8 }}>
              {stats.keys} keys · depth {stats.depth} · {stats.arrays} arrays · {stats.size}
            </span>
          )}
          <button style={btnStyle} onClick={() => setDark(!dark)} title="Toggle dark mode">
            {dark ? '☀' : '🌙'}
          </button>
        </span>
      </header>

      {/* Toolbar */}
      <div style={{ borderBottom: `1px solid ${th.border}`, padding: '6px 24px', display: 'flex', gap: 6, background: th.surface, flexWrap: 'wrap' }}>
        <button style={btnPrimary} onClick={doFormat}>Format</button>
        <button style={btnStyle} onClick={doMinify}>Minify</button>
        <button style={btnStyle} onClick={doValidate}>Validate</button>
        <button style={{ ...btnStyle, ...(copied ? { background: th.success, color: '#fff', border: 'none' } : {}) }} onClick={doCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
        <button style={btnStyle} onClick={doClear}>Clear</button>
        <button style={btnStyle} onClick={doSample}>Sample</button>
        {error && <span style={{ fontSize: 12, color: th.danger, fontFamily: 'monospace', alignSelf: 'center', marginLeft: 8 }}>{error}</span>}
      </div>

      {/* Split pane: code + tree */}
      <div ref={containerRef} style={{ display: 'flex', height: 'calc(100vh - 130px)', overflow: 'hidden' }}
        onDragOver={e => e.preventDefault()} onDrop={onDrop}>

        {/* Code editor */}
        <div style={{ width: `${splitPct}%`, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${th.border}` }}>
          <div style={{ padding: '4px 12px', fontSize: 10, fontWeight: 600, color: th.textDim, textTransform: 'uppercase', letterSpacing: '0.06em', background: th.surfaceAlt, borderBottom: `1px solid ${th.border}` }}>
            Code Editor — paste or drop a .json file
          </div>
          <textarea
            ref={codeRef}
            value={code}
            onChange={e => parseCode(e.target.value)}
            spellCheck={false}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none', padding: 16,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 12, lineHeight: 1.6,
              background: th.codeBg, color: th.codeText, tabSize: 2,
            }}
            placeholder='Paste JSON here, or drop a .json file...'
          />
        </div>

        {/* Splitter */}
        <div
          onMouseDown={onMouseDown}
          style={{ width: 5, cursor: 'col-resize', background: th.border, flexShrink: 0, transition: 'background 150ms' }}
        />

        {/* Tree view */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          <div style={{ padding: '4px 12px', fontSize: 10, fontWeight: 600, color: th.textDim, textTransform: 'uppercase', letterSpacing: '0.06em', background: th.surfaceAlt, borderBottom: `1px solid ${th.border}`, flexShrink: 0 }}>
            Tree View — click values to edit, hover for actions
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: 8, paddingBottom: 60 }}>
            {error ? (
              <div style={{ padding: 32, textAlign: 'center', color: th.textDim, fontSize: 13 }}>
                Fix the JSON error to see the tree
              </div>
            ) : (
              <JsonTree
                data={data}
                onChange={handleTreeChange}
                defaultExpanded
                maxHeight="none"
                theme={{ text: th.text, textMuted: th.textMuted, border: th.border, surfaceAlt: th.surfaceAlt, inputBg: th.inputBg }}
                style={{ border: 'none', background: 'transparent', display: 'flex', flexDirection: 'column', height: '100%' }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '4px 24px', fontSize: 10, color: th.textDim, background: th.surface, borderTop: `1px solid ${th.border}`, display: 'flex', justifyContent: 'space-between' }}>
        <span>webclerk.com/json-tree — free, open source, bottom-up</span>
        <span>All processing happens in your browser. Nothing is sent to any server.</span>
      </div>
    </div>
  );
}
