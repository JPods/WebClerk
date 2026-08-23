/**
 * JSON Tree — free public JSON editor at webclerk.com/json-tree
 *
 * Paste JSON, explore as a tree, edit inline, format, validate, minify.
 * No login required. No data leaves the browser.
 * Side-by-side: code editor (left) + tree view (right).
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';
import './JsonTreeApplet.css';

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

export default function JsonTreeApplet() {
  const [code, setCode] = useState(() => JSON.stringify(SAMPLE, null, 2));
  const [data, setData] = useState<any>(SAMPLE);
  const [error, setError] = useState('');
  const [dark, setDark] = useState(() => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false);
  const [splitPct, setSplitPct] = useState(45);
  const [copied, setCopied] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [posting, setPosting] = useState(false);
  const [postResult, setPostResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [filePath, setFilePath] = useState('');
  const codeRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  // Load from URL param or localStorage (Matrix Builder sends data via ?json=... or localStorage)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const jsonParam = params.get('json');
    const fromParam = params.get('from');
    if (jsonParam) {
      try { parseCode(decodeURIComponent(jsonParam)); } catch { /* ignore */ }
      window.history.replaceState({}, '', window.location.pathname);
    } else if (fromParam === 'matrix-builder') {
      const stored = localStorage.getItem('matrix-builder-bundle');
      if (stored) { parseCode(stored); localStorage.removeItem('matrix-builder-bundle'); setFilePath('matrix-builder-bundle.json'); }
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Actions
  const doFormat = () => { try { setCode(JSON.stringify(JSON.parse(code), null, 2)); setError(''); } catch (e: any) { setError(e.message); } };
  const doMinify = () => { try { setCode(JSON.stringify(JSON.parse(code))); setError(''); } catch (e: any) { setError(e.message); } };
  const doValidate = () => { try { JSON.parse(code); setError(''); alert('Valid JSON'); } catch (e: any) { setError(e.message); } };
  const doCopy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  const doClear = () => { setCode(''); setData({}); setError(''); setPostResult(null); setFilePath(''); };
  const doSample = () => { const s = JSON.stringify(SAMPLE, null, 2); setCode(s); setData(SAMPLE); setError(''); setPostResult(null); setFilePath('sample.json'); };

  // Save as .json file
  const doSave = () => {
    if (!code.trim()) return;
    const blob = new Blob([code], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath || 'data.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Post as bundle to WC3 SelfConnection
  const doPostBundle = async () => {
    if (error || !code.trim()) return;
    setPosting(true);
    setPostResult(null);
    try {
      const payload = JSON.parse(code);
      const body = {
        idempotency_key: crypto.randomUUID(),
        sequence: 1,
        payload,
        meta: { source: 'json-tree', posted: new Date().toISOString() },
      };
      const res = await fetch('/wcapi/sync/receive/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Sync-Key': 'self-connection',
        },
        body: JSON.stringify(body),
      });
      const result = await res.json();
      if (result.ack) {
        setPostResult({ ok: true, msg: `Bundle #${result.bundle_id} created` });
      } else {
        setPostResult({ ok: false, msg: result.error || 'Post failed' });
      }
    } catch (e: any) {
      setPostResult({ ok: false, msg: e.message || 'Network error' });
    } finally {
      setPosting(false);
    }
  };

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

  // File drop + file input
  const loadFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => { parseCode(reader.result as string); setFilePath(file.name); };
    reader.readAsText(file);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) loadFile(file);
  };
  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) loadFile(file);
    e.target.value = '';
  };

  const stats = error ? null : jsonStats(data);
  const themeAttr = dark ? 'dark' : 'light';

  return (
    <div className="jt-root" data-jt-theme={themeAttr}>
      {/* Header */}
      <header className="jt-header">
        <h1><span>JSON</span> Tree</h1>
        {filePath ? (
          <span className="jt-header-file">{filePath}</span>
        ) : (
          <span className="jt-header-sub">Paste, explore, edit, format — free, no login, nothing leaves your browser</span>
        )}
        <span className="jt-header-right">
          {stats && (
            <span className="jt-stats">
              {stats.keys} keys · depth {stats.depth} · {stats.arrays} arrays · {stats.size}
            </span>
          )}
          <button className="jt-btn" onClick={() => setDark(!dark)} title="Toggle dark mode">
            {dark ? '☀' : '🌙'}
          </button>
        </span>
      </header>

      {/* Toolbar */}
      <div className="jt-toolbar">
        <button className="jt-btn jt-btn--primary" onClick={doFormat}>Format</button>
        <button className="jt-btn" onClick={doMinify}>Minify</button>
        <button className="jt-btn" onClick={doValidate}>Validate</button>
        <button className={`jt-btn ${copied ? 'jt-btn--copied' : ''}`} onClick={doCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
        <button className="jt-btn" onClick={doClear}>Clear</button>
        <button className="jt-btn" onClick={doSample}>Sample</button>
        <span className="jt-toolbar-divider" />
        <button className="jt-btn" onClick={doSave} title="Save as .json file">Save</button>
        <button
          className="jt-btn jt-btn--success"
          onClick={doPostBundle}
          disabled={posting || !!error}
          style={{ opacity: posting ? 0.6 : 1 }}
          title="Post as bundle to WebClerk"
        >
          {posting ? 'Posting...' : 'Post Bundle'}
        </button>
        {postResult && (
          <span className="jt-toolbar-msg" style={{ color: postResult.ok ? 'var(--jt-success)' : 'var(--jt-danger)' }}>
            {postResult.msg}
          </span>
        )}
        {error && <span className="jt-toolbar-error">{error}</span>}
      </div>

      {/* Drop zone */}
      <input ref={fileInputRef} type="file" accept=".json,.txt" style={{ display: 'none' }} onChange={onFileInput} />
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`jt-dropzone ${dragOver ? 'jt-dropzone--active' : ''}`}
      >
        {dragOver ? 'Drop JSON file here' : 'Drop a .json file here, or click to browse'}
      </div>

      {/* Split pane: code + tree */}
      <div ref={containerRef} className="jt-split" onDragOver={e => e.preventDefault()} onDrop={onDrop}>

        {/* Code editor — width is dynamic (split drag) */}
        <div className="jt-code-pane" style={{ width: `${splitPct}%` }}>
          <div className="jt-pane-label">Code Editor — paste or drop a .json file</div>
          <textarea
            ref={codeRef}
            value={code}
            onChange={e => parseCode(e.target.value)}
            spellCheck={false}
            className="jt-code-editor"
            placeholder='Paste JSON here, or drop a .json file...'
          />
        </div>

        {/* Splitter */}
        <div className="jt-splitter" onMouseDown={onMouseDown} />

        {/* Tree view */}
        <div className="jt-tree-pane">
          <div className="jt-pane-label">Tree View — click values to edit, hover for actions</div>
          <div className="jt-tree-body">
            {error ? (
              <div className="jt-tree-empty">Fix the JSON error to see the tree</div>
            ) : (
              <JsonTree
                data={data}
                onChange={handleTreeChange}
                defaultExpanded
                maxHeight="none"
                theme={{
                  text: 'var(--jt-text)', textMuted: 'var(--jt-text-muted)',
                  border: 'var(--jt-border)', surfaceAlt: 'var(--jt-surface-alt)',
                  inputBg: 'var(--jt-input-bg)',
                }}
                style={{ border: 'none', background: 'transparent', display: 'flex', flexDirection: 'column', height: '100%' }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="jt-footer">
        <span>webclerk.com/json-tree — free, open source, bottom-up</span>
        <span>All processing happens in your browser. Nothing is sent to any server.</span>
      </div>
    </div>
  );
}
