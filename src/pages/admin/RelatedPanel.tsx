/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane | WhoCreated: Bill+Claude */
import React from 'react';
import { getRecords } from '../../api/wcapi';
import { PanelTable } from '../../apps/common/components/panels/PanelTable';
import { buildColumnsFromSpecs, buildColumnsFromRecord } from '../../apps/common/components/panels/panelColumnUtils';

// Common FK patterns: model_id, contact_id, or refs__links__model_id
// FK_PATTERNS: parent_model → { child_model: django_fk_field_name }
// Audited 2026-08-11 against Django model ForeignKey definitions.
// The fallback in getFilterKey is `${parentModel}_id` — only entries
// where the FK field name differs from that convention need to be here.
export const FK_PATTERNS: Record<string, Record<string, string>> = {
  contact: {
    email: 'contact', phone: 'contact', address: 'contact', domain: 'contact',
    action: 'refs__links__contact_id', document: 'refs__links__contact_id',
    question_answer: 'refs__links__contact_id',
    order: 'contact_id', invoice: 'contact_id', proposal: 'contact_id',
    purchase: 'contact_id', workorder: 'contact_id', payment: 'contact_id',
  },
  // OrgBase proxies — customer/vendor/manufacturer/rep all use orgbase FKs
  customer: {
    order: 'customer_id', invoice: 'customer_id', proposal: 'customer_id',
    purchase: 'customer_id', workorder: 'customer_id', payment: 'customer_id',
    contact: 'customer_id',
  },
  vendor: {
    purchase: 'vendor_id', invoice: 'vendor_id', order: 'vendor_id',
    item: 'vendor_id', payment: 'vendor_id', contact: 'vendor_id',
  },
  manufacturer: {
    item: 'manufacturer_id', invoice: 'manufacturer_id', order: 'manufacturer_id',
    proposal: 'manufacturer_id', purchase: 'manufacturer_id', contact: 'manufacturer_id',
  },
  // Transaction parents
  order: { order_line: 'order_id', document: 'refs__links__order_id', action: 'refs__links__order_id' },
  invoice: { invoice_line: 'invoice_id', payment: 'invoice_id', ledger: 'invoice_id', document: 'refs__links__invoice_id' },
  proposal: { proposal_line: 'proposal_id', document: 'refs__links__proposal_id' },
  purchase: { purchase_line: 'purchase_id', receipt: 'purchase_id', payment: 'purchase_id', document: 'refs__links__purchase_id' },
  workorder: { workorder_line: 'workorder_id', receipt: 'workorder_id' },
  receipt: { receipt_line: 'receipt_id' },
  // Products
  item: {
    serial: 'item_id', item_xref: 'item_id', org_item: 'item_id',
    bill_of_material: 'parent_item', variant: 'item_id', service: 'item_id',
    specification: 'item_id', catalog_line: 'item_id',
  },
  serial: { serial_log: 'serial_id' },
  catalog: { catalog_line: 'catalog_id', org_item: 'catalog_id' },
  // Inventory
  warehouse: { inventory_layer: 'warehouse_id' },
  payment: { payment_application: 'payment_id' },
};

export function getFilterKey(parentModel: string, relatedModel: string): string {
  return FK_PATTERNS[parentModel]?.[relatedModel] || `${parentModel}_id`;
}

/**
 * RelatedPanel — shows FK-linked or refs.links-linked child records.
 *
 * Resolution order:
 *   1. FK_PATTERNS explicit entry → use that field name as filter key
 *   2. Fallback `${parentModel}_id` → try as FK filter
 *
 * Columns come from the child model's workbench_fields Setting (db.panel),
 * falling back to auto-detection from the first record's keys.
 * Renders via PanelTable for unified column config and styling.
 */
export function RelatedPanel({ modelName, parentModel, parentId, fontSize, theme }: {
  modelName: string; parentModel: string; parentId: number;
  fontSize: number; theme: any;
}) {
  const [records, setRecords] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [collapsed, setCollapsed] = React.useState(false);
  const [linkType, setLinkType] = React.useState<'fk' | 'refs'>('fk');
  const [panelSpecs, setPanelSpecs] = React.useState<any[] | null>(null);

  // Fetch records + child model's db.panel column specs
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        // 1. Fetch records via FK filter
        const filterKey = getFilterKey(parentModel, modelName);
        const isRefsFilter = filterKey.startsWith('refs__');
        const params: Record<string, any> = { [filterKey]: parentId, limit: 50 };
        const res = await getRecords(modelName, params) as any;
        if (cancelled) return;
        const list = res?.results || [];
        setLinkType(isRefsFilter ? 'refs' : 'fk');
        setRecords(list);

        // 2. Fetch child model's workbench_fields Setting for db.panel
        try {
          const wsRes = await getRecords('setting', { parent_model: modelName, purpose: 'wc:workbench_fields', limit: 1 }) as any;
          if (cancelled) return;
          const wsRec = (wsRes?.results || [])[0];
          const dbLayout = wsRec?.config?.db || wsRec?.config;
          if (dbLayout?.panel?.length) setPanelSpecs(dbLayout.panel);
        } catch { /* no setting — auto-detect will handle it */ }
      } catch (e) {
        console.error(`[RelatedPanel] ${modelName}:`, e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [modelName, parentModel, parentId]);

  // Build PanelColumnDef from db.panel specs or auto-detect from data
  const panelColumns = React.useMemo(() => {
    if (panelSpecs?.length) return buildColumnsFromSpecs(panelSpecs);
    if (records.length > 0) return buildColumnsFromRecord(records[0]);
    return [];
  }, [panelSpecs, records]);

  return (
    <div className="border-t border-slate-200 dark:border-slate-700 mt-1">
      <div
        className="flex items-center gap-1.5 px-2 py-1.5 cursor-pointer select-none"
        onClick={() => setCollapsed(!collapsed)}
      >
        <span className="text-[10px] text-slate-400 dark:text-slate-500">{collapsed ? '▶' : '▼'}</span>
        <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
          {modelName.replace(/_/g, ' ')}
        </span>
        <span className="text-[10px] text-slate-400 dark:text-slate-500">({records.length})</span>
        {linkType === 'refs' && records.length > 0 && (
          <span className="text-[9px] text-slate-400 italic" title="Linked via refs.links (soft link)">refs</span>
        )}
        {loading && <span className="text-[10px] text-slate-400">loading...</span>}
      </div>
      {!collapsed && records.length > 0 && panelColumns.length > 0 && (
        <div className="px-1 pb-2">
          <PanelTable
            storageKey={`panel:${parentModel}:${modelName}`}
            columns={panelColumns}
            data={records}
            rowKey={(r: any) => r.id ?? r.uuid ?? Math.random()}
            compact
          />
        </div>
      )}
      {!collapsed && !loading && records.length === 0 && (
        <div className="px-2 pb-2 text-[10px] text-slate-400 dark:text-slate-500">
          No {modelName.replace(/_/g, ' ')} records
        </div>
      )}
    </div>
  );
}

export default RelatedPanel;
