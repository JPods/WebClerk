/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Whitelist Tester — interactive API endpoint tester.
 *
 * Presets cover the REST channel: /wcapi/<model>/ and /wcapi/<model>/<id>/, the HTTP
 * method naming get, save or delete (Bill, 2026-09-24: REST only).
 *
 * Related files:
 *   wc3  apps/core/views/channel_view.py          — the REST channel
 *   wc3  tests/test_route_shape.py                — holds every route to the REST shape
 *   r25  src/api/modelNameResolver.ts              — canonical model-name resolution
 */
import React, { useMemo, useState } from 'react';
import apiClient, { authClient } from '../../api/axios';

type HttpMethod = 'GET' | 'POST';

type Preset = {
  label: string;
  method: HttpMethod;
  url: string;
  body: Record<string, any>;
  info: {
    description: string;
    requires?: {
      query?: string[];
      body?: string[];
      headers?: string[];
    };
    notes?: string[];
    example?: Record<string, any>;
  };
};

const PRESETS: Preset[] = [
  // ── Auth ───────────────────────────────────────────────────────────────
  {
    label: 'Login (POST)',
    method: 'POST',
    url: '/api/auth/login/',
    body: { username: 'demo', password: 'demo' },
    info: {
      description: 'Obtain access/refresh tokens for API calls.',
      requires: { body: ['username', 'password'] },
      notes: ['Uses auth origin if configured (AUTH_URL).', 'Response includes tokens under data or top-level depending on backend.'],
      example: { username: 'demo', password: 'demo' },
    },
  },

  // ── WCAPI: Meta / Discovery ────────────────────────────────────────────
  {
    label: 'Models (GET)',
    method: 'GET',
    url: '/wcapi/_model_list/',
    body: {},
    info: {
      description: 'Returns whitelisted model names from registry.',
      notes: ['No params required.', 'Used by Admin Workbench left pane.'],
    },
  },
  {
    label: 'Choice Catalog (GET)',
    method: 'GET',
    url: '/wcapi/_choices/',
    body: {},
    info: {
      description: 'Aggregates DEFAULT_SELECT_LISTS from all app-level choices modules.',
      notes: [
        'Add ?app=core&app=transactions to focus specific apps.',
        'Use ?refresh=1 to rebuild the cached registry before responding.',
        'Response shape: { apps: { app_label: { model: { field: [{ value, label }]}}}, meta: {...} }',
      ],
    },
  },
  {
    label: 'Model Detail (GET)',
    method: 'GET',
    url: '/wcapi/_model_detail/?model_name=contact',
    body: {},
    info: {
      description: 'Returns model metadata including fields.',
      requires: { query: ['model_name'] },
      notes: ['model_name must be a canonical or resolvable name.'],
    },
  },

  // ── WCAPI: GET endpoints ───────────────────────────────────────────────
  {
    label: 'wcapi › Contact List',
    method: 'GET',
    url: '/wcapi/contact/?limit=10',
    body: {},
    info: {
      description: 'List contacts via wcapi gateway.',
      requires: { query: ['model_name'] },
      notes: ['Optional: id, limit, offset, search, filters.'],
    },
  },
  {
    label: 'wcapi › Contact Detail',
    method: 'GET',
    url: '/wcapi/contact/1/',
    body: {},
    info: {
      description: 'Single contact by ID via wcapi.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Customer List',
    method: 'GET',
    url: '/wcapi/customer/?limit=10',
    body: {},
    info: {
      description: 'List customers via wcapi gateway.',
      requires: { query: ['model_name'] },
    },
  },
  {
    label: 'wcapi › Vendor List',
    method: 'GET',
    url: '/wcapi/vendor/?limit=10',
    body: {},
    info: {
      description: 'List vendors via wcapi gateway.',
      requires: { query: ['model_name'] },
    },
  },
  {
    label: 'wcapi › Item List',
    method: 'GET',
    url: '/wcapi/item/?limit=10',
    body: {},
    info: {
      description: 'List items (canonical product model).',
      requires: { query: ['model_name'] },
    },
  },
  {
    label: 'wcapi › Order Detail + Lines',
    method: 'GET',
    url: '/wcapi/order/1/',
    body: {},
    info: {
      description: 'Order detail with embedded line items under data.related.*_lines.',
      requires: { query: ['model_name', 'id'] },
      notes: ['No separate call needed for order lines.'],
    },
  },
  {
    label: 'wcapi › Invoice Detail + Lines',
    method: 'GET',
    url: '/wcapi/invoice/21/',
    body: {},
    info: {
      description: 'Invoice detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Quote Detail + Lines',
    method: 'GET',
    url: '/wcapi/quote/1/',
    body: {},
    info: {
      description: 'Quote detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Purchase Detail + Lines',
    method: 'GET',
    url: '/wcapi/purchase/1/',
    body: {},
    info: {
      description: 'Purchase detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },

  // ── WCAPI: Save ────────────────────────────────────────────────────────
  {
    label: 'wcapi › Save (PUT /wcapi/<model>/<id>/)',
    method: 'PUT',
    url: '/wcapi/contact/1/',
    body: { name_first: 'Alice' },
    info: {
      description: 'Create or update a record depending on presence of id.',
      requires: { body: ['fields…'] },
      notes: ['Include id to update; omit id to create.', 'Field validation depends on model.'],
      example: { id: 1, name: 'Alice' },
    },
  },

];

const colBase = 'h-[calc(100vh-140px)] overflow-auto border border-gray-200 rounded-md bg-white';

const WhitelistTester: React.FC = () => {
  const [method, setMethod] = useState<HttpMethod>('GET');
  const [url, setUrl] = useState<string>('/wcapi/_model_list/');
  const [body, setBody] = useState<string>('{}');
  const [headers, setHeaders] = useState<string>('{}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<any>(null);

  const parsedBody = useMemo(() => {
    try { return JSON.parse(body || '{}'); } catch { return null; }
  }, [body]);
  const parsedHeaders = useMemo(() => {
    try { return JSON.parse(headers || '{}'); } catch { return null; }
  }, [headers]);

  const applyPreset = (idx: number) => {
    const p = PRESETS[idx];
    setMethod(p.method);
    setUrl(p.url);
    setBody(JSON.stringify(p.body, null, 2));
  };

  const send = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
  const config = { headers: parsedHeaders || undefined } as any;
  const isAuthPath = url.startsWith('/auth/') || url.startsWith('/api/auth/') || url.startsWith('/api/token');
  const client = isAuthPath ? authClient : apiClient;
      const res = method === 'GET'
        ? await client.get(url, config)
        : await client.post(url, parsedBody ?? {}, config);
      setResponse(res.data);
    } catch (e: any) {
      setError(e?.message || 'Request failed');
      setResponse(e?.response?.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Whitelist Tester</h1>
      <div className="grid grid-cols-12 gap-4">
        <div className={`col-span-12 md:col-span-3 ${colBase}`}>
          <div className="p-3 border-b text-sm font-medium bg-gray-50">Presets</div>
          <ul className="p-3 space-y-2">
            {PRESETS.map((p, i) => (
              <li key={i}>
                <button className="w-full text-left px-2 py-1 text-sm rounded border hover:bg-gray-100" onClick={() => applyPreset(i)}>
                  {p.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className={`col-span-12 md:col-span-9 ${colBase}`}>
          <div className="p-3 border-b text-sm font-medium bg-gray-50 flex items-center gap-2">
            <select className="border rounded px-2 py-1 text-sm" value={method} onChange={(e) => setMethod(e.target.value as HttpMethod)}>
              <option>GET</option>
              <option>POST</option>
            </select>
            <input className="flex-1 border rounded px-2 py-1 text-sm" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="/wcapi/..." />
            <button className="px-3 py-1 text-sm rounded border hover:bg-gray-100" onClick={send} disabled={loading}>
              {loading ? 'Sending…' : 'Send'}
            </button>
          </div>
          {/* Endpoint info */}
          <div className="p-3 border-b">
            {(() => {
              const p = PRESETS.find((x) => x.method === method && url.startsWith(x.url.split('?')[0]));
              if (!p) return null;
              return (
                <div className="text-xs">
                  <div className="font-semibold mb-1">About this endpoint</div>
                  <div className="mb-1 text-gray-700">{p.info.description}</div>
                  {p.info.requires && (
                    <div className="mb-1">
                      {p.info.requires.query && p.info.requires.query.length > 0 && (
                        <div><span className="font-medium">Query:</span> {p.info.requires.query.join(', ')}</div>
                      )}
                      {p.info.requires.body && p.info.requires.body.length > 0 && (
                        <div><span className="font-medium">Body:</span> {p.info.requires.body.join(', ')}</div>
                      )}
                      {p.info.requires.headers && p.info.requires.headers.length > 0 && (
                        <div><span className="font-medium">Headers:</span> {p.info.requires.headers.join(', ')}</div>
                      )}
                    </div>
                  )}
                  {p.info.notes && p.info.notes.length > 0 && (
                    <ul className="list-disc pl-5 text-gray-600">
                      {p.info.notes.map((n, i) => (<li key={i}>{n}</li>))}
                    </ul>
                  )}
                  {p.info.example && (
                    <div className="mt-2">
                      <div className="font-medium">Example body</div>
                      <pre className="bg-gray-50 border rounded p-2 overflow-auto">{JSON.stringify(p.info.example, null, 2)}</pre>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
          <div className="grid grid-cols-2 gap-3 p-3">
            <div>
              <div className="text-xs font-semibold mb-1">Headers (JSON)</div>
              <textarea className="w-full h-40 border rounded p-2 font-mono text-xs" value={headers} onChange={(e) => setHeaders(e.target.value)} />
            </div>
            <div>
              <div className="text-xs font-semibold mb-1">Body (JSON)</div>
              <textarea className="w-full h-40 border rounded p-2 font-mono text-xs" value={body} onChange={(e) => setBody(e.target.value)} disabled={method === 'GET'} />
            </div>
          </div>
          <div className="p-3 border-t">
            {error && <div className="text-sm text-red-600 mb-2">{error}</div>}
            <div className="text-xs font-semibold mb-1">Response</div>
            <pre className="w-full h-64 border rounded p-2 font-mono text-xs overflow-auto bg-gray-50">{response ? JSON.stringify(response, null, 2) : 'No response yet.'}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WhitelistTester;
