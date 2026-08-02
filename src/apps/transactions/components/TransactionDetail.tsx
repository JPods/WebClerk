/* LastChecked: 2026-08-01 | WhereUsed: AdminWorkbench, Router | WhoCreated: Claude */
/**
 * TransactionDetail — JSON-driven transaction detail renderer.
 *
 * Replaces all model-specific detail .tsx files (OrderDetail, InvoiceDetail, etc.)
 * with a single component driven by a detail_layout Setting per model.
 *
 * Layout JSON defines: header fields, line card config, tabs, edit rules, actions.
 * One renderer, many configurations.
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord, getRecords, saveRecord, saveTransactionWithLines } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { useWindowManager } from '@/context/WindowManagerContext';
import {
  useDetailLayout,
  type DetailLayout,
  type HeaderSection,
  type LineCardSection,
  type TabsSection,
} from '@/hooks/useDetailLayout';
import DataGrid from '@/components/common/DataGrid';
import { useLineCard } from '@/hooks/useLineCard';
import { applyCustomerDefaults } from '@/apps/transactions/utils/applyCustomerDefaults';
import InventoryPanel from './panels/InventoryPanel';
import MarginPanel from './panels/MarginPanel';
import SpecPanel from './panels/SpecPanel';
import XRefPanel from './panels/XRefPanel';
import { lineKey, getNextLineNumber } from '../utils/lineHelpers';
import type { TransactionLine } from '../types/transactionTypes';

// Tab content components — lazy loaded
// ContactPanel replaced by inline DataGrid for db.list pattern
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import FinancialsPanel from '@/apps/common/components/panels/FinancialsPanel';
import { DocumentsPanel } from '@/apps/common/components/panels';
import RelatedTransactions from '@/components/common/RelatedTransactions';
import QATab from './QATab';
import { WcToolbar, type ToolbarButton } from '@/components/widgets/WcToolbar';
import { WcModelMenu } from '@/components/widgets/WcModelMenu';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TransactionDetailProps {
  modelName?: string;
  recordId?: number;
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransactionDetail: React.FC<TransactionDetailProps> = ({
  modelName: propModelName,
  recordId: propRecordId,
  onClose,
}) => {
  const params = useParams<{ model?: string; id?: string }>();
  const modelName = propModelName || params.model || 'order';
  const recordId = propRecordId || (params.id ? Number(params.id) : 0);

  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};
  const loggedInUserName = authUser?.name || authUser?.email || 'User';

  // ── Layout ───────────────────────────────────────────────────────
  const { layout, loading: layoutLoading } = useDetailLayout(modelName);

  // ── Record state ─────────────────────────────────────────────────
  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [custSearchOpen, setCustSearchOpen] = useState(false);
  const [custSearchQuery, setCustSearchQuery] = useState('');
  const [custSearchResults, setCustSearchResults] = useState<any[]>([]);
  const [custSearching, setCustSearching] = useState(false);

  // ── Fetch record ─────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord(modelName, recordId);
      const record = response?.record || response;

      // Fetch customer config if customer_id exists
      const custId = record?.customer_id || record?.customer;
      if (custId) {
        try {
          const custResp = await getRecord('customer', custId);
          const cust = custResp?.record || custResp;
          if (cust?.config) record.customer_config = cust.config;
          record.customer_company = cust?.company || cust?.display_name || cust?.name || '';
          if (!record.price_level && cust?.price_level) record.price_level = cust.price_level;
          if (!record.terms && cust?.terms) record.terms = cust.terms;
        } catch { /* customer not found */ }
      }

      setData(record);
      setEditData(record);
    } catch (err) {
      dispatch(showToast({ message: `Failed to load ${modelName}`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [modelName, recordId, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Edit state ───────────────────────────────────────────────────
  // Three-tier edit state: open (edit freely) → pend (changes create pending) → closed (no edit)
  const editTier = useMemo((): 'open' | 'pend' | 'closed' => {
    if (!data || !layout) return 'closed';
    const rules = layout.edit_rules as any;
    const statusField = rules.status_field || 'status';
    const status = String(data[statusField] || '').toLowerCase();

    if (rules.closed_statuses?.includes(status)) return 'closed';
    if (rules.pend_statuses?.includes(status)) return 'pend';
    if (rules.open_statuses?.includes(status)) return 'open';

    // Legacy: locked_statuses = closed
    if (rules.locked_statuses?.includes(status)) return 'closed';
    return 'open';
  }, [data, layout]);

  const canEdit = editTier !== 'closed';
  const isPendMode = editTier === 'pend';

  // Auto-edit: if user pref is set, enter edit mode when record loads
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;
  useEffect(() => {
    if (autoEdit && canEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, canEdit, data]);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleEdit = () => {
    if (canEdit) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  };

  const handleAddNew = async () => {
    try {
      const res = await saveRecord(modelName, { status: 'open' });
      const newId = res?.record?.id || res?.id;
      if (newId) {
        windowManager.ensureWindow(`/${modelName}/${newId}`, `${modelName} #${newId}`);
      }
    } catch {
      dispatch(showToast({ message: `Failed to create ${modelName}`, type: 'error' }));
    }
  };

  const handleAddLine = () => {
    const lines = (isEditing ? editData : data)?.lines || [];
    const newLine: TransactionLine = {
      line_number: getNextLineNumber(lines),
      item_code: '',
      description: '',
      qty: 1,
      remain: 1,
      unit_price: 0,
      extended: 0,
    } as any;
    handleLinesChange([...lines, newLine]);
  };

  const handleCancel = () => {
    setEditData(data);
    setIsEditing(false);
  };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      return { ...prev, [field]: value };
    });

    // When customer changes, auto-populate order fields from customer defaults
    if ((field === 'customer' || field === 'customer_id') && value) {
      const custId = typeof value === 'number' ? value : Number(value);
      if (custId > 0) {
        applyCustomerDefaults(custId).then(defaults => {
          setEditData((prev: any) => {
            if (!prev) return prev;
            return { ...prev, ...defaults };
          });
          dispatch(showToast({ message: `Customer defaults applied: ${defaults.company}`, type: 'success' }));
        }).catch(() => {
          dispatch(showToast({ message: 'Could not load customer defaults', type: 'error' }));
        });
      }
    }
  }, [dispatch]);

  // ── Customer search ──────────────────────────────────────────────
  const custSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const custSearchRef = useRef<HTMLInputElement>(null);

  const handleCustSearch = useCallback((query: string) => {
    setCustSearchQuery(query);
    if (custSearchTimer.current) clearTimeout(custSearchTimer.current);
    if (!query || query.length < 2) { setCustSearchResults([]); return; }
    custSearchTimer.current = setTimeout(async () => {
      setCustSearching(true);
      try {
        const res = await getRecords('customer', { keyword: query, limit: 10 });
        const records = res?.results || res?.records || [];
        setCustSearchResults(records);
      } catch { setCustSearchResults([]); }
      setCustSearching(false);
    }, 300);
  }, []);

  const handleCustSelect = useCallback((cust: any) => {
    // Close search immediately, then apply customer
    setCustSearchOpen(false);
    setCustSearchQuery('');
    setCustSearchResults([]);
    setTimeout(() => handleFieldChange('customer', cust.id), 0);
  }, [handleFieldChange]);

  useEffect(() => {
    if (custSearchOpen && custSearchRef.current) custSearchRef.current.focus();
  }, [custSearchOpen]);

  const handleLinesChange = useCallback((lines: TransactionLine[]) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      return { ...prev, lines };
    });
  }, []);

  const handleSave = async () => {
    if (!editData) return;
    setSaving(true);
    try {
      const hasLines = editData.lines && Array.isArray(editData.lines);
      if (hasLines) {
        await saveTransactionWithLines(modelName, editData);
      } else {
        await saveRecord(modelName, editData);
      }
      dispatch(showToast({ message: `${modelName} saved`, type: 'success' }));
      setIsEditing(false);
      fetchData(); // refresh from server
    } catch (err) {
      dispatch(showToast({ message: `Save failed`, type: 'error' }));
    } finally {
      setSaving(false);
    }
  };

  // ── Current data (edit or read) ──────────────────────────────────
  const currentData = isEditing ? editData : data;

  // ── Loading states ───────────────────────────────────────────────
  if (layoutLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        Loading {modelName}…
      </div>
    );
  }

  if (!data || !layout) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        Record not found
      </div>
    );
  }

  // ── Render sections ──────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc={`${modelName}-detail`}>
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-1 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shrink-0 no-print">
        <span className="text-sm font-bold text-slate-900 dark:text-white capitalize">{modelName}</span>
        <span className="text-sm font-mono text-slate-600 dark:text-slate-400">{data.ida || `#${data.id}`}</span>
        {data.status && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {data.status}
          </span>
        )}
        {isPendMode && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
            journalized — changes pend
          </span>
        )}
        {editTier === 'closed' && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">
            closed
          </span>
        )}
      </div>

      {/* Toolbar — standard: Add, Save, Cancel, Report + model-specific menu */}
      {(() => {
        // Get model-specific actions from layout JSON
        const lineCardSection = layout.sections.find((s: any) => s.type === 'line_card') as any;
        const modelActions: string[] = lineCardSection?.actions || [];

        return (
          <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 no-print">
            {/* Record info */}
            <span className="text-sm font-mono text-slate-700 dark:text-slate-200">{data.ida}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${data.status === 'open' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>{data.status}</span>
            <span className="text-xs text-slate-500 ml-2">Total: <span className="font-medium">${(data.totals?.total ?? 0).toLocaleString()}</span></span>
            {(data.totals?.balance ?? 0) > 0 && (
              <span className="text-xs text-red-500">Bal: <span className="font-medium">${(data.totals?.balance ?? 0).toLocaleString()}</span></span>
            )}

            <span className="w-4" />

            {/* Standard buttons */}
            {canEdit && !isEditing && (
              <button onClick={handleEdit} className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded border border-blue-600 hover:bg-blue-700">Edit</button>
            )}
            <button onClick={handleAddNew}
              className="px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded border border-green-600 hover:bg-green-700">Add</button>
            {isEditing && (
              <>
                <button onClick={handleSave} disabled={saving} className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded border border-blue-600 hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button onClick={handleCancel} className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded border border-slate-300 dark:border-slate-600 hover:bg-slate-50">Cancel</button>
              </>
            )}
            <div className="relative group/report">
              <button className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded border border-slate-300 dark:border-slate-600 hover:bg-slate-50">
                Report ▾
              </button>
              <div className="hidden group-hover/report:block absolute top-full left-0 pt-1 z-50">
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg min-w-36">
                  <button onClick={async () => {
                    // Open print view in new window — renders layout JSON + record data as clean HTML
                    const w = window.open('', '_blank', 'width=800,height=1000');
                    if (!w) return;
                    w.document.write('<html><body><p>Loading...</p></body></html>');
                    const d = currentData;
                    const co = companyInfo;
                    const lines = d?.lines || [];
                    const totals = d?.totals || {};
                    // Resolve conditions text from Setting by id
                    let conditionsText = '';
                    let conditionsRev = '';
                    if (d.conditions_description) {
                      const parts = d.conditions_description.split('|');
                      conditionsRev = parts.length >= 3 ? `${parts[0]} (rev ${parts[2]})` : parts[0];
                      if (parts.length >= 2) {
                        try {
                          const res = await getRecord('setting', Number(parts[1]));
                          const setting = res?.record || res;
                          conditionsText = setting?.config?.current?.text || parts[0];
                        } catch { conditionsText = parts[0]; }
                      } else {
                        conditionsText = parts[0];
                      }
                    }
                    const lineRows = lines.map((l: any) => {
                      const item = l.item || {};
                      const price = l.price || {};
                      const qty = l.quantity || {};
                      return `<tr>
                        <td>${item.ida_item || ''}</td>
                        <td style="text-align:right">${qty.active ?? ''}</td>
                        <td style="text-align:right;font-style:italic">${qty.remaining ?? ''}</td>
                        <td>${item.description || ''}</td>
                        <td style="text-align:right">${price.unit != null ? price.unit.toFixed(2) : ''}</td>
                        <td style="text-align:right;font-style:italic">${price.extended != null ? price.extended.toLocaleString('en-US', {minimumFractionDigits:2}) : ''}</td>
                      </tr>`;
                    }).join('');
                    const totalExt = lines.reduce((s: number, l: any) => s + (l.price?.extended ?? 0), 0);
                    w.document.open();
                    const printName = `${modelName.toUpperCase()}_${d.ida}_${(d.company || '').replace(/\s+/g, '_')}`;
                    w.document.write(`<!DOCTYPE html><html><head><title>${printName}</title>
                      <style>body{font-family:-apple-system,system-ui,sans-serif;font-size:12px;color:#1a1a1a;margin:0.5in;line-height:1.4}
                      table{width:100%;border-collapse:collapse}th,td{padding:4px 8px;border-bottom:1px solid #e2e8f0}
                      th{text-align:left;font-size:11px;color:#64748b;border-bottom:2px solid #cbd5e1}
                      .hdr{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px}
                      .hdr>div{border:1px solid #e2e8f0;border-radius:6px;padding:10px}
                      .hdr h3{font-size:11px;font-weight:700;margin:0 0 6px;border-bottom:1px solid #f1f5f9;padding-bottom:4px}
                      .row{display:flex;gap:8px;font-size:11px;padding:2px 0}.row .lbl{color:#94a3b8;width:60px;text-align:right;flex-shrink:0}
                      .top{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #1e293b;padding-bottom:8px;margin-bottom:16px}
                      .co{font-size:16px;font-weight:700}.co-addr{font-size:10px;color:#64748b}
                      .doc-type{font-size:20px;font-weight:700;text-align:right}.doc-id{font-size:13px;font-family:monospace;color:#475569}
                      .footer{margin-top:12px;padding-top:8px;border-top:2px solid #cbd5e1;display:flex;justify-content:flex-end;gap:16px;font-size:11px}
                      .footer span{font-style:italic}.footer .total{font-weight:700;font-size:12px}
                      .terms{margin-top:16px;padding-top:8px;border-top:1px solid #e2e8f0;font-size:10px;color:#64748b}
                      @media print{@page{margin:0.5in;size:letter}}</style></head><body>
                      <div class="top"><div><img src="/images/logo/webclerk.png" alt="" style="height:36px;margin-bottom:4px">
                      <div class="co">${co?.name || co?.legal_name || 'Company'}</div>
                      <div class="co-addr">${co?.address?.street1 || ''}${co?.address?.street2 ? ', ' + co.address.street2 : ''}</div>
                      <div class="co-addr">${[co?.address?.city, co?.address?.state, co?.address?.zip].filter(Boolean).join(', ')}</div>
                      <div class="co-addr">${[co?.phone, co?.email, co?.website].filter(Boolean).join(' · ')}</div></div>
                      <div><div class="doc-type">${modelName.toUpperCase()}</div><div class="doc-id">${d.ida}</div><div style="font-size:11px;color:#64748b">${d.status}</div></div></div>
                      <div class="hdr"><div><h3>Customer</h3>
                      <div class="row"><span class="lbl">Company</span><span>${d.company || ''}</span></div>
                      <div class="row"><span class="lbl">Phone</span><span>${d.phone || ''}</span></div>
                      <div class="row"><span class="lbl">Attn</span><span>${d.attention || ''}</span></div>
                      <div class="row"><span class="lbl">Address</span><span>${d.address_full || ''}</span></div>
                      <div class="row"><span class="lbl">Email</span><span>${d.email || ''}</span></div></div>
                      <div><h3>Ship To</h3>
                      <div class="row"><span class="lbl">Ship To</span><span>${d.config?.ship_to?.company || d.company || ''}</span></div>
                      <div class="row"><span class="lbl">Phone</span><span>${d.config?.ship_to?.phone || d.phone || ''}</span></div>
                      <div class="row"><span class="lbl">Attn</span><span>${d.config?.ship_to?.attention || d.attention || ''}</span></div>
                      <div class="row"><span class="lbl">Address</span><span>${d.config?.ship_to?.address1 || d.address_full || ''}</span></div>
                      <div class="row"><span class="lbl">Ship Via</span><span>${d.ship_via || ''}</span></div></div>
                      <div><h3>Order</h3>
                      <div class="row"><span class="lbl">Type Sale</span><span>${d.price_level || ''}</span></div>
                      <div class="row"><span class="lbl">Terms</span><span>${d.terms || ''}</span></div>
                      <div class="row"><span class="lbl">Status</span><span>${d.status || ''}</span></div>
                      <div class="row"><span class="lbl">Date</span><span>${d.dt_created ? new Date(d.dt_created).toLocaleDateString() : ''}</span></div>
                      <div class="row"><span class="lbl">Need By</span><span>${d.dt_needed ? new Date(d.dt_needed).toLocaleDateString() : ''}</span></div>
                      <div class="row"><span class="lbl">Priority</span><span>${d.priority || ''}</span></div></div></div>
                      <table><thead><tr><th>Item</th><th style="text-align:right">Qty</th><th style="text-align:right;font-style:italic">Remain</th><th>Description</th><th style="text-align:right">Unit Price</th><th style="text-align:right;font-style:italic">Extended</th></tr></thead>
                      <tbody>${lineRows}</tbody>
                      <tfoot><tr style="border-top:2px solid #cbd5e1;font-weight:700"><td></td><td style="text-align:right">${lines.reduce((s: number, l: any) => s + (l.quantity?.active ?? 0), 0)}</td><td></td><td></td><td></td><td style="text-align:right">${totalExt.toLocaleString('en-US', {minimumFractionDigits:2})}</td></tr></tfoot></table>
                      <div class="footer"><span>Tax: $${(totals.tax ?? 0).toFixed(2)}</span><span>Ship: $${(totals.shipping ?? 0).toFixed(2)}</span><span>|</span><span class="total">Total: $${totalExt.toLocaleString('en-US', {minimumFractionDigits:2})}</span></div>
                      ${d.comments?.public ? `<div class="terms"><strong>Notes:</strong> ${d.comments.public}</div>` : ''}
                      ${d.conditions_description ? `<div class="terms"><strong>Conditions:</strong> <em>${d.conditions_description}</em><br>${conditionsText}</div>` : ''}
                      ${d.terms || documentText?.invoice_comment ? `<div class="terms">${d.terms ? '<strong>Terms:</strong> ' + d.terms : ''}${documentText?.invoice_comment ? '<br>' + documentText.invoice_comment : ''}</div>` : ''}
                      </body></html>`);
                    w.document.close();
                    setTimeout(() => w.print(), 300);
                  }} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 rounded-t">Print</button>
                  <button onClick={() => dispatch(showToast({ message: 'Email: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">Email</button>
                  <button onClick={() => dispatch(showToast({ message: 'Labels: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">Labels</button>
                  <button onClick={() => dispatch(showToast({ message: 'Clone: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 border-t border-slate-100 dark:border-slate-700 rounded-b">Clone</button>
                </div>
              </div>
            </div>

            {/* Model-specific menu */}
            <WcModelMenu
              modelName={modelName}
              actions={modelActions}
              onAction={(actionId) => dispatch(showToast({ message: `${actionId}: coming soon`, type: 'info' }))}
            />

            <span className="flex-1" />

            {/* Delete — far right */}
            {canEdit && (
              <button onClick={() => dispatch(showToast({ message: 'Delete: coming soon', type: 'info' }))}
                className="px-3 py-1.5 text-sm font-medium text-red-600 rounded border border-red-300 hover:bg-red-50">
                Delete
              </button>
            )}
          </div>
        );
      })()}

      {/* Content — scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {layout.sections.map((section, idx) => {
          switch (section.type) {
            case 'header':
              return (
                <HeaderRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  modelName={modelName}
                  onChange={handleFieldChange}
                  custSearch={{
                    open: custSearchOpen,
                    query: custSearchQuery,
                    results: custSearchResults,
                    searching: custSearching,
                    inputRef: custSearchRef,
                    onToggle: (open) => { setCustSearchOpen(open); if (!open) { setCustSearchQuery(''); setCustSearchResults([]); } },
                    onSearch: handleCustSearch,
                    onSelect: handleCustSelect,
                  }}
                />
              );
            case 'line_card':
              return (
                <LineCardRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  isLocked={editTier === 'closed'}
                  onLinesChange={handleLinesChange}
                />
              );
            case 'tabs':
              return (
                <TabsRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  modelName={modelName}
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  onChange={handleFieldChange}
                  onRefresh={fetchData}
                  loggedInUserName={loggedInUserName}
                />
              );
            default:
              return null;
          }
        })}

      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Section Renderers
// ---------------------------------------------------------------------------

/** Resolve a dot-notation field path (e.g., "config.ship_to.company") from a record */
function getNestedValue(data: any, path: string): unknown {
  if (!data || !path) return undefined;
  return path.split('.').reduce((obj, key) => obj?.[key], data);
}

/** Format epoch ms or ISO string to readable date */
function formatDate(val: unknown): string {
  if (val == null) return '—';
  let d: Date;
  if (typeof val === 'number') {
    // Epoch ms (> 1e12) or epoch seconds (< 1e12)
    d = new Date(val > 1e12 ? val : val * 1000);
  } else if (typeof val === 'string') {
    d = new Date(val);
  } else {
    return String(val);
  }
  if (isNaN(d.getTime())) return String(val);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/** Fields that should be formatted as dates */
const DATE_FIELDS = new Set(['dt_created', 'dt_modified', 'dt_needed', 'Date Ord', 'Need By']);

/** Render a single field row */
// Label style convention: select=blue, action=green, search=bold, readonly=italic, editable=normal
// Colors from company prefs.layout.label_styles, with dark mode variants
const LABEL_STYLES: Record<string, { light: string; dark: string; fontWeight?: number; fontStyle?: string }> = {
  select:   { light: '#1e40af', dark: '#60a5fa' },
  action:   { light: '#166534', dark: '#4ade80' },
  search:   { light: '#64748b', dark: '#94a3b8', fontWeight: 700 },
  readonly: { light: '#94a3b8', dark: '#64748b', fontStyle: 'italic' },
  editable: { light: '#64748b', dark: '#94a3b8' },
};

const useLabelStyle = (fieldType?: string) => {
  const isDark = document.documentElement.classList.contains('dark');
  const style = LABEL_STYLES[fieldType || 'editable'] || LABEL_STYLES.editable;
  return {
    color: isDark ? style.dark : style.light,
    fontWeight: style.fontWeight,
    fontStyle: style.fontStyle as any,
  };
};

const FieldRow: React.FC<{
  field: string;
  label: string;
  data: any;
  isEditing: boolean;
  options?: string[];
  fieldType?: string;  // select | action | search | readonly | editable
  help?: string;       // Shift+hover shows Alice's field help
  onChange: (field: string, value: unknown) => void;
}> = ({ field, label, data, isEditing, options, fieldType, help, onChange }) => {
  const [showHelp, setShowHelp] = useState(false);
  const val = field.includes('.') ? getNestedValue(data, field) : data?.[field];
  const isDate = field.startsWith('dt_') || DATE_FIELDS.has(field) || DATE_FIELDS.has(label);
  const displayVal = val == null ? '—'
    : isDate ? formatDate(val)
    : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || (val as any)?.ida || JSON.stringify(val)
    : String(val);
  // Derive field type: explicit > has options > calculated fields always readonly
  const resolvedType = fieldType || (options ? 'select' : 'editable');
  const labelStyle = useLabelStyle(resolvedType);
  const isClickable = resolvedType === 'select' || resolvedType === 'action' || resolvedType === 'search';
  return (
    <div className="flex items-baseline gap-2 py-0.5 relative">
      <span
        className={`text-[10px] font-medium w-16 shrink-0 text-right ${isClickable ? 'hover:underline cursor-pointer' : ''}`}
        style={labelStyle}
        onMouseEnter={(e) => { if (e.shiftKey && help) setShowHelp(true); }}
        onMouseLeave={() => setShowHelp(false)}
        onMouseMove={(e) => { if (!e.shiftKey) setShowHelp(false); else if (help) setShowHelp(true); }}
      >{label}</span>
      {showHelp && help && (
        <div className="absolute left-20 top-0 z-50 bg-slate-800 text-white text-[10px] px-2 py-1 rounded shadow-lg max-w-64 whitespace-normal leading-relaxed">
          {help}
        </div>
      )}
      {isEditing && options ? (
        <select
          value={val || ''}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 text-xs px-1 py-0.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
        >
          <option value="">—</option>
          {options.map(o => <option key={o} value={o}>{o.split('|')[0]}</option>)}
        </select>
      ) : isEditing ? (
        <input
          type="text"
          value={displayVal === '—' ? '' : displayVal}
          onChange={(e) => onChange(field, e.target.value)}
          className="flex-1 text-xs px-2 py-0.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
        />
      ) : (
        <span className="flex-1 text-xs text-slate-900 dark:text-white">{typeof displayVal === 'string' ? displayVal.split('|')[0] : displayVal}</span>
      )}
    </div>
  );
};

/** Render header — supports rows layout and three-column layout */
const HeaderRenderer: React.FC<{
  section: any;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  custSearch?: {
    open: boolean;
    query: string;
    results: any[];
    searching: boolean;
    inputRef: React.RefObject<HTMLInputElement | null>;
    onToggle: (open: boolean) => void;
    onSearch: (query: string) => void;
    onSelect: (cust: any) => void;
  };
}> = ({ section, data, isEditing, onChange, custSearch }) => {
  // Three-column layout (Customer | Ship To | Order)
  if (section.layout === 'three-column' && section.columns) {
    return (
      <div className="grid grid-cols-3 gap-3">
        {section.columns.map((col: any, colIdx: number) => (
          <div key={colIdx} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
            <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1 flex items-center gap-2">
              <span>{col.title}</span>
              {col.title_ida && data?.customer && (
                <span className="font-mono text-slate-400 dark:text-slate-500 font-normal text-[10px]">
                  #{typeof data.customer === 'object' ? data.customer.id : data.customer}
                </span>
              )}
              {col.title_ida && isEditing && custSearch && !custSearch.open && (
                <button
                  type="button"
                  className="ml-auto text-[10px] text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
                  title="Search customers"
                  onClick={() => custSearch.onToggle(true)}
                >🔍</button>
              )}
              {col.title_ida && isEditing && custSearch?.open && (
                <div className="ml-auto relative">
                  <input
                    ref={custSearch.inputRef}
                    type="text"
                    value={custSearch.query}
                    onChange={(e) => custSearch.onSearch(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Escape') { custSearch.onToggle(false); custSearch.onSearch(''); } }}
                    placeholder="bil,jame or 612..."
                    className="text-[11px] px-2 py-0.5 w-44 border border-blue-400 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  {custSearch.searching && <span className="absolute right-2 top-0.5 text-[10px] text-slate-400">...</span>}
                  {custSearch.results.length > 0 && (
                    <div className="absolute top-6 left-0 w-96 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 max-h-60 overflow-y-auto">
                      {custSearch.results.map((c: any) => (
                        <button
                          key={c.id}
                          type="button"
                          className="w-full text-left px-3 py-2 text-[11px] hover:bg-blue-50 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700 last:border-0"
                          onClick={() => custSearch.onSelect(c)}
                        >
                          <div className="flex items-baseline gap-2">
                            <span className="font-medium text-slate-900 dark:text-white">{c.company || c.display_name || `#${c.id}`}</span>
                            <span className="text-slate-400 font-mono text-[10px]">#{c.id}</span>
                          </div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                            {[c.attention, c.phone, c.address_full || c.email].filter(Boolean).join(' · ')}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                  {custSearch.query.length >= 2 && !custSearch.searching && custSearch.results.length === 0 && (
                    <div className="absolute top-6 left-0 w-52 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 px-3 py-2 text-[11px] text-slate-400">
                      No customers found
                    </div>
                  )}
                </div>
              )}
            </div>
            {col.fields.map((f: any) => (
              <FieldRow
                key={f.field}
                field={f.field}
                label={f.label}
                data={data}
                isEditing={isEditing}
                options={f.options}
                fieldType={f.type}
                help={f.help}
                onChange={onChange}
              />
            ))}
            {col.action_summary && (
              <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                <div
                  className="text-[10px] font-medium text-slate-400 cursor-pointer hover:text-blue-600 hover:underline"
                  onClick={() => {
                    const actionId = data?.actions?.items?.[0]?.id;
                    if (actionId) {
                      window.open(`/db/action?id=${actionId}`, '_blank');
                    }
                  }}
                  title="Click to open action record"
                >Next Action</div>
                <div className="text-xs text-slate-600 dark:text-slate-300">
                  {data?.actions?.items?.[0]
                    ? `${typeof data.actions.items[0].action === 'object' ? data.actions.items[0].action?.en : data.actions.items[0].action} — ${data.actions.items[0].status || 'pending'}`
                    : '—'}
                </div>
                {data?.actions?.items?.[0]?.assigned_to && (
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {data.actions.items[0].assigned_to}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Default rows layout
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2">
      {(section.rows || []).map((row: any, rowIdx: number) => (
        <div
          key={rowIdx}
          className="grid gap-3"
          style={{ gridTemplateColumns: `repeat(${row.cols}, 1fr)` }}
        >
          {row.fields.map((field: string, fieldIdx: number) => {
            const val = field.includes('.') ? getNestedValue(data, field) : data?.[field];
            const label = row.label?.[fieldIdx] || field.split('.').pop() || field;
            const displayVal = val == null ? '—'
              : typeof val === 'object' ? (val as any)?.name || (val as any)?.display_name || JSON.stringify(val)
              : String(val);
            return (
              <div key={field} className="flex flex-col gap-0.5">
                <label className="text-[10px] font-medium text-slate-500 dark:text-slate-400">{label}</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={displayVal === '—' ? '' : displayVal}
                    onChange={(e) => onChange(field, e.target.value)}
                    className="text-xs px-2 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  />
                ) : (
                  <span className="text-xs text-slate-900 dark:text-white">{displayVal}</span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

/** Render the line card — DataGrid with line card config, no LinesCard component */
const LineCardRenderer: React.FC<{
  section: LineCardSection;
  data: any;
  isEditing: boolean;
  isLocked: boolean;
  onLinesChange: (lines: TransactionLine[]) => void;
}> = ({ section, data, isEditing, isLocked, onLinesChange }) => {
  const lines = data?.lines || [];
  const windowManager = useWindowManager();

  const lc = useLineCard({
    lines,
    family: section.family,
    isEditing,
    isLocked,
    priceLevel: data?.price_level,
    onLinesChange,
    onOpenItem: (itemId, itemCode) => {
      const path = `/db/item?id=${itemId}`;
      windowManager.ensureWindow(path, `Item ${itemCode || itemId}`, { maximized: false });
    },
  });

  const formatCurrency = (v: number) => '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const formatNumber = (v: number) => v.toLocaleString();

  // Selection-aware footer calculations
  const activeRecords = lc.selectedLineIds.size > 0
    ? lc.records.filter(r => lc.selectedLineIds.has(r.id))
    : lc.records;
  const footerQty = activeRecords.reduce((s, r) => s + (r.qty ?? 0), 0);
  const footerExtended = activeRecords.reduce((s, r) => s + (r.extended ?? 0), 0);
  const footerBacklog = activeRecords.reduce((s, r) => s + (r._hasBacklog ? r.remaining * (lc.isSellSide ? r.discounted_unit : r.unit_cost) : 0), 0);
  const selectionLabel = lc.selectedLineIds.size > 0 ? ` (${lc.selectedLineIds.size} selected)` : '';

  if (!lines.length) {
    return (
      <div className="text-center py-12 text-slate-400">
        <p>No line items on this order</p>
      </div>
    );
  }

  const footerBar = (
    <div className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600 text-xs px-2 py-2">
      <div className="flex items-center gap-4 mb-1">
        <span className="font-medium text-slate-600">Lns: {lc.lineCount}</span>
        <span className="text-slate-600">Items: {formatNumber(footerQty)}</span>
        {selectionLabel && <span className="text-blue-600 font-medium">{selectionLabel}</span>}
        {lc.selectedId != null && (
          <span className="flex items-center gap-1 ml-2 text-[10px]">
            <button type="button" onClick={() => { const line = lc.records.find(r => r.id === lc.selectedId); if (line?._line) lc.setSelectedId(line.id); }}
              className="px-1.5 py-0.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded" title="Edit line details">edit</button>
            {lc.canEdit && (
              <button type="button" onClick={() => { lc.selectedLineIds.forEach(id => onLinesChange?.(lines.filter((_: any, i: number) => lc.records[i]?.id !== id))); lc.setSelectedLineIds(new Set()); }}
                className="px-1.5 py-0.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded" title="Delete selected (Del)">del</button>
            )}
          </span>
        )}
        <span className="flex-1" />
        <span className="flex items-center gap-1 text-[9px] font-bold">
          <button type="button" onClick={() => lc.togglePanel('inventory')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'inventory' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Inventory lookup (L)">L</button>
          <button type="button" onClick={() => lc.togglePanel('spec')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'spec' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Specification (S)">S</button>
          <button type="button" onClick={() => lc.togglePanel('xref')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'xref' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-600 hover:bg-blue-50'}`}
            title="Cross-references (XR)">XR</button>
          <button type="button" onClick={() => lc.togglePanel('margin')}
            className={`px-1.5 py-0.5 rounded transition-colors ${lc.activePanel === 'margin' ? 'bg-green-600 text-white' : 'text-slate-500 hover:text-green-600 hover:bg-green-50'}`}
            title="Margin view (M)">M</button>
        </span>
      </div>
      <div className="flex items-center gap-3 justify-end italic">
        <span className="text-slate-400">Tax:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.tax ?? 0)}</span>
        <span className="text-slate-400">Ship:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.shipping ?? 0)}</span>
        <span className="text-slate-400">Other:</span>
        <span className="font-mono text-slate-700 w-16 text-right">{formatCurrency(data?.totals?.other ?? 0)}</span>
        <span className="text-slate-300 not-italic">|</span>
        <span className="text-slate-500">Deposit:</span>
        <span className="font-bold text-slate-900 w-20 text-right">{formatCurrency(data?.totals?.deposit ?? 0)}</span>
        {footerBacklog > 0 && (
          <>
            <span className="text-red-500">Backlog:</span>
            <span className="font-bold text-red-600 w-20 text-right">{formatCurrency(footerBacklog)}</span>
          </>
        )}
        <span className="text-slate-700">Total:</span>
        <span className="font-bold text-slate-900 w-24 text-right">{formatCurrency(footerExtended)}</span>
      </div>
    </div>
  );

  const panelContent = (
    <>
      {lc.activePanel === 'margin' && (
        <MarginPanel lines={lines} selectedIds={lc.selectedLineIds} isSellSide={lc.isSellSide} />
      )}
      {lc.activePanel !== 'none' && lc.activePanel !== 'margin' && (
        <div className="border-t border-slate-200 bg-white max-h-[250px] overflow-y-auto">
          {lc.activePanel === 'inventory' && <InventoryPanel itemIds={lc.inventoryItemIds} itemCodes={[]} />}
          {lc.activePanel === 'spec' && <SpecPanel itemId={lc.selectedLineRecord?._itemId ?? null} itemCode={lc.selectedLineRecord?.item_code ?? ''} />}
          {lc.activePanel === 'xref' && <XRefPanel itemId={lc.selectedLineRecord?._itemId ?? null} itemCode={lc.selectedLineRecord?.item_code ?? ''} />}
        </div>
      )}
    </>
  );

  return (
    <DataGrid
      hideToolbar
      disableReorder
      records={lc.activePanel === 'margin' ? [] : lc.records}
      columns={lc.richColumns.map(c => c.name)}
      richColumns={lc.richColumns}
      colWidths={lc.colWidths}
      fieldBehaviors={lc.fieldBehaviors}
      selectedId={lc.selectedId}
      selectedRowIds={lc.selectedLineIds}
      sort={null}
      onSelectRecord={(id) => { lc.setSelectedId(id); if (id != null) lc.setSelectedLineIds(new Set([id])); }}
      onToggleRow={(id) => { lc.setSelectedLineIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }); }}
      onSelectAll={() => { lc.setSelectedLineIds(new Set(lc.records.map(r => r.id).filter((id): id is number => id != null))); }}
      onClearSelection={() => lc.setSelectedLineIds(new Set())}
      onSort={() => {}}
      onColumnDrop={() => {}}
      onResizeStart={() => {}}
      onCellEdit={lc.canEdit ? lc.handleCellEdit : undefined}
      numId={(v: unknown) => typeof v === 'number' ? v : null}
      theme={lc.theme}
      fontSize={12}
      footerBar={footerBar}
      panelContent={panelContent}
      onHeaderClick={lc.canEdit ? lc.openBulkEdit : undefined}
      headerEditField={lc.bulkEditField}
      headerEditValue={lc.bulkEditValue}
      onHeaderEditChange={lc.setBulkEditValue}
      onHeaderEditApply={lc.applyBulkEdit}
      onHeaderEditCancel={lc.cancelBulkEdit}
    />
  );
};

/** Render tabbed sections */
const TabsRenderer: React.FC<{
  section: TabsSection;
  data: any;
  isEditing: boolean;
  modelName: string;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}> = ({ section, data, isEditing, modelName, activeTab, onTabChange, onChange, onRefresh, loggedInUserName }) => {
  // Default to first tab if activeTab not in this section
  const tabIds = section.tabs.map(t => t.content);
  const currentTab = tabIds.includes(activeTab) ? activeTab : tabIds[0] || 'summary';

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
      {/* Tab bar */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 overflow-x-auto no-print">
        {section.tabs.map((tab) => (
          <button
            key={tab.content}
            onClick={() => onTabChange(tab.content)}
            className={`px-4 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
              currentTab === tab.content
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4">
        <TabContent
          tabId={currentTab}
          data={data}
          isEditing={isEditing}
          modelName={modelName}
          onChange={onChange}
          onRefresh={onRefresh}
          loggedInUserName={loggedInUserName}
        />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tab Content — renders the right component for each tab type
// ---------------------------------------------------------------------------

const TabContent: React.FC<{
  tabId: string;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}> = ({ tabId, data, isEditing, modelName, onChange, onRefresh, loggedInUserName }) => {
  switch (tabId) {
    case 'summary':
      return <SummaryTabContent data={data} modelName={modelName} />;

    case 'payments':
    case 'financials':
    case 'margins':
      return (
        <FinancialsPanel
          transactionId={data?.id}
          modelName={modelName}
          isEditing={false}
        />
      );

    case 'contacts': {
      // Extract contact IDs from refs.links.contact and render as db.list
      const rawContacts = data?.refs?.links?.contact ?? [];
      const contactRows = Array.isArray(rawContacts) ? rawContacts.map((c: any) => {
        const ct = c.contact || c;
        return {
          id: ct.id || ct.contact_id || 0,
          ida: ct.ida || '',
          role: c.purpose || ct.role || '',
          name: ct.attention || ct.display_name || '',
          email: Array.isArray(ct.email) ? ct.email[0] : (ct.email || ''),
          phone: Array.isArray(ct.phone) ? ct.phone[0] : (ct.phone || ''),
          address: Array.isArray(ct.address) ? ct.address[0]?.full : (ct.address?.full || ct.address || ''),
        };
      }) : [];

      if (!contactRows.length) {
        return <div className="text-center py-8 text-slate-400 text-sm">No contacts linked</div>;
      }

      return (
        <DataGrid
          hideToolbar
          records={contactRows}
          columns={['role', 'name', 'email', 'phone', 'address']}
          richColumns={[
            { name: 'role', field: 'role', width: '70px', sortable: true },
            { name: 'name', field: 'name', width: '150px', sortable: true },
            { name: 'email', field: 'email', width: '200px', sortable: true },
            { name: 'phone', field: 'phone', width: '140px', sortable: true },
            { name: 'address', field: 'address', width: '250px', sortable: true },
          ]}
          colWidths={{ role: 70, name: 150, email: 200, phone: 140, address: 250 }}
          fieldBehaviors={{ role: { type: 'readonly' }, name: { type: 'readonly' }, email: { type: 'readonly' }, phone: { type: 'readonly' }, address: { type: 'readonly' } }}
          selectedId={null}
          selectedRowIds={new Set()}
          sort={null}
          onSelectRecord={() => {}}
          onSort={() => {}}
          onColumnDrop={() => {}}
          onResizeStart={() => {}}
          numId={(v: unknown) => typeof v === 'number' ? v : null}
          fontSize={12}
        />
      );
    }

    case 'comments':
      return (
        <CommentsPanel
          comments={data?.comments}
          isEditing={isEditing}
          onChange={(comments: any) => onChange('comments', comments)}
        />
      );

    case 'documents': {
      // Fetch documents linked via refs
      const docs = data?.refs?.links?.document ?? [];
      const docRows = Array.isArray(docs) ? docs.map((d: any) => {
        const doc = d.document || d;
        return { id: doc.id || 0, ida: doc.ida || '', name: doc.name || doc.display_name || '', status: doc.status || d.purpose || '' };
      }) : [];
      if (!docRows.length) return <div className="text-center py-8 text-slate-400 text-sm">No documents attached</div>;
      return (
        <DataGrid
          hideToolbar
          records={docRows}
          columns={['ida', 'name', 'status']}
          richColumns={[
            { name: 'ida', field: 'ida', width: '120px', sortable: true },
            { name: 'name', field: 'name', width: '350px', sortable: true },
            { name: 'status', field: 'status', width: '100px', sortable: true },
          ]}
          colWidths={{ ida: 120, name: 350, status: 100 }}
          fieldBehaviors={{ ida: { type: 'readonly' }, name: { type: 'readonly' }, status: { type: 'readonly' } }}
          selectedId={null}
          selectedRowIds={new Set()}
          sort={null}
          onSelectRecord={() => {}}
          onSort={() => {}}
          onColumnDrop={() => {}}
          onResizeStart={() => {}}
          numId={(v: unknown) => typeof v === 'number' ? v : null}
          fontSize={12}
        />
      );
    }

    case 'actions': {
      const actionItems = (data?.actions?.items ?? []) as any[];
      if (!actionItems.length) return <div className="text-center py-8 text-slate-400 text-sm">No actions on this {modelName}</div>;
      return (
        <DataGrid
          hideToolbar
          records={actionItems}
          columns={['action', 'status']}
          richColumns={[
            { name: 'action', field: 'action', width: '400px', sortable: true },
            { name: 'status', field: 'status', width: '100px', sortable: true },
          ]}
          colWidths={{ action: 400, status: 100 }}
          fieldBehaviors={{ action: { type: 'readonly' }, status: { type: 'readonly' } }}
          selectedId={null}
          selectedRowIds={new Set()}
          sort={null}
          onSelectRecord={() => {}}
          onSort={() => {}}
          onColumnDrop={() => {}}
          onResizeStart={() => {}}
          numId={(v: unknown) => typeof v === 'number' ? v : null}
          fontSize={12}
        />
      );
    }

    case 'related_transactions': {
      // Build rows from all refs.links entries
      const links = data?.refs?.links || {};
      const relatedRows: any[] = [];
      for (const [linkType, items] of Object.entries(links)) {
        if (!Array.isArray(items)) continue;
        for (const item of items as any[]) {
          const obj = item.contact || item.customer || item;
          relatedRows.push({
            id: obj.id || 0,
            type: linkType,
            ida: obj.ida || '',
            name: obj.display_name || obj.company || obj.name || obj.attention || '',
          });
        }
      }
      if (!relatedRows.length) return <div className="text-center py-8 text-slate-400 text-sm">No related records</div>;
      return (
        <DataGrid
          hideToolbar
          records={relatedRows}
          columns={['type', 'ida', 'name']}
          richColumns={[
            { name: 'type', field: 'type', width: '100px', sortable: true },
            { name: 'ida', field: 'ida', width: '150px', sortable: true },
            { name: 'name', field: 'name', width: '300px', sortable: true },
          ]}
          colWidths={{ type: 100, ida: 150, name: 300 }}
          fieldBehaviors={{ type: { type: 'readonly' }, ida: { type: 'readonly' }, name: { type: 'readonly' } }}
          selectedId={null}
          selectedRowIds={new Set()}
          sort={null}
          onSelectRecord={() => {}}
          onSort={() => {}}
          onColumnDrop={() => {}}
          onResizeStart={() => {}}
          numId={(v: unknown) => typeof v === 'number' ? v : null}
          fontSize={12}
        />
      );
    }

    case 'qa': {
      const [qaRecords, setQaRecords] = React.useState<any[]>([]);
      React.useEffect(() => {
        if (!data?.id) return;
        getRecords('qa', { parent_id: data.id, parent_model: modelName, limit: 50 })
          .then(res => setQaRecords(res?.results || []))
          .catch(() => setQaRecords([]));
      }, [data?.id, modelName]);

      if (!qaRecords.length) return <div className="text-center py-8 text-slate-400 text-sm">No QA records</div>;
      return (
        <DataGrid
          hideToolbar
          records={qaRecords.map((q: any) => ({
            id: q.id,
            ida: q.ida || '',
            question: q.question || '',
            answer: q.answer || '',
            status: q.status || '',
          }))}
          columns={['ida', 'question', 'answer', 'status']}
          richColumns={[
            { name: 'ida', field: 'ida', width: '100px', sortable: true },
            { name: 'question', field: 'question', width: '300px', sortable: true },
            { name: 'answer', field: 'answer', width: '250px', sortable: true },
            { name: 'status', field: 'status', width: '80px', sortable: true },
          ]}
          colWidths={{ ida: 100, question: 300, answer: 250, status: 80 }}
          fieldBehaviors={{ ida: { type: 'readonly' }, question: { type: 'readonly' }, answer: { type: 'readonly' }, status: { type: 'readonly' } }}
          selectedId={null}
          selectedRowIds={new Set()}
          sort={null}
          onSelectRecord={() => {}}
          onSort={() => {}}
          onColumnDrop={() => {}}
          onResizeStart={() => {}}
          numId={(v: unknown) => typeof v === 'number' ? v : null}
          fontSize={12}
        />
      );
    }

    case 'shipping':
      return <ShippingTabContent data={data} />;

    case 'notes':
      return <NotesTabContent data={data} isEditing={isEditing} onChange={onChange} userName={loggedInUserName || 'User'} />;

    case 'history':
      return (
        <div className="text-xs text-slate-500 dark:text-slate-400">
          <pre className="whitespace-pre-wrap">{JSON.stringify(data?.metadata?.history ?? [], null, 2)}</pre>
        </div>
      );

    default:
      return (
        <div className="text-center py-8 text-slate-400 text-sm">
          Tab "{tabId}" not implemented
        </div>
      );
  }
};

// ---------------------------------------------------------------------------
// Built-in Tab Content Components
// ---------------------------------------------------------------------------

const SummaryTabContent: React.FC<{ data: any; modelName: string }> = ({ data, modelName }) => {
  const lines = data?.lines || [];
  const isSellSide = ['order', 'invoice', 'proposal'].includes(modelName);
  const totals = data?.totals || {};
  const sell = data?.sell || {};
  const cost = data?.cost || {};

  const totalExtended = lines.reduce((sum: number, line: any) => {
    if (isSellSide) return sum + Number(line.price?.extended ?? 0);
    return sum + Number(line.cost?.extended ?? 0);
  }, 0);
  const totalCost = lines.reduce((sum: number, line: any) => sum + Number(line.cost?.extended ?? 0), 0);
  const margin = totalExtended - totalCost;
  const marginPct = totalExtended > 0 ? (margin / totalExtended) * 100 : 0;

  const fmt = (v: number | null | undefined) => v == null ? '—' : `$${Number(v).toFixed(2)}`;

  // Customer data from refs links OR from the record's customer config
  const customerLink = data?.refs?.links?.customer?.[0] || {};
  const customerConfig = data?.customer_config || {};
  const customerData = { ...customerConfig, ...customerLink };

  // Payment and invoice data for third column
  const [payments, setPayments] = React.useState<any[]>([]);
  const [invoices, setInvoices] = React.useState<any[]>([]);
  React.useEffect(() => {
    if (!data?.id) return;
    (async () => {
      try {
        // Invoices linked via parent_id; payments by customer (no parent_id on payment model)
        const custId = data.customer_id || data.customer;
        const [payRes, invRes] = await Promise.all([
          custId ? getRecords('payment', { customer_id: custId, limit: 20 }).catch(() => null) : null,
          getRecords('invoice', { parent_id: data.id, parent_model: modelName, limit: 20 }).catch(() => null),
        ]);
        // Filter out demo/test records (ida starting with qq or zz)
        const filterReal = (recs: any[]) => (recs || []).filter((r: any) => {
          const ida = String(r.ida || '').toLowerCase();
          return !ida.startsWith('qq') && !ida.startsWith('zz') && !ida.startsWith('dev-');
        });
        setPayments(filterReal(payRes?.results));
        setInvoices(filterReal(invRes?.results));
      } catch { /* nothing yet */ }
    })();
  }, [data?.id]);

  const totalPayments = payments.reduce((s: number, d: any) => s + Number(d.total ?? d.totals?.total ?? 0), 0);
  const totalInvoiced = invoices.reduce((s: number, d: any) => s + Number(d.total ?? d.totals?.total ?? 0), 0);
  const totalUnapplied = invoices.reduce((s: number, d: any) => s + Number(d.balance ?? d.totals?.balance ?? 0), 0);

  return (
    <div className="grid grid-cols-3 gap-6 text-xs">
      {/* Left: Order Totals */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Order Totals</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-slate-500">Lines</span><span className="font-mono">{lines.length}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Sell Amount</span><span className="font-mono">{fmt(sell.line_sum_goods || totalExtended)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Discount</span><span className="font-mono">{fmt(sell.discount || totals.discount)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Sell Total</span><span className="font-mono font-medium">{fmt(sell.total || totalExtended)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Taxable</span><span className="font-mono">{fmt(totals.taxable)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Tax</span><span className="font-mono">{fmt(totals.tax)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Shipping</span><span className="font-mono">{fmt(totals.shipping)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Other</span><span className="font-mono">{fmt(totals.other)}</span></div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />
          <div className="flex justify-between font-bold"><span>Total</span><span className="font-mono">{fmt(totals.total || totalExtended)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Cost</span><span className="font-mono">{fmt(cost.line_sum_goods || totalCost)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Freight</span><span className="font-mono">{fmt(cost.freight)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Commissions</span><span className="font-mono">{fmt(cost.commissions)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Cost Total</span><span className="font-mono">{fmt(cost.total || totalCost)}</span></div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />
          <div className="flex justify-between">
            <span className="text-slate-500">Margin</span>
            <span className="font-mono text-green-700 dark:text-green-400">{fmt(margin)} ({marginPct.toFixed(1)}%)</span>
          </div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Payments</span><span className="font-mono">{data?.finance?.payment_count ?? totals.payment_count ?? 0}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Received</span><span className="font-mono">{fmt(totals.received)}</span></div>
          <div className="flex justify-between font-medium"><span>Balance</span><span className="font-mono">{fmt(totals.balance || data?.balance)}</span></div>
        </div>
      </div>

      {/* Right: Customer */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Customer</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-slate-500">Company</span><span className="font-mono">{data?.company || data?.customer_company || customerData.company || customerData.display_name || '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Price Level</span><span className="font-mono">{data?.price_level || '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Terms</span><span className="font-mono">{data?.terms || '—'}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Credit</div>
          <div className="flex justify-between"><span className="text-slate-500">Credit Limit</span><span className="font-mono">{fmt(customerData.credit_limit)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Available</span><span className="font-mono">{fmt(customerData.credit_available)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Balance Due</span><span className="font-mono">{fmt(customerData.balance_due)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Current</span><span className="font-mono">{fmt(customerData.balance_current)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Sales History</div>
          <div className="flex justify-between"><span className="text-slate-500">MTD</span><span className="font-mono">{fmt(customerData.sales_mtd)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">YTD</span><span className="font-mono">{fmt(customerData.sales_ytd)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Lifetime</span><span className="font-mono">{fmt(customerData.sales_lifetime)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Payment</div>
          <div className="flex justify-between"><span className="text-slate-500">Avg Days</span><span className="font-mono">{customerData.avg_pay_days ?? '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Last Payment</span><span className="font-mono">{fmt(customerData.last_payment_amount)}</span></div>
        </div>
      </div>

      {/* Right: Payments then Invoices */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Flow</div>
        <div className="space-y-0.5">
          <div className="flex justify-between font-medium"><span>Total</span><span className="font-mono">{fmt(totalInvoiced || totals.total || totalExtended)}</span></div>
          <div className="flex justify-between font-medium">
            <span className={totalUnapplied > 0 ? 'text-red-600' : 'text-slate-500'}>Unapplied</span>
            <span className={`font-mono ${totalUnapplied > 0 ? 'text-red-600 font-bold' : ''}`}>{fmt(totalUnapplied || totals.balance || data?.balance)}</span>
          </div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />

          {/* Payments first */}
          <div className="text-[10px] font-medium text-slate-400 mb-0.5">Payments</div>
          {payments.length > 0 ? (
            <div className="space-y-0.5 mb-2">
              {payments.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/payment/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-slate-700 dark:text-slate-300">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono text-green-700 dark:text-green-400">{fmt(doc.total ?? doc.totals?.total)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-400 mb-2">No payments</div>
          )}

          {/* Invoices second */}
          <div className="text-[10px] font-medium text-slate-400 mb-0.5">Invoices</div>
          {invoices.length > 0 ? (
            <div className="space-y-0.5">
              {invoices.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/invoice/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-slate-700 dark:text-slate-300">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono">{fmt(doc.total ?? doc.totals?.total)}</span>
                  <span className={`font-mono ${Number(doc.balance ?? doc.totals?.balance ?? 0) > 0 ? 'text-red-500' : 'text-green-600'}`}>
                    {fmt(doc.balance ?? doc.totals?.balance)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-400">No invoices</div>
          )}
        </div>
      </div>
    </div>
  );
};

const ActionsTabContent: React.FC<{ data: any; modelName: string }> = ({ data, modelName }) => {
  const actions = (data?.actions?.items ?? []) as any[];

  if (!actions.length) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No actions on this {modelName}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actions.map((action: any, idx: number) => (
        <div
          key={action.id ?? idx}
          className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 flex justify-between items-center"
        >
          <span className="font-medium text-sm text-slate-900 dark:text-white">
            {typeof action.action === 'object' ? action.action?.en : action.action ?? action.what ?? '—'}
          </span>
          <span className={`px-2 py-0.5 text-xs rounded-full ${
            action.status === 'done' || action.status === 'completed'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
          }`}>
            {action.status ?? 'pending'}
          </span>
        </div>
      ))}
    </div>
  );
};

const ShippingTabContent: React.FC<{ data: any }> = ({ data }) => {
  const shipments = (data?.metadata?.shipping ?? []) as any[];

  if (!shipments.length) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No shipments recorded
      </div>
    );
  }

  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
          <th className="text-left px-2 py-1.5 font-medium">Carrier</th>
          <th className="text-left px-2 py-1.5 font-medium">Shipment ID</th>
          <th className="text-right px-2 py-1.5 font-medium">Mass</th>
          <th className="text-left px-2 py-1.5 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {shipments.map((s: any, i: number) => (
          <tr key={i} className="border-b border-slate-100 dark:border-slate-700">
            <td className="px-2 py-1">{s.carrier ?? '—'}</td>
            <td className="px-2 py-1 font-mono">{s.shipment_id ?? '—'}</td>
            <td className="px-2 py-1 text-right">{s.mass != null ? `${s.mass} lbs` : '—'}</td>
            <td className="px-2 py-1">{s.status ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const NotesTabContent: React.FC<{
  data: any;
  isEditing: boolean;
  onChange: (field: string, value: unknown) => void;
  userName?: string;
}> = ({ data, isEditing, onChange, userName }) => {
  const notes = data?.notes || data?.comments || {};
  const currentUser = userName || 'User';

  const textareaRefs = React.useRef<Record<string, HTMLTextAreaElement | null>>({});

  const handleLabelClick = (key: string) => {
    // Click on label inserts timestamp + username, then focuses textarea with cursor at end of header
    const existing = notes[key] || '';
    const now = new Date();
    const ts = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      + ' ' + now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    const header = `${ts} — ${currentUser}\n`;
    const newVal = header + (existing ? '\n' + existing : '');
    onChange('comments', { ...notes, [key]: newVal });

    // Focus textarea and place cursor at end of the header line
    setTimeout(() => {
      const ta = textareaRefs.current[key];
      if (ta) {
        ta.focus();
        ta.setSelectionRange(header.length, header.length);
      }
    }, 50);
  };

  return (
    <div className="space-y-3">
      {['public', 'process', 'partner'].map((key) => (
        <div key={key}>
          <label
            className={`text-xs font-medium capitalize mb-1 block ${
              isEditing
                ? 'text-blue-600 dark:text-blue-400 cursor-pointer hover:underline'
                : 'text-slate-500 dark:text-slate-400'
            }`}
            onClick={isEditing ? () => handleLabelClick(key) : undefined}
            title={isEditing ? `Click to add timestamped entry to ${key}` : undefined}
          >
            {key}
          </label>
          {isEditing ? (
            <textarea
              ref={(el) => { textareaRefs.current[key] = el; }}
              value={notes[key] ?? ''}
              onChange={(e) => onChange('comments', { ...notes, [key]: e.target.value })}
              className="w-full text-xs p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white min-h-[80px] font-mono"
              placeholder={`Click "${key}" label above to add a timestamped entry`}
            />
          ) : (
            <div className="text-xs text-slate-600 dark:text-slate-300 p-2 bg-slate-50 dark:bg-slate-900/50 rounded min-h-[30px] whitespace-pre-wrap font-mono">
              {notes[key] || '—'}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default TransactionDetail;
