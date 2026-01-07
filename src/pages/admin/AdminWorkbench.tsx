import React, { useEffect, useMemo, useState } from 'react';
import { useAppSelector } from '../../store/hooks';
import { NetworkInfo } from '../../routes/network';
import { getModelNames, getModelDetail, getRecords, getRecord, saveRecord, getWorkbenchFieldsSetting, saveWorkbenchFieldsSetting, getAllWorkbenchFieldsSettings } from '../../api/wcapi';

//

type ModelListItem = {
  name: string;
  label: string;
};

type ModelGroup = {
  appId: string;
  appLabel: string;
  models: ModelListItem[];
};

const toTitleCase = (value: string): string => {
  return value
    .replace(/[_\-]+/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const ALPHA_OPTIONS: Intl.CollatorOptions = { sensitivity: 'base', numeric: false };

const groupModelNames = (names: string[]): ModelGroup[] => {
  const groups = new Map<string, ModelGroup>();

  names.forEach((fullName) => {
    const hasSeparator = fullName.includes('.');
    const [rawApp, rawModel] = hasSeparator ? fullName.split('.') : ['default', fullName];
    const appId = (rawApp || 'default').toLowerCase();
    const appLabel = toTitleCase(rawApp || 'Default');
    const modelLabelSource = rawModel || fullName;
    const modelLabel = toTitleCase(modelLabelSource);

    if (!groups.has(appId)) {
      groups.set(appId, {
        appId,
        appLabel,
        models: [],
      });
    }

    groups.get(appId)?.models.push({
      name: fullName,
      label: modelLabel,
    });
  });

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      models: group.models
        .slice()
        .sort((a, b) => a.label.localeCompare(b.label, undefined, ALPHA_OPTIONS)),
    }))
    .sort((a, b) => a.appLabel.localeCompare(b.appLabel, undefined, ALPHA_OPTIONS));
};

const colBase = 'flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm';

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
  const [workbenchSetting, setWorkbenchSetting] = useState<{ list: string[]; detail: string[] } | null>(null);
  const [workbenchSettingsMap, setWorkbenchSettingsMap] = useState<Record<string, { list: string[]; detail: string[] }>>({});
  const { isAuthenticated } = useAppSelector((s) => s.auth);
  const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
  const [lastModelsFetchAt, setLastModelsFetchAt] = useState<number | null>(null);
  const [isModelNavOpen, setIsModelNavOpen] = useState(false);

  const modelGroups = useMemo(() => groupModelNames(modelNames), [modelNames]);
  const totalModelCount = useMemo(() => modelGroups.reduce((sum, group) => sum + group.models.length, 0), [modelGroups]);

  // Load model names only when a token is present (avoids 401s pre-login)
  useEffect(() => {
    const hasToken = !!(typeof window !== 'undefined' && localStorage.getItem('accessToken'));
    if (!hasToken) return;
    (async () => {
      try {
        setLoadingModels(true);
        setModelsError(null);
        const data = await getModelNames();
        const names = Array.isArray(data.model_names) ? data.model_names : [];
        const sortedNames = names.slice().sort((a, b) => a.localeCompare(b));
        setModelNames(sortedNames);
        setLastModelsFetchAt(Date.now());

        // Load all workbench fields settings
        const settings = await getAllWorkbenchFieldsSettings();
        const map: Record<string, { list: string[]; detail: string[] }> = {};
        settings.forEach(s => {
          map[s.model_name] = s.data;
        });
        setWorkbenchSettingsMap(map);
      } catch (err: any) {
        setModelsError(err?.message || 'Failed to load models');
      } finally {
        setLoadingModels(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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

        // Set workbench fields setting from map
        setWorkbenchSetting(workbenchSettingsMap[selectedModel] || null);
      } catch (err: any) {
        setRecordsError(err?.message || 'Failed to load records');
      } finally {
        setRecordsLoading(false);
      }
    })();
  }, [selectedModel, workbenchSettingsMap]);

  useEffect(() => {
    if (selectedModel || modelGroups.length === 0) return;
    const first = modelGroups[0]?.models[0];
    if (first) {
      setSelectedModel(first.name);
    }
  }, [modelGroups, selectedModel]);

  const handleSelectModel = (modelName: string) => {
    setSelectedModel(modelName);
    setIsModelNavOpen(false);
  };

  const modelListContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
        <span className="text-sm font-medium text-gray-700">WebClerk3 apps</span>
        <button
          type="button"
          onClick={() => setIsModelNavOpen(false)}
          className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 md:hidden"
        >
          Close
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {loadingModels && (
          <div className="px-2 text-xs text-gray-500">Loading models…</div>
        )}
        {modelsError && (
          <div className="px-2 text-xs text-red-600">{modelsError}</div>
        )}
        {!loadingModels && !modelsError && modelGroups.length === 0 && (
          <div className="px-2 text-xs text-gray-500">No models available.</div>
        )}
        {!loadingModels && !modelsError && (
          <ul className="space-y-4">
            {modelGroups.map((group) => (
              <li key={group.appId}>
                <p className="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {group.appLabel} ({group.models.length})
                </p>
                <ul className="mt-1 space-y-1">
                  {group.models.map((model) => {
                    const active = selectedModel === model.name;
                    return (
                      <li key={model.name}>
                        <button
                          type="button"
                          onClick={() => handleSelectModel(model.name)}
                          className={`w-full rounded-md px-3 py-2 text-left text-sm transition ${
                            active
                              ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-200'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <div className="font-medium">{model.label}</div>
                          <div className="text-xs text-gray-400">{model.name}</div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );

  useEffect(() => {
    if (!selectedModel || selectedId == null) return;
    (async () => {
      const det = await getRecord(selectedModel, selectedId);
      setSelectedRecord(det.record || null);
    })();
  }, [selectedModel, selectedId]);

  const toggleField = async (kind: 'list' | 'detail', field: string) => {
    if (!selectedModel) return;

    // Get current setting or create default
    const current = workbenchSetting || { list: [], detail: [] };
    const currentList = current[kind] || [];

    // If no explicit prefs yet, seed from visible set
    const base = currentList.length === 0
      ? (kind === 'list' ? visibleListFields : allFields)
      : currentList;

    const has = base.includes(field);
    const updated = has ? base.filter((f: string) => f !== field) : [...base, field];

    const nextSetting = {
      ...current,
      [kind]: updated,
    };

    setWorkbenchSetting(nextSetting);
    // Update the map
    setWorkbenchSettingsMap(prev => ({ ...prev, [selectedModel]: nextSetting }));

    // Save to API
    try {
      const existing = await getWorkbenchFieldsSetting(selectedModel);
      const settingToSave = {
        id: existing?.id,
        model_name: selectedModel,
        purpose: 'workbench_fields',
        data: nextSetting,
      };
      await saveWorkbenchFieldsSetting(settingToSave);
    } catch (err) {
      console.error('Failed to save field settings:', err);
    }
  };

  const bulkSetFields = async (kind: 'list' | 'detail', mode: 'all' | 'clear') => {
    if (!selectedModel) return;
    const current = workbenchSetting || { list: [], detail: [] };
    const nextSet = mode === 'all' ? allFields : [];
    const nextSetting = {
      ...current,
      [kind]: nextSet,
    };
    setWorkbenchSetting(nextSetting);
    // Update the map
    setWorkbenchSettingsMap(prev => ({ ...prev, [selectedModel]: nextSetting }));

    // Save to API
    try {
      const existing = await getWorkbenchFieldsSetting(selectedModel);
      const settingToSave = {
        id: existing?.id,
        model_name: selectedModel,
        purpose: 'workbench_fields',
        data: nextSetting,
      };
      await saveWorkbenchFieldsSetting(settingToSave);
    } catch (err) {
      console.error('Failed to save field settings:', err);
    }
  };

  const visibleListFields = useMemo(() => {
    return workbenchSetting?.list.length ? workbenchSetting.list : ['id', 'ida', 'name', 'email'];
  }, [workbenchSetting?.list]);

  // Compute visible fields for detail pane: use prefs if set, otherwise show all fields.
  const visibleDetailFields = useMemo(() => {
    return workbenchSetting?.detail.length ? workbenchSetting.detail : allFields;
  }, [workbenchSetting?.detail, allFields]);

  const handleSave = async () => {
    if (!selectedModel || !selectedRecord) return;
    const payload = { id: selectedRecord.id, ...selectedRecord };
    await saveRecord(selectedModel, payload);
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsModelNavOpen(true)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 text-slate-600 transition hover:bg-slate-100 md:hidden"
            aria-label="Open model navigation"
          >
            <span className="flex flex-col items-center gap-1.5">
              <span className="block h-0.5 w-5 bg-current" />
              <span className="block h-0.5 w-5 bg-current" />
              <span className="block h-0.5 w-5 bg-current" />
            </span>
          </button>
          <div>
            <p className="hidden text-xs font-semibold uppercase tracking-wide text-slate-500 md:block">TailAdmin</p>
            <h1 className="text-lg font-semibold text-slate-900">Admin Workbench</h1>
          </div>
        </div>
        <div className="text-xs text-slate-500">
          {totalModelCount ? `${totalModelCount} models` : 'No models'}
        </div>
      </header>
      <div className="border-b border-slate-200 bg-white px-4 py-2 text-xs text-slate-600">
        <div className="flex flex-wrap items-center gap-4">
          <div><span className="font-semibold">API</span>: {NetworkInfo.API_URL || '(unset)'}</div>
          <div><span className="font-semibold">Auth</span>: {token ? 'token ✓' : 'no token'} ({isAuthenticated ? 'auth ✓' : 'auth ✗'})</div>
          <div><span className="font-semibold">Models</span>: {loadingModels ? 'loading…' : (totalModelCount ? `${totalModelCount} loaded` : 'none')}</div>
          {lastModelsFetchAt && (
            <div><span className="font-semibold">Last fetch</span>: {new Date(lastModelsFetchAt).toLocaleTimeString()}</div>
          )}
          {modelsError && (
            <div className="text-red-600"><span className="font-semibold">Error</span>: {modelsError}</div>
          )}
        </div>
      </div>
      <div className="flex flex-1 overflow-hidden">
        {isModelNavOpen && (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div className="absolute inset-0 bg-slate-900/40" onClick={() => setIsModelNavOpen(false)} aria-hidden="true" />
            <div className="relative z-10 h-full w-72">
              <div className={`${colBase} h-full rounded-none shadow-lg`}>{modelListContent}</div>
            </div>
          </div>
        )}
        <div className="flex flex-1 flex-col overflow-hidden p-4 md:p-6">
          <div className="flex h-full min-h-0 flex-col gap-4 md:flex-row">
            <div className="hidden md:flex md:w-64 md:flex-shrink-0">
              <div className={colBase}>{modelListContent}</div>
            </div>
            <div className="flex flex-1 flex-col gap-4 md:flex-row">
              <div className={`flex w-full flex-col md:w-96 xl:w-[24rem] ${colBase}`}>
                <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
                  <span className="text-sm font-medium text-gray-700">
                    Records {selectedModel ? `(${selectedModel})` : ''}
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto px-4 py-4">
                  {recordsLoading && (
                    <div className="text-xs text-gray-500">Loading records…</div>
                  )}
                  {recordsError && (
                    <div className="text-xs text-red-600">{recordsError}</div>
                  )}
                  {!recordsLoading && !recordsError && records.length === 0 && (
                    <div className="text-xs text-gray-500">No records found.</div>
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
                        <tr
                          key={r.id}
                          className={`border-t hover:bg-gray-50 cursor-pointer ${selectedId === r.id ? 'bg-blue-50' : ''}`}
                          onClick={() => setSelectedId(r.id)}
                        >
                          {visibleListFields.map((f) => (
                            <td key={f} className="py-1 pr-3 align-top">{String(r?.[f] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-xs font-semibold">List fields</div>
                    <div className="space-x-2">
                      <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'all')}>Select all</button>
                      <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'clear')}>Clear</button>
                    </div>
                  </div>
                  <div className="flex max-h-40 flex-wrap gap-2 overflow-auto">
                    {allFields.map((f: string) => {
                      const active = workbenchSetting?.list.includes(f) || false;
                      return (
                        <button
                          key={f}
                          onClick={() => toggleField('list', f)}
                          className={`px-2 py-1 rounded text-xs border ${active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white hover:bg-gray-100'}`}
                        >
                          {f}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div className={`flex flex-1 flex-col ${colBase}`}>
                <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
                  <span className="text-sm font-medium text-gray-700">Detail {selectedId ? `#${selectedId}` : ''}</span>
                  <div className="space-x-2">
                    <button className="px-3 py-1 text-sm rounded border hover:bg-gray-100" onClick={handleSave} disabled={!selectedRecord}>Save</button>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto px-4 py-4">
                  {selectedRecord ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {visibleDetailFields
                        .filter((k) => k in (selectedRecord || {}))
                        .map((k) => {
                          const v = (selectedRecord as any)[k];
                          return (
                            <label key={k} className="text-sm">
                              <div className="mb-1 text-gray-600">{k}</div>
                              <input
                                className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                                value={typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v ?? '')}
                                onChange={(e) => setSelectedRecord({ ...selectedRecord, [k]: e.target.value })}
                              />
                            </label>
                          );
                        })}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500">Select a record to edit.</div>
                  )}
                </div>
                <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-xs font-semibold">Detail fields</div>
                    <div className="space-x-2">
                      <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'all')}>Select all</button>
                      <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'clear')}>Clear</button>
                    </div>
                  </div>
                  <div className="flex max-h-40 flex-wrap gap-2 overflow-auto">
                    {allFields.map((f) => {
                      const active = visibleDetailFields.includes(f);
                      return (
                        <button
                          key={f}
                          onClick={() => toggleField('detail', f)}
                          className={`px-2 py-1 rounded text-xs border ${active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white hover:bg-gray-100'}`}
                        >
                          {f}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminWorkbench;
