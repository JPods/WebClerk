/**
 * JsonViewer — standalone window for displaying JSON with clickable links.
 *
 * Spawned from DataBrowser via window.open(). Receives data via URL params
 * or postMessage. Renders a collapsible tree where:
 *   - URLs open in a new tab (documents are URL pointers)
 *   - _id fields link back to DataBrowser for that record
 *   - Theme matches DataBrowser via shared CSS custom properties
 *
 * Usage from DataBrowser:
 *   window.open(`/json-viewer?model=serial&id=42&field=refs`, '_blank')
 *   // or pass complex JSON via postMessage after open
 */
import React, { useCallback, useEffect, useState } from 'react';
import './JsonViewer.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

interface JsonNodeProps {
  keyName: string | null;
  value: JsonValue;
  depth: number;
  defaultCollapsed: number;  // collapse nodes deeper than this
  onNavigate?: (model: string, id: number) => void;
}

// ---------------------------------------------------------------------------
// Value detection
// ---------------------------------------------------------------------------

function isUrl(v: unknown): v is string {
  if (typeof v !== 'string') return false;
  return /^https?:\/\//.test(v) || /^\/[\w]/.test(v);  // http(s) or absolute path
}

function isIdField(key: string): boolean {
  return /(_id|_uuid)$/.test(key) || key === 'id';
}

function inferModel(key: string): string | null {
  // customer_id → contact, vendor_id → contact, invoice_id → invoice, etc.
  const match = key.match(/^(.+)_id$/);
  if (!match) return null;
  const base = match[1];
  const modelMap: Record<string, string> = {
    customer: 'contact', vendor: 'contact', rep: 'contact',
    parent_item: 'item', child_item: 'item', item: 'item',
    invoice: 'invoice', order: 'order', proposal: 'proposal',
    purchase: 'purchase', workorder: 'workorder',
    payment: 'payment', serial: 'serial',
    po: 'purchase', contact: 'contact',
  };
  return modelMap[base] || base;
}

function isEpochMs(key: string, v: unknown): boolean {
  if (typeof v !== 'number') return false;
  if (!/^(dt_|dt$|date|timestamp)/.test(key)) return false;
  return v > 1_000_000_000_000 && v < 2_000_000_000_000;  // 2001–2033 in ms
}

// ---------------------------------------------------------------------------
// JsonNode — recursive tree renderer
// ---------------------------------------------------------------------------

const JsonNode: React.FC<JsonNodeProps> = ({ keyName, value, depth, defaultCollapsed, onNavigate }) => {
  const isObject = value !== null && typeof value === 'object' && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const isExpandable = isObject || isArray;
  const [collapsed, setCollapsed] = useState(depth >= defaultCollapsed);

  const childCount = isObject ? Object.keys(value).length : isArray ? value.length : 0;

  // Render the key label
  const keyEl = keyName !== null ? (
    <span className={`jv-key ${isIdField(keyName) ? 'jv-key--id' : ''}`}>{keyName}</span>
  ) : null;

  // Leaf node — render value
  if (!isExpandable) {
    let valueEl: React.ReactNode;

    if (value === null) {
      valueEl = <span className="jv-null">null</span>;
    } else if (typeof value === 'boolean') {
      valueEl = <span className={`jv-bool ${value ? 'jv-bool--true' : 'jv-bool--false'}`}>{String(value)}</span>;
    } else if (typeof value === 'number') {
      // Epoch ms → formatted date
      if (keyName && isEpochMs(keyName, value)) {
        const dateStr = new Date(value).toLocaleString();
        valueEl = <span className="jv-date" title={String(value)}>{dateStr}</span>;
      } else {
        valueEl = <span className="jv-number">{value}</span>;
      }
    } else if (typeof value === 'string') {
      if (isUrl(value)) {
        valueEl = (
          <a className="jv-url" href={value} target="_blank" rel="noopener noreferrer" title={value}>
            {value.length > 60 ? value.slice(0, 57) + '...' : value}
          </a>
        );
      } else {
        valueEl = <span className="jv-string">"{value}"</span>;
      }
    } else {
      valueEl = <span className="jv-string">{String(value)}</span>;
    }

    // ID fields — make clickable to open in DataBrowser
    if (keyName && isIdField(keyName) && typeof value === 'number' && value > 0) {
      const model = inferModel(keyName);
      if (model && onNavigate) {
        valueEl = (
          <span className="jv-id-link" onClick={() => onNavigate(model, value)} title={`Open ${model} #${value} in DataBrowser`}>
            {value} ↗
          </span>
        );
      }
    }

    return (
      <div className="jv-leaf" style={{ paddingLeft: depth * 16 }}>
        {keyEl}{keyEl && <span className="jv-colon">: </span>}{valueEl}
      </div>
    );
  }

  // Expandable node — object or array
  const bracket = isArray ? ['[', ']'] : ['{', '}'];

  return (
    <div className="jv-node">
      <div className="jv-node-header" style={{ paddingLeft: depth * 16 }}
        onClick={() => setCollapsed(!collapsed)}>
        <span className="jv-chevron">{collapsed ? '▶' : '▼'}</span>
        {keyEl}{keyEl && <span className="jv-colon">: </span>}
        <span className="jv-bracket">{bracket[0]}</span>
        {collapsed && <span className="jv-collapsed-hint"> {childCount} {isArray ? 'items' : 'keys'} </span>}
        {collapsed && <span className="jv-bracket">{bracket[1]}</span>}
      </div>
      {!collapsed && (
        <>
          {isArray
            ? (value as JsonValue[]).map((item, i) => (
                <JsonNode key={i} keyName={String(i)} value={item} depth={depth + 1}
                  defaultCollapsed={defaultCollapsed} onNavigate={onNavigate} />
              ))
            : Object.entries(value as Record<string, JsonValue>).map(([k, v]) => (
                <JsonNode key={k} keyName={k} value={v} depth={depth + 1}
                  defaultCollapsed={defaultCollapsed} onNavigate={onNavigate} />
              ))
          }
          <div className="jv-bracket-close" style={{ paddingLeft: depth * 16 }}>{bracket[1]}</div>
        </>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// JsonViewer page
// ---------------------------------------------------------------------------

const JsonViewer: React.FC = () => {
  const [data, setData] = useState<JsonValue>(null);
  const [title, setTitle] = useState('JSON Viewer');
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('db-theme') as 'dark' | 'light') || 'dark'
  );
  const [collapseDepth, setCollapseDepth] = useState(2);
  const [copyMsg, setCopyMsg] = useState('');

  // Track which model/id/field this viewer is showing (for cross-window reload)
  const [viewerModel, setViewerModel] = useState('');
  const [viewerId, setViewerId] = useState('');
  const [viewerField, setViewerField] = useState('');

  // Fetch a record's field data
  const fetchData = useCallback((model: string, id: string, field: string) => {
    if (!model || !id) return;
    setTitle(`${model} #${id}${field ? ` · ${field}` : ''}`);
    fetch(`/wcapi/get/?model_name=${model}&id=${id}`)
      .then(r => r.json())
      .then(resp => {
        const record = resp?.data?.record || resp?.record || resp?.data || resp;
        setData(field ? (record[field] ?? record) : record);
      })
      .catch(() => setData({ error: 'Failed to fetch record' }));
  }, []);

  // Load data from URL params or postMessage
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const model = params.get('model') || '';
    const id = params.get('id') || '';
    const field = params.get('field') || '';
    const rawJson = params.get('json');

    setViewerModel(model);
    setViewerId(id);
    setViewerField(field);

    if (rawJson) {
      try { setData(JSON.parse(rawJson)); } catch { setData({ error: 'Invalid JSON in URL' }); }
      setTitle(`${model} #${id} · ${field}`);
    } else if (model && id) {
      fetchData(model, id, field);
    }

    // Also accept postMessage for large JSON
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'json-viewer-data') {
        setData(e.data.json);
        if (e.data.title) setTitle(e.data.title);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [fetchData]);

  // Listen for cross-window messages from DataBrowser
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    import('@/utils/windowChannel').then(({ windowChannel }) => {
      // When DataBrowser selects a new record of the same model, reload
      const unsub1 = windowChannel.on('record-selected', (msg) => {
        if (msg.model === viewerModel && msg.id) {
          setViewerId(String(msg.id));
          fetchData(viewerModel, String(msg.id), viewerField);
        }
      });
      // When a record is saved, reload if it's the one we're showing
      const unsub2 = windowChannel.on('record-saved', (msg) => {
        if (msg.model === viewerModel && String(msg.id) === viewerId) {
          fetchData(viewerModel, viewerId, viewerField);
        }
      });
      // Theme sync across windows
      const unsub3 = windowChannel.on('theme-changed', (msg) => {
        if (typeof msg.data === 'string' && (msg.data === 'dark' || msg.data === 'light')) {
          setTheme(msg.data);
        }
      });
      cleanup = () => { unsub1(); unsub2(); unsub3(); };
    }).catch(() => {});
    return () => cleanup?.();
  }, [viewerModel, viewerId, viewerField, fetchData]);

  const handleNavigate = useCallback((model: string, id: number) => {
    window.open(`/admin-wb?model=${model}&id=${id}`, '_blank');
  }, []);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopyMsg('Copied');
    setTimeout(() => setCopyMsg(''), 1500);
  }, [data]);

  return (
    <div className="jv-root" data-theme={theme}>
      <header className="jv-header">
        <span className="jv-title">{title}</span>
        <div className="jv-controls">
          <label className="jv-depth-label">
            Depth:
            <select className="jv-depth-select" value={collapseDepth}
              onChange={(e) => setCollapseDepth(Number(e.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={99}>All</option>
            </select>
          </label>
          <button className="jv-btn" onClick={handleCopy}>{copyMsg || 'Copy'}</button>
          <button className="jv-btn" onClick={() => {
            const n = theme === 'dark' ? 'light' : 'dark';
            setTheme(n);
            localStorage.setItem('db-theme', n);
          }}>{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </div>
      </header>
      <div className="jv-body">
        {data !== null ? (
          <JsonNode keyName={null} value={data} depth={0}
            defaultCollapsed={collapseDepth} onNavigate={handleNavigate} />
        ) : (
          <div className="jv-empty">No data loaded. Pass ?model=X&id=N&field=F in the URL.</div>
        )}
      </div>
    </div>
  );
};

export default JsonViewer;
