/* LastChecked: 2026-08-21 | WhereUsed: ModelDetailPage | WhoCreated: Bill+Claude */
/**
 * panelRegistry — Maps tab content names to panel components.
 *
 * Each entry receives a standard PanelContext and returns a ReactElement.
 * Models declare their tabs in layout JSON; the registry resolves the component.
 * Add new panels here — no switch statements in detail pages.
 */
import type { ReactElement } from 'react';
import type { ChannelDef } from '@/apps/common/components/panels/CommentsPanel';

// ── Standard context passed to every panel ──
export interface PanelContext {
  modelName: string;
  recordId: number;
  data: any;
  isEditing: boolean;
  onFieldChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  ensureWindow: (path: string, title: string) => void;
  /** Section config from the layout Setting JSON */
  sectionConfig?: { channels?: ChannelDef[]; [key: string]: unknown };
}

type PanelRenderer = (ctx: PanelContext) => ReactElement;

// ── Lazy imports — panels load on first tab click ──
import { lazy, Suspense, createElement } from 'react';
import { getInventoryLayers } from '@/api/workorderApi';
import { formatCurrency } from '@/utils/stringUtils';

const CommPanel = lazy(() => import('@/apps/communications/components/CommPanel'));
const LinkedRecordsPanel = lazy(() => import('@/apps/common/components/panels/LinkedRecordsPanel').then(m => ({ default: m.LinkedRecordsPanel })));
const CommentsPanel = lazy(() => import('@/apps/common/components/panels/CommentsPanel'));
const FinancialsPanel = lazy(() => import('@/apps/common/components/panels/FinancialsPanel'));
const OrgFinancialsPanel = lazy(() => import('@/apps/orgs/components/OrgFinancialsPanel'));
const TransactionsPanel = lazy(() => import('@/apps/common/components/panels/TransactionsPanel'));
const ProjectKanbanPanel = lazy(() => import('@/apps/common/components/panels/ProjectKanbanPanel'));
const ProjectGanttPanel = lazy(() => import('@/apps/common/components/panels/ProjectGanttPanel'));
const ProjectActionGantt = lazy(() => import('@/apps/common/components/panels/ProjectActionGantt'));
const BomPanel = lazy(() => import('@/apps/products/components/BomPanel'));
const CatalogLinesPanel = lazy(() => import('@/apps/products/components/CatalogLinesPanel'));
const CycleCountPanel = lazy(() => import('@/apps/products/components/CycleCountPanel'));
const DataGrid = lazy(() => import('@/components/common/DataGrid'));
const DbColumns = lazy(() => import('@/apps/common/components/panels/DbColumns').then(m => ({ default: m.DbColumns })));
const LazyTimeClockWidget = lazy(() => import('@/components/widgets/TimeClockWidget').then(m => ({ default: m.TimeClockWidget })));
const LazyBillableWidget = lazy(() => import('@/components/widgets/BillableWidget').then(m => ({ default: m.BillableWidget })));
const LazyFileUploadPanel = lazy(() => import('@/components/common/FileUploadPanel'));

const fallback = createElement('div', { className: 'p-4 text-xs text-slate-400' }, 'Loading...');
const wrap = (el: ReactElement) => createElement(Suspense, { fallback }, el);
const placeholder = (label: string) => createElement('div', { className: 'p-4 text-xs text-slate-400' }, `${label} — coming soon`);

// ── Registry ──

const registry: Record<string, PanelRenderer> = {
  // === Common panels (all models) ===
  // A record's actions are those it lists in refs.links.action; each lists the record back
  // (two-sided links, Bill 2026-10-31). One panel code for every list.
  actions: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'action', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  // A record's documents are those it lists in refs.links.document, each listing it back; the
  // upload under the rows makes the document and adds it there.
  documents: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'document', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  }, createElement(LazyFileUploadPanel, { modelName: ctx.modelName, recordId: ctx.recordId, recordIda: ctx.data?.ida, className: 'px-3 py-1' }))),

  notes: (ctx) => wrap(createElement(CommentsPanel, {
    entityType: ctx.modelName,
    entityId: ctx.data.id,
    comments: ctx.data.comments,
    isEditing: ctx.isEditing,
    channels: ctx.sectionConfig?.channels,
    onChange: (comments: any) => ctx.onFieldChange('comments', comments),
    onSave: async (comments: any) => {
      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord(ctx.modelName, { id: ctx.data.id, comments: { mode: 'update', value: comments } });
    },
  })),

  comments: (ctx) => wrap(createElement(CommentsPanel, {
    entityType: ctx.modelName,
    entityId: ctx.data.id,
    comments: ctx.data.comments,
    isEditing: ctx.isEditing,
    channels: ctx.sectionConfig?.channels,
    onChange: (comments: any) => ctx.onFieldChange('comments', comments),
    onSave: async (comments: any) => {
      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord(ctx.modelName, { id: ctx.data.id, comments: { mode: 'update', value: comments } });
    },
  })),

  // === Contact panels ===
  communications: (ctx) => {
    const contactId = ctx.modelName === 'contact' ? ctx.data.id : ctx.data.contact_id;
    const source = ctx.modelName === 'contact' ? ctx.data : (ctx.data._contact || ctx.data);
    if (!contactId) return placeholder('No contact linked');
    return wrap(createElement(CommPanel, {
      contactId,
      emails: source.refs?.links?.email || [],
      phones: source.refs?.links?.phone || [],
      addresses: source.refs?.links?.address || [],
      domains: source.refs?.links?.domain || [],
      onRefresh: ctx.onRefresh,
    }));
  },

  kanban: (ctx) => {
    const contactId = ctx.modelName === 'contact' ? ctx.data.id : ctx.data.contact_id;
    if (!contactId) return placeholder('No contact linked');
    return wrap(createElement(ProjectKanbanPanel, { contactId }));
  },

  gantt: (ctx) => {
    // For projects: show action-level Gantt with dependencies + critical path
    if (ctx.modelName === 'project' || ctx.modelName === 'tx_projects') {
      return wrap(createElement(ProjectActionGantt, { projectId: ctx.data.id }));
    }
    // For contacts: show project-level timeline
    const contactId = ctx.modelName === 'contact' ? ctx.data.id : ctx.data.contact_id;
    if (!contactId) return placeholder('No contact linked');
    return wrap(createElement(ProjectGanttPanel, { contactId }));
  },

  // === Linked record panels — all use LinkedRecordsPanel for consistent db.panel behavior ===
  contacts: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'contact', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  // An org's documents by their own customer / vendor / rep field — never a copy on the org.
  transactions: (ctx) => wrap(createElement(TransactionsPanel, {
    orgId: ctx.data?.id, orgType: ctx.data?.org_type || ctx.modelName,
  })),

  purchases: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'purchase', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  organizations: (ctx) => {
    const orgData = [
      ...(ctx.data.refs?.links?.customer ? [{ type: 'Customer', ...ctx.data.refs.links.customer }] : []),
      ...(ctx.data.refs?.links?.vendor ? [{ type: 'Vendor', ...ctx.data.refs.links.vendor }] : []),
    ];
    return wrap(createElement(DbColumns, {
      storageKey: `panel:${ctx.modelName}:organizations`,
      columns: [
        { key: 'type', label: 'type', width: '80px', className: 'font-semibold text-slate-600 dark:text-slate-300', render: (r: any) => String(r.type ?? '—') },
        { key: 'company', label: 'company', className: 'text-slate-800 dark:text-slate-200', render: (r: any) => String(r.company ?? r.name ?? '—') },
        { key: 'ida', label: 'ida', width: '70px', className: 'font-mono text-slate-500 dark:text-slate-400', render: (r: any) => String(r.ida ?? '—') },
      ],
      data: orgData,
      rowKey: (r: any) => `${r.type}-${r.id ?? r.ida}`,
      compact: true,
    }));
  },

  // === Item panels ===
  bom: (ctx) => wrap(createElement(BomPanel, {
    itemId: ctx.data.id,
    itemCode: ctx.data.ida || ctx.data.item_code || `#${ctx.data.id}`,
  })),

  catalog_lines: (ctx) => wrap(createElement(CatalogLinesPanel, { catalogId: ctx.data.id })),

  // An item's serials, cross references and specifications: the records whose item_id is the
  // item — the shared list, columns from each model's layout.panel.
  serials: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'serial', parentModel: ctx.modelName, parentId: ctx.data?.id, byField: 'item_id',
    chipField: 'status', title: 'Serials', defaultCollapsed: false,
  })),

  xref: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'item_xref', parentModel: ctx.modelName, parentId: ctx.data?.id, byField: 'item_id',
    title: 'Cross references', defaultCollapsed: false,
  })),

  specs: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'specification', parentModel: ctx.modelName, parentId: ctx.data?.id, byField: 'item_id',
    title: 'Specifications', defaultCollapsed: false,
  })),

  // An item's cost layers from the inventory service view (it computes what remains), by warehouse.
  layers: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'inventory_layer', parentModel: ctx.modelName, parentId: ctx.data?.id, byField: 'item_id',
    read: getInventoryLayers, editable: false, title: 'Inventory layers', defaultCollapsed: false,
    groupBy: (l: any) => l.warehouse_name || l.warehouse_code || 'Default',
    // Sums of the server's per-layer values; the view has no per-warehouse total.
    groupSummary: (rows: any[]) => `${rows.reduce((s, l) => s + Number(l.remaining || 0), 0)} units | ${
      formatCurrency(rows.reduce((s, l) => s + Number(l.remaining || 0) * Number(l.landed || 0), 0))} value`,
  })),

  counts: (ctx) => wrap(createElement(CycleCountPanel, { itemId: ctx.data.id })),

  // === Action panels ===
  touches: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'touch', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  linked_action: (ctx) => {
    // Touch's parent action
    const actionId = ctx.data.action_id || ctx.data.refs?.parents?.action;
    if (!actionId) return placeholder('No action linked');
    return wrap(createElement(DataGrid, {
      records: [{ id: actionId, action: ctx.data._action_title || `Action #${actionId}` }],
      columns: ['id', 'action'],
      sort: null,
      onSort: () => {},
      onSelectRecord: (id: any) => ctx.ensureWindow(`/action/${id}`, `Action #${id}`),
      fontSize: 11,
    }));
  },

  linked_contact: (ctx) => {
    const contactId = ctx.data.contact_id;
    if (!contactId) return placeholder('No contact linked');
    return wrap(createElement(DataGrid, {
      records: [{ id: contactId, name: ctx.data._contact_name || `Contact #${contactId}` }],
      columns: ['id', 'name'],
      sort: null,
      onSort: () => {},
      onSelectRecord: (id: any) => ctx.ensureWindow(`/contact/${id}`, `Contact #${id}`),
      fontSize: 11,
    }));
  },

  // === Placeholders ===
  // === Communication panels (contact model) ===
  phone: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'phone', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),
  email: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'email', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),
  domain: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'domain', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),
  address: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'address', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  // === Combined billing panel (times entries + billable fields) ===
  billing: (ctx) => {
    const timesEl = createElement(LazyTimeClockWidget, {
      name: 'config.times',
      value: ctx.data?.config?.times ?? { entries: [] },
      onChange: (v: any) => {
        ctx.onFieldChange('config.times', v);
        import('@/api/wcapi').then(({ saveRecord }) => {
          const config = { ...(ctx.data.config || {}), times: v };
          saveRecord('action', { id: ctx.data.id, config: { mode: 'update', value: config } }).catch(() => {});
        });
      },
      disabled: false,
      record: ctx.data,
    });
    const billableEl = createElement(LazyBillableWidget, {
      name: 'config.billable',
      value: ctx.data?.config?.billable ?? { is_billable: true, rate_unit: 'hour', currency: 'USD' },
      onChange: (v: any) => ctx.onFieldChange('config.billable', v),
      disabled: false,
      record: ctx.data,
    });
    return wrap(createElement('div', { className: 'space-y-2' }, timesEl, billableEl));
  },

  // Legacy aliases — point to combined billing panel
  times: (ctx) => registry.billing(ctx),
  billable: (ctx) => registry.billing(ctx),

  files: (ctx) => wrap(createElement(LazyFileUploadPanel, {
    modelName: ctx.modelName,
    recordId: ctx.recordId,
    recordIda: ctx.data?.ida,
  })),

  financials: (ctx) => {
    // Org models have ctx.data.financial; transaction models have ctx.data.totals
    if (ctx.data.financial) {
      return wrap(createElement(OrgFinancialsPanel, {
        financial: ctx.data.financial,
        orgType: ctx.data.org_type,
        orgTypes: ctx.data.org_types,
        currency: ctx.data.currency,
      }));
    }
    return wrap(createElement(FinancialsPanel, {
      totals: ctx.data.totals,
      currency: ctx.data.currency,
    }));
  },

  org_financials: (ctx) => wrap(createElement(OrgFinancialsPanel, {
    financial: ctx.data.financial,
    orgType: ctx.data.org_type,
    orgTypes: ctx.data.org_types,
    currency: ctx.data.currency,
  })),

  summary: () => placeholder('Summary'),
  history: () => placeholder('Transaction history'),
  qa: () => placeholder('QA panel'),
  link: () => placeholder('Link picker — select a model to link'),
};

// ── Public API ──

export function renderPanel(content: string, ctx: PanelContext): ReactElement {
  const renderer = registry[content];
  if (!renderer) return placeholder(`Unknown panel: ${content}`);
  return renderer(ctx);
}

/** Register a custom panel at runtime (e.g., from a plugin) */
export function registerPanel(content: string, renderer: PanelRenderer): void {
  registry[content] = renderer;
}

// Tab declarations live in wc:model Settings (config.layout.form.default → tabs section).
// seed_layouts writes them (apps/core/layouts). No hardcoded tab config here.
