/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createBlankRecord } from '../../tools/createBlankRecord';
import { useSearchParams } from 'react-router-dom';
import { useAppSelector } from '../../store/hooks';
import { NetworkInfo } from '../../routes/network';
import { getModelNames, getModelDetail, getRecords, getRecord, saveRecord, getWorkbenchFieldsSetting, saveWorkbenchFieldsSetting, getAllWorkbenchFieldsSettings } from '../../api/wcapi';

// Dev mode: return raw field names for alignment
const toTitleCase = (value: string): string => value;

const colBase = 'relative flex h-full min-h-0 flex-col rounded-lg border border-gray-200 bg-white shadow-sm';

type WorkbenchRecord = {
  id?: number | string;
  [key: string]: unknown;
};

type WorkbenchFieldsSetting = {
  list: string[];
  detail: string[];
};

type ModelDetailData = {
  model?: {
    fields?: unknown;
  };
};

type ModelRecordsData = {
  results?: unknown;
};

type ModelRecordData = {
  record?: unknown;
};

const defaultFieldsSetting: WorkbenchFieldsSetting = { list: [], detail: [] };

const isPlainObject = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
};

const toWorkbenchRecord = (value: unknown): WorkbenchRecord | null => {
  if (!isPlainObject(value)) return null;
  return value as WorkbenchRecord;
};

const toWorkbenchRecordList = (value: unknown): WorkbenchRecord[] => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => toWorkbenchRecord(item))
    .filter((item): item is WorkbenchRecord => item !== null);
};

const toFieldName = (field: unknown): string | null => {
  if (typeof field === 'string') return field;
  if (isPlainObject(field)) {
    const name = field['name'];
    if (typeof name === 'string') {
      return name;
    }
  }
  return null;
};

const toNumericId = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (isPlainObject(error)) {
    const message = error['message'];
    if (typeof message === 'string') {
      return message;
    }
  }
  return fallback;
};

const AdminWorkbench: React.FC = () => {
  const [modelNames, setModelNames] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState<boolean>(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [records, setRecords] = useState<WorkbenchRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState<boolean>(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<WorkbenchRecord | null>(null);
  const [allFields, setAllFields] = useState<string[]>([]);
  const [workbenchSetting, setWorkbenchSetting] = useState<WorkbenchFieldsSetting | null>(null);
  const [workbenchSettingsMap, setWorkbenchSettingsMap] = useState<Record<string, WorkbenchFieldsSetting>>({});
  const { isAuthenticated, user } = useAppSelector((s) => s.auth);
  const [lastModelsFetchAt, setLastModelsFetchAt] = useState<number | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const previousModelParam = useRef<string | null>(null);

  const handleSelectModel = useCallback((name: string) => {
    setSelectedModel((prev) => (prev === name ? prev : name));
  }, []);

  const modelParam = searchParams.get('model');
  const totalModelCount = modelNames.length;
  const selectedModelLabel = useMemo(() => {
    if (!selectedModel) return '';
    const parts = selectedModel.split('.');
    return toTitleCase(parts[parts.length - 1] || selectedModel);
  }, [selectedModel]);

  const roleLabel = useMemo(() => {
    const roleValue = user?.role;
    if (!roleValue) return 'Not assigned';
    if (Array.isArray(roleValue)) {
      return roleValue.length ? roleValue.join(', ') : 'Not assigned';
    }
    return roleValue;
  }, [user?.role]);

  useEffect(() => {
    if (!modelNames.length) {
      if (selectedModel) {
        setSelectedModel('');
      }
      setRecords([]);
      setSelectedId(null);
      setSelectedRecord(null);
      previousModelParam.current = modelParam;
      return;
    }

    if (modelParam && modelNames.includes(modelParam)) {
      if (previousModelParam.current !== modelParam) {
        previousModelParam.current = modelParam;
        if (selectedModel !== modelParam) {
          setSelectedModel(modelParam);
        }
      }
      return;
    }

    previousModelParam.current = modelParam;

    if (!selectedModel || !modelNames.includes(selectedModel)) {
      setSelectedModel(modelNames[0]);
    }
  }, [modelNames, modelParam, selectedModel]);

  useEffect(() => {
    if (!selectedModel && !modelParam) return;

    const next = new URLSearchParams(searchParams);

    if (selectedModel) {
      if (modelParam === selectedModel) return;
      next.set('model', selectedModel);
      setSearchParams(next, { replace: true });
      return;
    }

    if (modelParam) {
      next.delete('model');
      setSearchParams(next, { replace: true });
    }
  }, [modelParam, searchParams, selectedModel, setSearchParams]);

  // Load model names only when authenticated (avoids 401s pre-login)
  useEffect(() => {
    if (!isAuthenticated) return;
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
      } catch (error) {
        setModelsError(getErrorMessage(error, 'Failed to load models'));
      } finally {
        setLoadingModels(false);
      }
    })();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!selectedModel) return;
    if (modelNames.length && !modelNames.includes(selectedModel)) return;
    (async () => {
      try {
        setRecordsLoading(true);
        setRecordsError(null);
        setRecords([]);
        setSelectedId(null);
        setSelectedRecord(null);

        const md = (await getModelDetail(selectedModel)) as ModelDetailData;
        const rawFields = md?.model?.fields;
        let fields: string[] = [];
        if (Array.isArray(rawFields)) {
          fields = rawFields
            .map((field) => toFieldName(field))
            .filter((name): name is string => Boolean(name));
        } else if (isPlainObject(rawFields)) {
          fields = Object.keys(rawFields);
        }
        setAllFields(fields);

        const list = (await getRecords(selectedModel)) as ModelRecordsData;
        setRecords(toWorkbenchRecordList(list?.results));

        // Set workbench fields setting from map
        setWorkbenchSetting(workbenchSettingsMap[selectedModel] || null);
      } catch (error) {
        setRecordsError(getErrorMessage(error, 'Failed to load records'));
      } finally {
        setRecordsLoading(false);
      }
    })();
  }, [modelNames, selectedModel, workbenchSettingsMap]);

  useEffect(() => {
    if (!selectedModel || selectedId == null) return;
    (async () => {
      const det = (await getRecord(selectedModel, selectedId)) as ModelRecordData;
      const nextRecord = toWorkbenchRecord(det?.record);
      setSelectedRecord(nextRecord);
    })();
  }, [selectedModel, selectedId]);

  const toggleField = async (kind: 'list' | 'detail', field: string) => {
    if (!selectedModel) return;

    // Get current setting or create default
    const current = workbenchSetting ?? defaultFieldsSetting;
    const currentList = current[kind] || [];

    // If no explicit prefs yet, seed from visible set
    const base = currentList.length === 0
      ? (kind === 'list' ? visibleListFields : allFields)
      : currentList;

    const has = base.includes(field);
    const updated = has ? base.filter((f: string) => f !== field) : [...base, field];

    const nextSetting: WorkbenchFieldsSetting = {
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
    } catch (error) {
      console.error('Failed to save field settings:', error);
    }
  };

  const bulkSetFields = async (kind: 'list' | 'detail', mode: 'all' | 'clear') => {
    if (!selectedModel) return;
    const current = workbenchSetting ?? defaultFieldsSetting;
    const nextSet = mode === 'all' ? allFields : [];
    const nextSetting: WorkbenchFieldsSetting = {
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
    } catch (error) {
      console.error('Failed to save field settings:', error);
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
    const payload: WorkbenchRecord = { ...selectedRecord };
    await saveRecord(selectedModel, payload);
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <p className="hidden text-xs font-semibold uppercase tracking-wide text-slate-500 md:block">WebClerk 3.0</p>
          <h1 className="text-lg font-semibold text-slate-900">Admin Workbench</h1>
          <p className="mt-0.5 text-xs text-slate-400">Role: {roleLabel}</p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>{totalModelCount ? `${totalModelCount} models` : 'No models'}</div>
          {selectedModel && (
            <div className="mt-0.5 text-[11px] text-slate-400">{selectedModel}</div>
          )}
        </div>
      </header>
      <div className="border-b border-slate-200 bg-white px-4 py-2 text-xs text-slate-600">
        <div className="flex flex-wrap items-center gap-4">
          <div><span className="font-semibold">API</span>: {NetworkInfo.API_URL || '(unset)'}</div>
          <div><span className="font-semibold">Auth</span>: {isAuthenticated ? 'auth ✓' : 'auth ✗'}</div>
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
        <div className="flex flex-1 flex-col overflow-hidden p-4 md:p-6">
          <div className="flex h-full min-h-0 flex-col gap-4 md:flex-row">
            <div className={`${colBase} w-full md:basis-[20%] md:max-w-xs md:flex-none`}>
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-gray-700">Models</span>
                  <p className="text-xs text-gray-400">Choose a model to inspect</p>
                </div>
              </div>
              <div className="flex items-center justify-between px-4 py-2">
                <div className="text-xs font-semibold">Records List</div>
                <button
                  className="px-3 py-1 text-xs rounded border bg-blue-600 text-white hover:bg-blue-700"
                  onClick={() => {
                    if (selectedModel && allFields.length) {
                      const blankRecord = createBlankRecord(selectedModel, allFields);
                      setRecords(prev => [blankRecord, ...prev]);
                      setSelectedId(null);
                      setSelectedRecord(blankRecord);
                    }
                  }}
                >Add Record</button>
              </div>
              <div className="flex-1 overflow-y-auto px-4 py-4">
                {loadingModels && (
                  <div className="text-xs text-gray-500">Loading models…</div>
                )}
                {!loadingModels && modelsError && (
                  <div className="text-xs text-red-600">{modelsError}</div>
                )}
                {!loadingModels && !modelsError && modelNames.length === 0 && (
                  <div className="text-xs text-gray-500">No models available.</div>
                )}
                {!loadingModels && !modelsError && modelNames.length > 0 && (
                  <ul className="space-y-1">
                    {modelNames.map((name) => {
                      const isActive = name === selectedModel;
                      const parts = name.split('.');
                      const label = toTitleCase(parts[parts.length - 1] || name);
                      return (
                        <li key={name}>
                          <button
                            type="button"
                            onClick={() => handleSelectModel(name)}
                            className={`flex w-full flex-col rounded px-3 py-2 text-left transition ${
                              isActive
                                ? 'bg-blue-600 text-white shadow'
                                : 'bg-white text-slate-700 hover:bg-gray-100'
                            }`}
                          >
                            <span className="text-sm font-medium">{label}</span>
                            <span className={`text-xs ${isActive ? 'text-blue-100' : 'text-slate-400'}`}>{name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
            <div className={`${colBase} w-full md:basis-[30%] md:max-w-2xl md:flex-none`}>
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-gray-700">
                    {selectedModelLabel ? `Records (${selectedModelLabel})` : 'Records'}
                  </span>
                  {selectedModel && (
                    <p className="text-xs text-gray-400">{selectedModel}</p>
                  )}
                </div>
              </div>
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-xs font-semibold">List fields</div>
                  <div className="space-x-2">
                    <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'all')}>Select all</button>
                    <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('list', 'clear')}>Clear</button>
                  </div>
                </div>
                <div className="flex max-h-24 flex-wrap gap-2 overflow-auto">
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
                    {records.map((record, index) => {
                      const recordId = toNumericId(record.id);
                      const rowKey = recordId ?? `${selectedModel || 'record'}-${index}`;
                      const isActive = recordId !== null && selectedId === recordId;
                      return (
                        <tr
                          key={rowKey}
                          className={`cursor-pointer border-t hover:bg-gray-50 ${isActive ? 'bg-blue-50' : ''}`}
                          onClick={() => {
                            if (recordId !== null) {
                              setSelectedId(recordId);
                            }
                          }}
                        >
                          {visibleListFields.map((field) => {
                            const value = record[field];
                            const displayValue = typeof value === 'object' && value !== null
                              ? JSON.stringify(value)
                              : String(value ?? '');
                            return (
                              <td key={field} className="py-1 pr-3 align-top">{displayValue}</td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
            <div className={`${colBase} w-full flex-1 md:basis-[50%]`}>
              <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-gray-700">
                    Detail{selectedModelLabel ? ` (${selectedModelLabel})` : ''}
                  </span>
                  {selectedId ? (
                    <p className="text-xs text-gray-400">Record #{selectedId}</p>
                  ) : null}
                </div>
                <div className="space-x-2">
                  <button className="px-3 py-1 text-sm rounded border hover:bg-gray-100" onClick={handleSave} disabled={!selectedRecord}>Save</button>
                </div>
              </div>
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-xs font-semibold">Detail fields</div>
                  <div className="space-x-2">
                    <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'all')}>Select all</button>
                    <button className="px-2 py-0.5 text-xs rounded border hover:bg-gray-100" onClick={() => bulkSetFields('detail', 'clear')}>Clear</button>
                  </div>
                </div>
                <div className="flex max-h-24 flex-wrap gap-2 overflow-auto">
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
              <div className="flex-1 overflow-y-auto px-4 py-4">
                {selectedRecord ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {visibleDetailFields
                      .filter((field) => Object.prototype.hasOwnProperty.call(selectedRecord, field))
                      .map((field) => {
                        const value = selectedRecord[field];
                        const displayValue = typeof value === 'object' && value !== null
                          ? JSON.stringify(value)
                          : String(value ?? '');
                        return (
                          <label key={field} className="text-sm">
                            <div className="mb-1 text-gray-600">{field}</div>
                            <input
                              className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                              value={displayValue}
                              onChange={(event) =>
                                setSelectedRecord((prev) => (prev ? { ...prev, [field]: event.target.value } : prev))
                              }
                            />
                          </label>
                        );
                      })}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">Select a record to edit.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminWorkbench;
