/**
 * OrgPage — shared list + detail page for any org type.
 *
 * Config-driven: pass orgType and the page renders with the right fields,
 * actions, related records, and communications. One component, five org types.
 *
 * Usage:
 *   <OrgPage orgType="customer" />
 *   <OrgPage orgType="vendor" />
 */
import DataGrid from "@/components/common/DataGrid";
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import ComponentCard from '@/components/common/ComponentCard';
import ButtonToolbar from '@/components/common/ButtonToolbar';
import FieldConfigBar from '@/components/common/FieldConfigBar';
import ReportMenu from '@/components/common/ReportMenu';
import { useListFieldConfig } from '@/hooks/useListFieldConfig';
import { getOrgConfig, type OrgTypeConfig, type OrgFieldDef } from '../orgConfig';
import CommunicationsPanel from './CommunicationsPanel';
import CustomerHealthCard from '@/components/collections/CustomerHealthCard';

interface OrgPageProps {
  orgType: string;
}

// Build table columns from config
function buildColumns(config: OrgTypeConfig, onEdit: (row: any) => void) {
  return config.listFields.map((f: OrgFieldDef) => {
    const col: any = {
      name: f.label,
      selector: (row: any) => row[f.name] ?? '--',
      sortable: true,
      width: f.width,
    };

    if (f.name === 'id') {
      col.cell = (row: any) => (
        <span onClick={(e) => { e.stopPropagation(); onEdit(row); }}
          className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline">
          {row.id}
        </span>
      );
    } else if (f.type === 'badge') {
      col.cell = (row: any) => {
        const v = row[f.name];
        const colors: Record<string, string> = {
          active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
          prospect: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
          inactive: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
          retired: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
          true: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
          false: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400',
        };
        const display = typeof v === 'boolean' ? (v ? 'Yes' : 'No') : (v || '--');
        return <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${colors[String(v)] || colors.inactive}`}>{display}</span>;
      };
    }
    return col;
  });
}

export default function OrgPage({ orgType }: OrgPageProps) {
  const config = getOrgConfig(orgType);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // List state
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  // Detail state
  const [record, setRecord] = useState<any>(null);
  const [formMode, setFormMode] = useState<'add' | 'edit' | 'view' | null>(null);
  const [editData, setEditData] = useState<Record<string, any>>({});
  const [isDirty, setIsDirty] = useState(false);
  const [detailKey, setDetailKey] = useState(0);
  const [activeTab, setActiveTab] = useState('details');

  if (!config) return <div className="p-8 text-red-500">Unknown org type: {orgType}</div>;

  // Columns from config
  const allColumns = useMemo(() => buildColumns(config, (row) => {
    setRecord(row);
    setFormMode('edit');
    setEditData({ ...row });
    setDetailKey((k) => k + 1);
    setActiveTab('details');
  }), [config]);

  const fieldConfig = useListFieldConfig(orgType, allColumns);

  // Fetch
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getRecords(orgType) as any;
      const items = res?.results || res?.data?.items || [];
      setData(Array.isArray(items) ? items : []);
    } catch (e) {
      dispatch(showToast({ message: `Failed to load ${config.labelPlural}`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [orgType, config.labelPlural, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const res = await getRecords(orgType, { keyword: terms.join(' ') }) as any;
      setData(res?.results || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [orgType]);

  // Filter
  const filteredData = useMemo(() => {
    if (!Object.keys(filterValues).length) return data;
    return data.filter((row: any) =>
      Object.entries(filterValues).every(([k, v]) => !v || String(row[k] || '').toLowerCase().includes(v.toLowerCase()))
    );
  }, [data, filterValues]);

  const visibleColumns = useMemo(() => {
    const base = fieldConfig.visibleColumns;
    if (!columnVisibility.length) return base;
    return base.filter((_: any, i: number) => columnVisibility[i] !== false);
  }, [fieldConfig.visibleColumns, columnVisibility]);

  // CRUD
  const handleAdd = useCallback(() => {
    setRecord(null);
    setFormMode('add');
    setEditData({ org_type: orgType, status: 'active' });
    setDetailKey((k) => k + 1);
    setActiveTab('details');
  }, [orgType]);

  const handleSave = useCallback(async () => {
    try {
      await saveRecord(orgType, editData);
      dispatch(showToast({ message: `${config.label} saved`, type: 'success' }));
      setFormMode(null);
      setRecord(null);
      setIsDirty(false);
      fetchData();
    } catch (e: any) {
      dispatch(showToast({ message: e?.message || 'Save failed', type: 'error' }));
    }
  }, [orgType, editData, config.label, dispatch, fetchData]);

  const handleDelete = useCallback(async (row: any) => {
    if (!confirm(`Delete ${config.label} #${row.id}?`)) return;
    try {
      await deleteRecord(orgType, row.id);
      dispatch(showToast({ message: 'Deleted', type: 'success' }));
      if (record?.id === row.id) { setRecord(null); setFormMode(null); }
      fetchData();
    } catch {
      dispatch(showToast({ message: 'Delete failed', type: 'error' }));
    }
  }, [orgType, config.label, record, dispatch, fetchData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selected.length || !confirm(`Delete ${selected.length} ${config.labelPlural}?`)) return;
    try {
      await Promise.all(selected.map((r) => deleteRecord(orgType, r.id)));
      dispatch(showToast({ message: 'Deleted', type: 'success' }));
      setSelected([]);
      fetchData();
    } catch {
      dispatch(showToast({ message: 'Bulk delete failed', type: 'error' }));
    }
  }, [selected, orgType, config.labelPlural, dispatch, fetchData]);

  // Related records tab content
  const RelatedPanel = ({ rel }: { rel: typeof config.related[0] }) => {
    const [items, setItems] = useState<any[]>([]);
    const [relLoading, setRelLoading] = useState(true);

    useEffect(() => {
      if (!record?.id) return;
      (async () => {
        try {
          const res = await getRecords(rel.model, { [rel.filterField]: record.id }) as any;
          setItems(res?.results || []);
        } catch { /* silent */ }
        finally { setRelLoading(false); }
      })();
    }, [record?.id, rel.model, rel.filterField]);

    if (relLoading) return <div className="text-xs text-gray-400 p-3">Loading...</div>;
    if (!items.length) return <div className="text-xs text-gray-400 p-3">No {rel.label.toLowerCase()} found.</div>;

    return (
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {rel.listFields.map((f) => <th key={f} className="py-1.5 px-2 text-left text-gray-500 font-semibold uppercase text-[10px] tracking-wider">{f}</th>)}
          </tr>
        </thead>
        <tbody>
          {items.map((item: any, i: number) => (
            <tr key={item.id || i} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800">
              {rel.listFields.map((f) => (
                <td key={f} className="py-1.5 px-2">{typeof item[f] === 'object' ? JSON.stringify(item[f]) : String(item[f] ?? '--')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  // Filters from config
  const filters = useMemo(() => {
    return config.listFields
      .filter((f) => f.options)
      .map((f) => ({
        key: f.name, name: f.name, field: f.name, label: f.label,
        type: 'select' as const, options: f.options!,
      }));
  }, [config]);

  return (
    <>
      <ButtonToolbar
        pageTitle={config.labelPlural}
        title={config.label}
        modelKey={orgType}
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selected}
        selectedCount={selected.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={fetchData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={allColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey={`${orgType}-list`}
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
        customActions={
          <button onClick={fieldConfig.togglePanel}
            className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
              fieldConfig.showPanel ? 'bg-blue-100 text-blue-700 border-blue-300' : 'text-gray-600 border-gray-300 hover:bg-gray-100'
            }`}>Cols</button>
        }
      />

      <FieldConfigBar
        show={fieldConfig.showPanel}
        allKeys={fieldConfig.allKeys}
        effectiveKeys={fieldConfig.effectiveKeys}
        onToggle={fieldConfig.toggleField}
        onAll={fieldConfig.setAll}
        onClear={fieldConfig.clearAll}
        onMove={fieldConfig.moveField}
        onClose={fieldConfig.togglePanel}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-1">
        {/* List */}
        <div className={formMode ? 'lg:col-span-1' : 'lg:col-span-3'}>
          <ComponentCard>
            <DataGrid
              ref={tableRef}
              data={filteredData}
              columns={visibleColumns}
              title={config.label}
              loading={loading}
              enableExport
              enableSelection
              enableDatabaseSearch
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              onSelectionChange={setSelected}
              onDeleteSelected={handleBulkDelete}
              exportFileName={`${orgType}_export`}
              searchPlaceholder={`Search ${config.labelPlural.toLowerCase()}...`}
              noDataMessage={`No ${config.labelPlural.toLowerCase()} found`}
              onRowDoubleClicked={(row: any) => {
                setRecord(row);
                setFormMode('view');
                setEditData({ ...row });
                setDetailKey((k) => k + 1);
              }}
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              hideHeader
            />
          </ComponentCard>
        </div>

        {/* Detail */}
        {formMode && (
          <div className="lg:col-span-2" key={detailKey}>
            <ComponentCard>
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {formMode === 'add' ? `New ${config.label}` : editData.display_name || `${config.label} #${editData.id}`}
                  </h2>
                  {editData.id && (
                    <div className="flex gap-2 mt-1">
                      {/* Org type badges — show all relationships */}
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded" style={{ background: config.color + '20', color: config.color }}>
                        {config.label}
                      </span>
                      {editData.org_type && editData.org_type !== orgType && (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          Also: {editData.org_type}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isDirty && <span className="text-xs text-amber-600 font-medium">unsaved</span>}
                  {editData.id && <ReportMenu modelName={orgType} recordId={editData.id} />}
                  <button onClick={handleSave}
                    className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700">Save</button>
                  <button onClick={() => { setFormMode(null); setRecord(null); setIsDirty(false); }}
                    className="px-3 py-1.5 text-xs text-gray-500 rounded border border-gray-300 hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700">Close</button>
                </div>
              </div>

              {/* Action buttons */}
              {config.actions.length > 0 && editData.id && (
                <div className="flex gap-2 mb-4">
                  {config.actions.map((a) => (
                    <button key={a.label}
                      onClick={() => {
                        if (a.route) navigate(a.route.replace('{id}', String(editData.id)));
                        else alert(`Create ${a.model} for ${config.label} #${editData.id} — not yet implemented`);
                      }}
                      className={`px-3 py-1.5 text-xs font-medium rounded transition ${
                        a.variant === 'primary' ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'border border-gray-300 text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700'
                      }`}
                    >{a.label}</button>
                  ))}
                </div>
              )}

              {/* Tabs */}
              <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4">
                {['details', 'communications', ...config.related.map((r) => r.label)].map((tab) => (
                  <button key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 text-xs font-medium transition border-b-2 -mb-px ${
                      activeTab === tab
                        ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                  >{tab === 'details' ? 'Details' : tab === 'communications' ? 'Communications' : tab}</button>
                ))}
              </div>

              {/* Tab content */}
              {activeTab === 'details' && (
                <div className="space-y-3">
                  {orgType === 'customer' && editData.id && (
                    <CustomerHealthCard customerId={editData.id} />
                  )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {config.formFields.map((f) => (
                    <div key={f.name}>
                      <label className="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">{f.label}</label>
                      {f.type === 'readonly' ? (
                        <div className="px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 text-gray-500 font-mono">
                          {String(editData[f.name] ?? '--')}
                        </div>
                      ) : f.type === 'select' ? (
                        <select value={editData[f.name] || ''}
                          onChange={(e) => { setEditData((d) => ({ ...d, [f.name]: e.target.value })); setIsDirty(true); }}
                          className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200">
                          <option value="">--</option>
                          {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      ) : (
                        <input type={f.type === 'email' ? 'email' : f.type === 'phone' ? 'tel' : 'text'}
                          value={editData[f.name] || ''}
                          onChange={(e) => { setEditData((d) => ({ ...d, [f.name]: e.target.value })); setIsDirty(true); }}
                          className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                        />
                      )}
                    </div>
                  ))}
                </div>
                </div>
              )}

              {activeTab === 'communications' && (
                <CommunicationsPanel contactId={editData.contact_id || editData.contact?.id || null} orgType={orgType} />
              )}

              {config.related.map((rel) =>
                activeTab === rel.label ? <RelatedPanel key={rel.label} rel={rel} /> : null
              )}
            </ComponentCard>
          </div>
        )}
      </div>
    </>
  );
}
