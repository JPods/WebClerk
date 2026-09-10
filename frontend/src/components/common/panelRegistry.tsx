/* LastChecked: 2026-08-21 | WhereUsed: ModelDetailPage | WhoCreated: Bill+Claude */
/**
 * panelRegistry — Maps tab content names to panel components.
 *
 * Each entry receives a standard PanelContext and returns a ReactElement.
 * Models declare their tabs in layout JSON; the registry resolves the component.
 * Add new panels here — no switch statements in detail pages.
 */
import type { ReactElement } from 'react';

// ── Standard context passed to every panel ──
export interface PanelContext {
  modelName: string;
  recordId: number;
  data: any;
  isEditing: boolean;
  onFieldChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  ensureWindow: (path: string, title: string) => void;
}

type PanelRenderer = (ctx: PanelContext) => ReactElement;

// ── Lazy imports — panels load on first tab click ──
import { lazy, Suspense, createElement } from 'react';

const CommPanel = lazy(() => import('@/apps/communications/components/CommPanel'));
const ActionsPanel = lazy(() => import('@/apps/common/components/panels/ActionsPanel'));
const DocumentsPanel = lazy(() => import('@/apps/common/components/panels/DocumentsPanel'));
const LinkedRecordsPanel = lazy(() => import('@/apps/common/components/panels/LinkedRecordsPanel').then(m => ({ default: m.LinkedRecordsPanel })));
const CommentsPanel = lazy(() => import('@/apps/common/components/panels/CommentsPanel'));
const ProjectKanbanPanel = lazy(() => import('@/apps/common/components/panels/ProjectKanbanPanel'));
const ProjectGanttPanel = lazy(() => import('@/apps/common/components/panels/ProjectGanttPanel'));
const ProjectActionGantt = lazy(() => import('@/apps/common/components/panels/ProjectActionGantt'));
const BomPanel = lazy(() => import('@/apps/products/components/BomPanel'));
const SerialPanel = lazy(() => import('@/apps/products/components/SerialPanel'));
const ProductListPanel = lazy(() => import('@/apps/products/components/ProductListPanel'));
const InventoryLayersPanel = lazy(() => import('@/apps/products/components/InventoryLayersPanel'));
const CycleCountPanel = lazy(() => import('@/apps/products/components/CycleCountPanel'));
const XRefCard = lazy(() => import('@/apps/products/components/XRefCard'));
const SpecCard = lazy(() => import('@/apps/products/components/SpecCard'));
const DataGrid = lazy(() => import('@/components/common/DataGrid'));
const PanelTable = lazy(() => import('@/apps/common/components/panels/PanelTable').then(m => ({ default: m.PanelTable })));
const PanelSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/PanelSectionRenderer'));
const JsonSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/JsonSectionRenderer'));
const LazyTimeClockWidget = lazy(() => import('@/components/widgets/TimeClockWidget').then(m => ({ default: m.TimeClockWidget })));
const LazyBillableWidget = lazy(() => import('@/components/widgets/BillableWidget').then(m => ({ default: m.BillableWidget })));
const LazyFileUploadPanel = lazy(() => import('@/components/common/FileUploadPanel'));

const fallback = createElement('div', { className: 'p-4 text-xs text-slate-400' }, 'Loading...');
const wrap = (el: ReactElement) => createElement(Suspense, { fallback }, el);
const placeholder = (label: string) => createElement('div', { className: 'p-4 text-xs text-slate-400' }, `${label} — coming soon`);

// ── Registry ──

const registry: Record<string, PanelRenderer> = {
  // === Common panels (all models) ===
  actions: (ctx) => wrap(createElement(ActionsPanel, {
    entityType: ctx.modelName,
    entityId: ctx.data.id,
    data: ctx.data.actions?.items || [],
    isEditing: ctx.isEditing,
  })),

  documents: (ctx) => wrap(createElement(DocumentsPanel, {
    parent_model: ctx.modelName,
    parentId: ctx.data.id,
    data: ctx.data.refs?.links?.document,
    isEditing: ctx.isEditing,
  })),

  notes: (ctx) => wrap(createElement(CommentsPanel, {
    entityType: ctx.modelName,
    entityId: ctx.data.id,
    data: ctx.data.comments,
    isEditing: ctx.isEditing,
    onChange: (comments: any) => ctx.onFieldChange('comments', comments),
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
      return wrap(createElement(ProjectActionGantt, {
        projectId: ctx.data.id,
        projectName: ctx.data.name,
      }));
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

  transactions: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'order', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  purchases: (ctx) => wrap(createElement(LinkedRecordsPanel, {
    linkedModel: 'purchase', parentModel: ctx.modelName, parentId: ctx.data?.id, defaultCollapsed: false,
  })),

  organizations: (ctx) => {
    const orgData = [
      ...(ctx.data.refs?.links?.customer ? [{ type: 'Customer', ...ctx.data.refs.links.customer }] : []),
      ...(ctx.data.refs?.links?.vendor ? [{ type: 'Vendor', ...ctx.data.refs.links.vendor }] : []),
    ];
    return wrap(createElement(PanelTable, {
      storageKey: `panel:${ctx.modelName}:organizations`,
      columns: [
        { key: 'type', label: 'type', cellClassName: 'w-[80px] font-semibold text-slate-600 dark:text-slate-300', render: (r: any) => String(r.type ?? '—') },
        { key: 'company', label: 'company', cellClassName: 'min-w-[120px] flex-1 text-slate-800 dark:text-slate-200', render: (r: any) => String(r.company ?? r.name ?? '—') },
        { key: 'ida', label: 'ida', cellClassName: 'w-[70px] font-mono text-slate-500 dark:text-slate-400', render: (r: any) => String(r.ida ?? '—') },
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

  serials: (ctx) => wrap(createElement(SerialPanel, {
    itemId: ctx.data.id,
    itemCode: ctx.data.ida || ctx.data.item_code || `#${ctx.data.id}`,
  })),

  xref: (ctx) => wrap(createElement(ProductListPanel, {
    model: 'item_xref',
    itemId: ctx.data.id,
    itemCode: ctx.data.ida || ctx.data.item_code || `#${ctx.data.id}`,
    filterField: 'item_id',
    CardComponent: XRefCard,
    headers: ['Type', 'XRef Code', 'Description', 'Org'],
    headerWidths: ['w-16', 'w-28', 'flex-1', 'w-20'],
    onCardClick: (id: any) => ctx.ensureWindow(`/item_xref?id=${id}`, `XRef #${id}`),
  })),

  specs: (ctx) => wrap(createElement(ProductListPanel, {
    model: 'specification',
    itemId: ctx.data.id,
    itemCode: ctx.data.ida || ctx.data.item_code || `#${ctx.data.id}`,
    filterField: 'item_id',
    CardComponent: SpecCard,
    headers: ['Name', 'Value', 'Unit', 'Category'],
    headerWidths: ['w-32', 'w-24', 'w-16', 'flex-1'],
  })),

  layers: (ctx) => wrap(createElement(InventoryLayersPanel, { itemId: ctx.data.id })),

  counts: (ctx) => wrap(createElement(CycleCountPanel, {
    itemId: ctx.data.id,
    itemCode: ctx.data.ida || ctx.data.item_code || `#${ctx.data.id}`,
  })),

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
// The seed script (seed_detail_layouts) writes them. No hardcoded tab config here.
