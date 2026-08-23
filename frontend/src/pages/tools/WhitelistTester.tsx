/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Whitelist Tester — interactive API endpoint tester.
 *
 * Presets cover both the wcapi gateway and legacy REST paths that
 * are 301-redirected by RestToWcapiMiddleware on the backend.
 *
 * Related files:
 *   wc3  common/middleware/rest_redirect.py      — server-side REST→wcapi redirect middleware
 *   wc3  tests/test_rest_redirect.py              — 46 middleware tests
 *   wc3  readmes/03-wcapi-gateway.md              — gateway overview & mapping table
 *   r25  src/api/restToWcapi.ts                   — client-side REST→wcapi converter
 *   r25  src/api/modelNameResolver.ts              — canonical model-name resolution
 *   r25  readmes/api-migration-rest-to-wcapi.md   — migration tracker
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
    url: '/wcapi/model_name/list/',
    body: {},
    info: {
      description: 'Returns whitelisted model names from registry.',
      notes: ['No params required.', 'Used by Admin Workbench left pane.'],
    },
  },
  {
    label: 'Choice Catalog (GET)',
    method: 'GET',
    url: '/wcapi/choices/',
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
    url: '/wcapi/model_name/detail/?model_name=contact',
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
    url: '/wcapi/get/?model_name=contact&limit=10',
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
    url: '/wcapi/get/?model_name=contact&id=1',
    body: {},
    info: {
      description: 'Single contact by ID via wcapi.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Customer List',
    method: 'GET',
    url: '/wcapi/get/?model_name=customer&limit=10',
    body: {},
    info: {
      description: 'List customers via wcapi gateway.',
      requires: { query: ['model_name'] },
    },
  },
  {
    label: 'wcapi › Vendor List',
    method: 'GET',
    url: '/wcapi/get/?model_name=vendor&limit=10',
    body: {},
    info: {
      description: 'List vendors via wcapi gateway.',
      requires: { query: ['model_name'] },
    },
  },
  {
    label: 'wcapi › Item List',
    method: 'GET',
    url: '/wcapi/get/?model_name=item&limit=10',
    body: {},
    info: {
      description: 'List items (canonical product model).',
      requires: { query: ['model_name'] },
      notes: ['Prefer item over org_item. org_item is an association (org↔item).'],
    },
  },
  {
    label: 'wcapi › Order Detail + Lines',
    method: 'GET',
    url: '/wcapi/get/?model_name=order&id=1',
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
    url: '/wcapi/get/?model_name=invoice&id=21',
    body: {},
    info: {
      description: 'Invoice detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Proposal Detail + Lines',
    method: 'GET',
    url: '/wcapi/get/?model_name=proposal&id=1',
    body: {},
    info: {
      description: 'Proposal detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },
  {
    label: 'wcapi › Purchase Detail + Lines',
    method: 'GET',
    url: '/wcapi/get/?model_name=purchase&id=1',
    body: {},
    info: {
      description: 'Purchase detail with embedded line items.',
      requires: { query: ['model_name', 'id'] },
    },
  },

  // ── WCAPI: Save ────────────────────────────────────────────────────────
  {
    label: 'wcapi › Save (POST)',
    method: 'POST',
    url: '/wcapi/save/',
    body: { model_name: 'contact', id: 1 },
    info: {
      description: 'Create or update a record depending on presence of id.',
      requires: { body: ['model_name', 'fields…'] },
      notes: ['Include id to update; omit id to create.', 'Field validation depends on model.'],
      example: { model_name: 'contact', id: 1, name: 'Alice' },
    },
  },

  // ── REST → wcapi redirect tests ───────────────────────────────────────
  // These legacy REST paths are intercepted by RestToWcapiMiddleware
  // and 301-redirected to the equivalent wcapi endpoint.
  {
    label: 'REST › /api/contacts/',
    method: 'GET',
    url: '/api/contacts/',
    body: {},
    info: {
      description: 'Legacy REST list → redirects to /wcapi/get/?model_name=contact',
      notes: [
        'RestToWcapiMiddleware strips /api/, singularises "contacts" → "contact".',
        'Expect 301 redirect (axios follows automatically).',
      ],
    },
  },
  {
    label: 'REST › /api/contacts/1/',
    method: 'GET',
    url: '/api/contacts/1/',
    body: {},
    info: {
      description: 'Legacy REST detail → redirects to /wcapi/get/?model_name=contact&id=1',
      notes: ['Extracts numeric ID from path.'],
    },
  },
  {
    label: 'REST › /api/customers/',
    method: 'GET',
    url: '/api/customers/',
    body: {},
    info: {
      description: 'Legacy REST list → redirects to /wcapi/get/?model_name=customer',
    },
  },
  {
    label: 'REST › /api/orgs/customers/',
    method: 'GET',
    url: '/api/orgs/customers/',
    body: {},
    info: {
      description: 'App-namespaced REST → strips "orgs/" prefix, redirects to /wcapi/get/?model_name=customer',
      notes: ['Middleware strips known app prefixes (orgs, transactions, core, etc.)'],
    },
  },
  {
    label: 'REST › /api/orgs/customers/2/',
    method: 'GET',
    url: '/api/orgs/customers/2/',
    body: {},
    info: {
      description: 'App-namespaced REST detail → /wcapi/get/?model_name=customer&id=2',
    },
  },
  {
    label: 'REST › /api/invoices/',
    method: 'GET',
    url: '/api/invoices/',
    body: {},
    info: {
      description: 'REST list → redirects to /wcapi/get/?model_name=invoice',
    },
  },
  {
    label: 'REST › /api/invoices/21/',
    method: 'GET',
    url: '/api/invoices/21/',
    body: {},
    info: {
      description: 'REST detail → redirects to /wcapi/get/?model_name=invoice&id=21',
    },
  },
  {
    label: 'REST › /api/transactions/invoices/21/',
    method: 'GET',
    url: '/api/transactions/invoices/21/',
    body: {},
    info: {
      description: 'Full app-namespaced REST → /wcapi/get/?model_name=invoice&id=21',
      notes: ['Both /api/invoices/21/ and /api/transactions/invoices/21/ resolve to the same wcapi call.'],
    },
  },
  {
    label: 'REST › /api/core/contacts/list',
    method: 'GET',
    url: '/api/core/contacts/list',
    body: {},
    info: {
      description: 'REST with "core" prefix + trailing "list" action → /wcapi/get/?model_name=contact',
      notes: ['Trailing action verbs (list, detail) are stripped by the middleware.'],
    },
  },
  {
    label: 'REST › /api/transactions/orders/',
    method: 'GET',
    url: '/api/transactions/orders/',
    body: {},
    info: {
      description: 'REST orders list → redirects to /wcapi/get/?model_name=order',
    },
  },
  {
    label: 'REST › /api/transactions/orders/1/',
    method: 'GET',
    url: '/api/transactions/orders/1/',
    body: {},
    info: {
      description: 'REST order detail → redirects to /wcapi/get/?model_name=order&id=1',
    },
  },
  {
    label: 'REST › /api/vendors/',
    method: 'GET',
    url: '/api/vendors/',
    body: {},
    info: {
      description: 'REST vendor list → redirects to /wcapi/get/?model_name=vendor',
    },
  },
  {
    label: 'REST › /api/orgs/vendors/16/',
    method: 'GET',
    url: '/api/orgs/vendors/16/',
    body: {},
    info: {
      description: 'REST vendor detail → redirects to /wcapi/get/?model_name=vendor&id=16',
    },
  },
  {
    label: 'REST › /api/products/items/',
    method: 'GET',
    url: '/api/products/items/',
    body: {},
    info: {
      description: 'REST items list → redirects to /wcapi/get/?model_name=item',
    },
  },
  {
    label: 'REST › /api/products/items/1/',
    method: 'GET',
    url: '/api/products/items/1/',
    body: {},
    info: {
      description: 'REST item detail → redirects to /wcapi/get/?model_name=item&id=1',
    },
  },
  {
    label: 'REST › /api/orgs/employees/',
    method: 'GET',
    url: '/api/orgs/employees/',
    body: {},
    info: {
      description: 'REST employee list → redirects to /wcapi/get/?model_name=employee',
    },
  },
  {
    label: 'REST › /api/orgs/manufacturers/',
    method: 'GET',
    url: '/api/orgs/manufacturers/',
    body: {},
    info: {
      description: 'REST manufacturer list → redirects to /wcapi/get/?model_name=manufacturer',
    },
  },
  {
    label: 'REST › /api/transactions/proposals/',
    method: 'GET',
    url: '/api/transactions/proposals/',
    body: {},
    info: {
      description: 'REST proposal list → redirects to /wcapi/get/?model_name=proposal',
    },
  },
  {
    label: 'REST › /api/transactions/proposals/1/',
    method: 'GET',
    url: '/api/transactions/proposals/1/',
    body: {},
    info: {
      description: 'REST proposal detail → redirects to /wcapi/get/?model_name=proposal&id=1',
    },
  },
  {
    label: 'REST › /api/transactions/purchases/',
    method: 'GET',
    url: '/api/transactions/purchases/',
    body: {},
    info: {
      description: 'REST purchase list → redirects to /wcapi/get/?model_name=purchase',
    },
  },
];

const colBase = 'h-[calc(100vh-140px)] overflow-auto border border-gray-200 rounded-md bg-white';

const WhitelistTester: React.FC = () => {
  const [method, setMethod] = useState<HttpMethod>('GET');
  const [url, setUrl] = useState<string>('/wcapi/model_name/list/');
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
