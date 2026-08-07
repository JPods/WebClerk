/* LastChecked: 2026-08-03 | WhereUsed: Router, protectedRoutesConfig | WhoCreated: Claude */
/**
 * ItemDetailJson — JSON-driven item detail page.
 *
 * Replaces ItemDetail.tsx (2,968 lines).
 * 3-column header (Item|Pricing|Inventory) + 8 tabs.
 * Tabs use product panels (BomPanel, SerialPanel, ProductListPanel).
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, saveRecord } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import DetailToolbar from '@/components/common/DetailToolbar';
import { BomPanel, SerialPanel, ProductListPanel, WarehouseCard, VariantCard, XRefCard, SpecCard } from '@/apps/products/components';
import InventoryLayersPanel from '@/apps/products/components/InventoryLayersPanel';
import CycleCountPanel from '@/apps/products/components/CycleCountPanel';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import { DocumentsPanel } from '@/apps/common/components/panels';
import ActionsPanel from '@/apps/common/components/panels/ActionsPanel';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ItemDetailJsonProps {
  itemId?: number;
  recordId?: number;
  inline?: boolean;
  onRegisterActions?: (actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => void;
  onEditStateChange?: (editing: boolean) => void;
  [key: string]: any;
}

const ItemDetailJson: React.FC<ItemDetailJsonProps> = ({ itemId, recordId: propId, inline, onRegisterActions, onEditStateChange }) => {
  const resolvedPropId = propId || itemId;
  const params = useParams<{ id?: string }>();
  const recordId = resolvedPropId || (params.id ? Number(params.id) : 0);
  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};

  const { layout, loading: layoutLoading, invalidate: invalidateLayout } = useDetailLayout('item');

  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [designMode, setDesignMode] = useState(false);
  const [designLayout, setDesignLayout] = useState<any>(null);

  const activeLayout = designMode && designLayout ? designLayout : layout;
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;

  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord('item', recordId);
      const record = response?.record || response;
      setData(record);
      setEditData(record);
    } catch {
      dispatch(showToast({ message: 'Failed to load item', type: 'error' }));
    }
    setLoading(false);
  }, [recordId, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (autoEdit && data && !isEditing) { setEditData({ ...data }); setIsEditing(true); }
  }, [autoEdit, data]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEdit = () => { setEditData({ ...data }); setIsEditing(true); };
  const handleCancel = () => { setEditData(data); setIsEditing(false); };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      if (!field.includes('.')) return { ...prev, [field]: value };
      const parts = field.split('.');
      const clone = JSON.parse(JSON.stringify(prev));
      let obj = clone;
      for (let i = 0; i < parts.length - 1; i++) {
        if (obj[parts[i]] == null || typeof obj[parts[i]] !== 'object') obj[parts[i]] = {};
        obj = obj[parts[i]];
      }
      obj[parts[parts.length - 1]] = value;
      return clone;
    });
  }, []);

  const handleSave = async () => {
    if (!editData) return;
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      await saveRecord('item', clean);
      dispatch(showToast({ message: 'Item saved', type: 'success' }));
      setIsEditing(false);
      fetchData();
    } catch {
      dispatch(showToast({ message: 'Save failed', type: 'error' }));
    }
    setSaving(false);
  };

  const handleAddNew = async () => {
    try {
      const res = await saveRecord('item', { is_active: true });
      const newId = res?.record?.id || res?.id;
      if (newId) windowManager.ensureWindow(`/item/${newId}`, `Item #${newId}`);
    } catch {
      dispatch(showToast({ message: 'Failed to create item', type: 'error' }));
    }
  };

  // Register actions for parent toolbar
  useEffect(() => {
    if (onRegisterActions) onRegisterActions({ save: handleSave, cancel: handleCancel, addNew: handleAddNew });
  }, [onRegisterActions, handleSave, handleCancel, handleAddNew]);
  useEffect(() => {
    if (onEditStateChange) onEditStateChange(isEditing);
  }, [isEditing, onEditStateChange]);

  if (loading || layoutLoading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading item...</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Item not found</div>;
  }

  const currentData = isEditing ? editData : data;
  const headerSection = activeLayout.sections?.find((s: any) => s.type === 'header') as any;
  const tabsSection = activeLayout.sections?.find((s: any) => s.type === 'tabs') as any;
  const columns = headerSection?.columns || [];
  const itemCode = data.ida || data.item_code || `#${data.id}`;
  const tabs = tabsSection?.tabs || [
    { label: 'Summary', content: 'summary' },
    { label: 'BOM', content: 'bom' },
    { label: 'XRef', content: 'xref' },
    { label: 'Serials', content: 'serials' },
    { label: 'Specs', content: 'specs' },
    { label: 'Layers', content: 'layers' },
    { label: 'Counts', content: 'counts' },
    { label: 'History', content: 'history' },
    { label: 'Documents', content: 'documents' },
    { label: 'Notes', content: 'notes' },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc="item-detail" data-zone="db.detail.form | .item-detail | ItemDetailJson.tsx">
      {/* Toolbar — hidden when inline (DataBrowser owns the toolbar) */}
      {!inline && (
        <DetailToolbar
          data={data}
          currentData={currentData}
          modelName="item"
          layout={activeLayout}
          isEditing={isEditing}
          saving={saving}
          companyInfo={companyInfo}
          logos={logos}
          documentText={documentText}
          userRole={authUser?.role}
          onEdit={handleEdit}
          onAddNew={handleAddNew}
          onSave={handleSave}
          onCancel={handleCancel}
          designMode={designMode}
          onToggleDesign={() => {
            if (designMode) { setDesignMode(false); setDesignLayout(null); invalidateLayout(); }
            else { setDesignMode(true); if (layout) setDesignLayout(JSON.parse(JSON.stringify(layout))); }
          }}
        />
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Header columns */}
        {headerSection && (
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
            {columns.map((col: any, colIdx: number) => (
              <div key={colIdx} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1">
                  <span>{col.title}</span>
                  {colIdx === 0 && data.ida && (
                    <span className="font-mono font-normal text-slate-400 dark:text-slate-500">{data.ida}</span>
                  )}
                </div>
                {(col.fields || []).map((f: any) => (
                  <FieldRow
                    key={f.field}
                    field={f.field}
                    label={f.label}
                    data={currentData}
                    isEditing={isEditing}
                    options={f.options}
                    fieldType={f.type}
                    help={f.help}
                    onChange={handleFieldChange}
                  />
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="flex border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
            {tabs.map((tab: any) => (
              <button
                key={tab.content}
                onClick={() => setActiveTab(tab.content)}
                className={`px-4 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.content
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="p-2">
            {activeTab === 'summary' && (
              <div className="p-4 text-xs text-slate-400">Item summary — sales history, margins, usage trends</div>
            )}
            {activeTab === 'bom' && (
              <BomPanel itemId={data.id} itemCode={itemCode} />
            )}
            {activeTab === 'xref' && (
              <ProductListPanel
                model="item_xref" itemId={data.id} itemCode={itemCode}
                filterField="item_id"
                CardComponent={XRefCard}
                headers={['Type', 'XRef Code', 'Description', 'Org']}
                headerWidths={['w-16', 'w-28', 'flex-1', 'w-20']}
                onCardClick={(id) => windowManager.ensureWindow(`/item_xref?id=${id}`, `XRef #${id}`)}
              />
            )}
            {activeTab === 'serials' && (
              <SerialPanel itemId={data.id} itemCode={itemCode} />
            )}
            {activeTab === 'specs' && (
              <ProductListPanel
                model="specification" itemId={data.id} itemCode={itemCode}
                filterField="item_id"
                CardComponent={SpecCard}
                headers={['Name', 'Value', 'Unit', 'Category']}
                headerWidths={['w-32', 'w-24', 'w-16', 'flex-1']}
              />
            )}
            {activeTab === 'layers' && (
              <InventoryLayersPanel itemId={data.id} />
            )}
            {activeTab === 'counts' && (
              <CycleCountPanel itemId={data.id} itemCode={itemCode} />
            )}
            {activeTab === 'history' && (
              <div className="p-4 text-xs text-slate-400">Transaction history — coming soon</div>
            )}
            {activeTab === 'documents' && (
              <DocumentsPanel parent_model="item" parentId={data.id} data={data.refs?.links?.document} isEditing={isEditing} />
            )}
            {activeTab === 'notes' && (
              <CommentsPanel entityType="item" entityId={data.id} data={data.comments} isEditing={isEditing}
                onChange={(comments: any) => handleFieldChange('comments', comments)} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(ItemDetailJson, 'ItemDetailJson', 'indigo', 'apps/products/pages/ItemDetailJson.tsx');
