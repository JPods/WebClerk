import React, { useEffect, useMemo, useState } from 'react';
import { getModelNames, getModelDetail, getRecords, getRecord, saveRecord, loadFieldSelections, saveFieldSelections } from '../../api/wcapi';

//

const colBase = 'h-[calc(100vh-140px)] overflow-auto border border-gray-200 rounded-md bg-white';

const AdminWorkbench: React.FC = () => {
  const [modelNames, setModelNames] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState<boolean>(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [records, setRecords] = useState<any[]>([]);
  const [recordsLoading, setRecordsLoading] = useState<boolean>(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  const [allFields, setAllFields] = useState<string[]>([]);
  const [fieldPrefs, setFieldPrefs] = useState(loadFieldSelections());
  const prefsForModel = fieldPrefs[selectedModel] || { list: [], detail: [] };

  useEffect(() => {
    (async () => {
      try {
        setLoadingModels(true);
        setModelsError(null);
        const data = await getModelNames();
        const names = Array.isArray(data.model_names) ? data.model_names : [];
        setModelNames(names);
        // Auto-select first model to populate middle pane immediately
        if (!selectedModel && names.length > 0) {
          setSelectedModel(names[0]);
        }
      } catch (err: any) {
        setModelsError(err?.message || 'Failed to load models');
      } finally {
        setLoadingModels(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedModel) return;
    (async () => {
      try {
        setRecordsLoading(true);
        setRecordsError(null);
        setRecords([]);
        setSelectedId(null);
        setSelectedRecord(null);

        const md = await getModelDetail(selectedModel);
        const rawFields = md?.model?.fields as any;
        let fields: string[] = [];
        if (Array.isArray(rawFields)) {
          fields = rawFields.map((f: any) => (typeof f === 'string' ? f : (f?.name ?? ''))).filter(Boolean);
        } else if (rawFields && typeof rawFields === 'object') {
          fields = Object.keys(rawFields);
        }
        setAllFields(fields);

        const list = await getRecords(selectedModel);
        const recs = Array.isArray(list?.results) ? list.results : [];
        setRecords(recs);
      } catch (err: any) {
        setRecordsError(err?.message || 'Failed to load records');
      } finally {
        setRecordsLoading(false);
      }
    })();
  }, [selectedModel]);

  useEffect(() => {
    if (!selectedModel || selectedId == null) return;
    (async () => {
      const det = await getRecord(selectedModel, selectedId);
      setSelectedRecord(det.record || null);
    })();
  }, [selectedModel, selectedId]);

  const toggleField = (kind: 'list' | 'detail', field: string) => {
    // Determine current preferences for this model
    const current = fieldPrefs[selectedModel] || { list: [], detail: [] };
    const currentList = current[kind] || [];

    // If no explicit prefs yet, we're using a fallback set.
    // Seed the toggle operation from the visible set so toggling adds/removes from what the user actually sees.
    const base = currentList.length === 0
      ? (kind === 'list' ? visibleListFields : allFields)
      : currentList;

    const has = base.includes(field);
    const updated = has ? base.filter((f) => f !== field) : [...base, field];

    const next = {
      ...fieldPrefs,
      [selectedModel]: {
        ...current,
        [kind]: updated,
      },
    } as typeof fieldPrefs;

    setFieldPrefs(next);
    saveFieldSelections(next);
  };

  const bulkSetFields = (kind: 'list' | 'detail', mode: 'all' | 'clear') => {
    if (!selectedModel) return;
    const current = fieldPrefs[selectedModel] || { list: [], detail: [] };
    const nextSet = mode === 'all' ? allFields : [];
    const next = {
      ...fieldPrefs,
      [selectedModel]: {
        ...current,
        [kind]: nextSet,
      },
    } as typeof fieldPrefs;
    setFieldPrefs(next);
    saveFieldSelections(next);
  };

  const visibleListFields = useMemo(() => {
    return prefsForModel.list.length ? prefsForModel.list : ['id', 'ida', 'name', 'email'];
  }, [prefsForModel.list]);

  // Compute visible fields for detail pane: use prefs if set, otherwise show all fields.
  const visibleDetailFields = useMemo(() => {
    return prefsForModel.detail.length ? prefsForModel.detail : allFields;
  }, [prefsForModel.detail, allFields]);

  const handleSave = async () => {
    if (!selectedModel || !selectedRecord) return;
    const payload = { id: selectedRecord.id, ...selectedRecord };
    await saveRecord(selectedModel, payload);
  };

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Admin Workbench</h1>
      <div className="grid grid-cols-12 gap-4">
        {/* Left: Model list (20%) */}
        <div className={`col-span-12 md:col-span-2 ${colBase}`}>
          <div className="p-3 border-b text-sm font-medium bg-gray-50">Models</div>
          {loadingModels && (
            <div className="p-3 text-xs text-gray-500">Loading models…</div>
          )}
          {modelsError && (
            <div className="p-3 text-xs text-red-600">{modelsError}</div>
          )}
          <ul className="divide-y">
            {modelNames.map((name) => (
              <li key={name} className={`p-3 cursor-pointer hover:bg-gray-50 ${selectedModel === name ? 'bg-blue-50' : ''}`} onClick={() => setSelectedModel(name)}>
                <div className="text-sm font-medium">{name}</div>
              </li>
            ))}
          </ul>
        </div>

        {/* Middle: Records list (30%) */}
        <div className={`col-span-12 md:col-span-3 ${colBase}`}>
          <div className="p-3 border-b text-sm font-medium bg-gray-50 flex items-center justify-between">
            <span>Records {selectedModel ? `(${selectedModel})` : ''}</span>
          </div>
          <div className="p-3">
            {recordsLoading && (
              <div className="text-xs text-gray-500">Loading records…</div>
            )}
            {recordsError && (
              <div className="text-xs text-red-600">{recordsError}</div>
            )}
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  {visibleListFields.map((f) => (
                    <th key={f} className="py-1 pr-3">{f}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className={`border-t hover:bg-gray-50 cursor-pointer ${selectedId === r.id ? 'bg-blue-50' : ''}`} onClick={() => setSelectedId(r.id)}>
                    {visibleListFields.map((f) => (
                      <td key={f} className="py-1 pr-3 align-top">{String(r?.[f] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Field selector at bottom */}
          <div className="p-3 border-t bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold">List fields</div>
              <div className="space-x-2">
                <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'all')}>Select all</button>
                <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'clear')}>Clear</button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 max-h-40 overflow-auto">
              {allFields.map((f) => {
                const active = prefsForModel.list.includes(f);
                return (
                  <button key={f} onClick={() => toggleField('list', f)} className={`px-2 py-1 rounded text-xs border ${active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white hover:bg-gray-100'}`}>
                    {f}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Detail form (50%) */}
        <div className={`col-span-12 md:col-span-7 ${colBase}`}>
          <div className="p-3 border-b text-sm font-medium bg-gray-50 flex items-center justify-between">
            <span>Detail {selectedId ? `#${selectedId}` : ''}</span>
            <div className="space-x-2">
              <button className="px-3 py-1 text-sm rounded border hover:bg-gray-100" onClick={handleSave} disabled={!selectedRecord}>Save</button>
            </div>
          </div>
          <div className="p-3 space-y-3">
            {selectedRecord ? (
              <div className="grid grid-cols-2 gap-3">
                {visibleDetailFields
                  .filter((k) => k in (selectedRecord || {}))
                  .map((k) => {
                    const v = (selectedRecord as any)[k];
                    return (
                      <label key={k} className="text-sm">
                        <div className="text-gray-600 mb-1">{k}</div>
                        <input
                          className="w-full border rounded px-2 py-1 text-sm"
                          value={typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v ?? '')}
                          onChange={(e) => setSelectedRecord({ ...selectedRecord, [k]: e.target.value })}
                        />
                      </label>
                    );
                  })}
              </div>
            ) : (
              <div className="text-gray-500 text-sm">Select a record to edit.</div>
            )}
          </div>
          {/* Field selector at bottom */}
          <div className="p-3 border-t bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold">Detail fields</div>
              <div className="space-x-2">
                <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'all')}>Select all</button>
                <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'clear')}>Clear</button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 max-h-40 overflow-auto">
              {allFields.map((f) => {
                const active = visibleDetailFields.includes(f);
                return (
                  <button key={f} onClick={() => toggleField('detail', f)} className={`px-2 py-1 rounded text-xs border ${active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white hover:bg-gray-100'}`}>
                    {f}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminWorkbench;
