/**
 * SelectListEditor — Edit select lists across models from one place.
 *
 * Not a source of truth — wc:model.config.select_lists IS the source.
 * This is an authoring tool: edit a template, pick which models to push to.
 *
 * Reads all wc:model Settings, builds a matrix of shared select lists,
 * lets you edit and push changes to individual model records.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecords, saveRecord } from '@/api/wcapi';
import { useAppSelector } from '@/store/hooks';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';

interface SelectOption {
  value: string | number;
  label: string;
}

interface ModelSelectLists {
  settingId: number;
  model: string;
  lists: Record<string, SelectOption[]>;
}

interface FieldGroup {
  field: string;
  options: SelectOption[];
  models: string[];
  variants: number; // how many distinct option sets exist for this field
}

export default function SelectListEditor() {
  const { user } = useAppSelector((s) => s.auth);
  const dispatch = useDispatch();
  const [modelData, setModelData] = useState<ModelSelectLists[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [editOptions, setEditOptions] = useState<SelectOption[]>([]);
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [pushing, setPushing] = useState(false);
  const [newOptionValue, setNewOptionValue] = useState('');
  const [newOptionLabel, setNewOptionLabel] = useState('');

  // Load all wc:model settings
  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('setting', { purpose: 'wc:model', limit: 200 }) as any;
        const records = res?.results || [];
        const data: ModelSelectLists[] = [];
        for (const r of records) {
          const sl = r.config?.select_lists;
          if (sl && typeof sl === 'object' && Object.keys(sl).length > 0) {
            const normalized: Record<string, SelectOption[]> = {};
            for (const [field, opts] of Object.entries(sl)) {
              if (Array.isArray(opts)) {
                normalized[field] = (opts as any[]).map((o: any) =>
                  typeof o === 'object' && o !== null
                    ? { value: o.value ?? o.id ?? '', label: o.label ?? String(o.value ?? '') }
                    : { value: o, label: String(o) }
                );
              }
            }
            if (Object.keys(normalized).length > 0) {
              data.push({ settingId: r.id, model: r.parent_model, lists: normalized });
            }
          }
        }
        setModelData(data);
      } catch (e) {
        console.error('[SelectListEditor] load failed:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Build field groups — which fields exist, with how many models and variants
  const fieldGroups = useMemo<FieldGroup[]>(() => {
    const fieldMap: Record<string, { optionSets: Map<string, SelectOption[]>; models: string[] }> = {};
    for (const md of modelData) {
      for (const [field, opts] of Object.entries(md.lists)) {
        if (!fieldMap[field]) fieldMap[field] = { optionSets: new Map(), models: [] };
        fieldMap[field].models.push(md.model);
        const key = JSON.stringify(opts);
        if (!fieldMap[field].optionSets.has(key)) {
          fieldMap[field].optionSets.set(key, opts);
        }
      }
    }
    return Object.entries(fieldMap)
      .map(([field, data]) => {
        const firstSet = data.optionSets.values().next().value;
        return {
          field,
          options: firstSet || [],
          models: data.models.sort(),
          variants: data.optionSets.size,
        };
      })
      .sort((a, b) => b.models.length - a.models.length);
  }, [modelData]);

  // When selecting a field, load its options and pre-select all models that have it
  const handleSelectField = useCallback((field: string) => {
    setSelectedField(field);
    const group = fieldGroups.find(g => g.field === field);
    if (group) {
      setEditOptions([...group.options]);
      setSelectedModels(new Set(group.models));
    }
  }, [fieldGroups]);

  // Option editing
  const removeOption = useCallback((idx: number) => {
    setEditOptions(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const moveOption = useCallback((idx: number, dir: -1 | 1) => {
    setEditOptions(prev => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  }, []);

  const addOption = useCallback(() => {
    const v = newOptionValue.trim();
    if (!v) return;
    const l = newOptionLabel.trim() || v;
    const numVal = Number(v);
    const value = Number.isFinite(numVal) && String(numVal) === v ? numVal : v;
    setEditOptions(prev => [...prev, { value, label: l }]);
    setNewOptionValue('');
    setNewOptionLabel('');
  }, [newOptionValue, newOptionLabel]);

  const updateOptionLabel = useCallback((idx: number, label: string) => {
    setEditOptions(prev => prev.map((o, i) => i === idx ? { ...o, label } : o));
  }, []);

  // Toggle model selection
  const toggleModel = useCallback((model: string) => {
    setSelectedModels(prev => {
      const next = new Set(prev);
      if (next.has(model)) next.delete(model);
      else next.add(model);
      return next;
    });
  }, []);

  const selectAllModels = useCallback(() => {
    const group = fieldGroups.find(g => g.field === selectedField);
    if (group) setSelectedModels(new Set(group.models));
  }, [fieldGroups, selectedField]);

  const selectNoneModels = useCallback(() => {
    setSelectedModels(new Set());
  }, []);

  // Push edited options to selected models
  const handlePush = useCallback(async () => {
    if (!selectedField || selectedModels.size === 0) return;
    setPushing(true);
    let ok = 0;
    let fail = 0;
    for (const model of selectedModels) {
      const md = modelData.find(m => m.model === model);
      if (!md) continue;
      try {
        await saveRecord('setting', {
          id: md.settingId,
          [`config.select_lists.${selectedField}`]: { mode: 'update', value: editOptions },
        });
        ok++;
      } catch (e) {
        console.error(`[SelectListEditor] push to ${model} failed:`, e);
        fail++;
      }
    }
    dispatch(showToast({
      message: `Pushed "${selectedField}" to ${ok} model${ok !== 1 ? 's' : ''}${fail ? ` (${fail} failed)` : ''}`,
      type: fail ? 'warning' : 'success',
    }));
    setPushing(false);
    // Reload
    setLoading(true);
    const res = await getRecords('setting', { purpose: 'wc:model', limit: 200 }) as any;
    const records = res?.results || [];
    const data: ModelSelectLists[] = [];
    for (const r of records) {
      const sl = r.config?.select_lists;
      if (sl && typeof sl === 'object' && Object.keys(sl).length > 0) {
        const normalized: Record<string, SelectOption[]> = {};
        for (const [field, opts] of Object.entries(sl)) {
          if (Array.isArray(opts)) {
            normalized[field] = (opts as any[]).map((o: any) =>
              typeof o === 'object' && o !== null
                ? { value: o.value ?? o.id ?? '', label: o.label ?? String(o.value ?? '') }
                : { value: o, label: String(o) }
            );
          }
        }
        if (Object.keys(normalized).length > 0) {
          data.push({ settingId: r.id, model: r.parent_model, lists: normalized });
        }
      }
    }
    setModelData(data);
    setLoading(false);
  }, [selectedField, selectedModels, editOptions, modelData, dispatch]);

  // Models that have the selected field
  const modelsForField = useMemo(() => {
    if (!selectedField) return [];
    return modelData
      .filter(md => selectedField in md.lists)
      .map(md => md.model)
      .sort();
  }, [selectedField, modelData]);

  // All models (for adding this list to models that don't have it yet)
  const allModels = useMemo(() => {
    return [...new Set(modelData.map(md => md.model))].sort();
  }, [modelData]);

  if (!user?.is_superuser) {
    return <div className="p-8" style={{ color: 'var(--db-text-muted)' }}>Superuser access required.</div>;
  }

  return (
    <div className="flex h-full" style={{ color: 'var(--db-text)' }}>
      {/* Left: field list */}
      <div className="w-64 shrink-0 overflow-y-auto border-r p-4" style={{ borderColor: 'var(--db-border)', background: 'var(--db-surface)' }}>
        <h2 className="mb-3 text-lg font-semibold">select lists</h2>
        {loading ? (
          <div className="db-font-sm" style={{ color: 'var(--db-text-muted)' }}>Loading...</div>
        ) : fieldGroups.length === 0 ? (
          <div className="db-font-sm" style={{ color: 'var(--db-text-muted)' }}>No select lists found in wc:model records.</div>
        ) : (
          <div className="space-y-1">
            {fieldGroups.map(g => (
              <button
                key={g.field}
                onClick={() => handleSelectField(g.field)}
                className={`w-full rounded-lg px-3 py-2 text-left db-font-sm transition ${
                  selectedField === g.field ? 'font-semibold' : ''
                }`}
                style={{
                  background: selectedField === g.field ? 'var(--db-surface-alt)' : 'transparent',
                  color: selectedField === g.field ? 'var(--db-text)' : 'var(--db-text-muted)',
                }}
              >
                <div className="font-mono">{g.field}</div>
                <div className="db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
                  {g.models.length} model{g.models.length !== 1 ? 's' : ''}
                  {g.variants > 1 ? ` · ${g.variants} variants` : ''}
                  {' · '}{g.options.length} options
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: editor */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selectedField ? (
          <div className="flex h-full items-center justify-center db-font-sm" style={{ color: 'var(--db-text-dim)' }}>
            Select a field to edit its options
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold font-mono">{selectedField}</h2>
              <p className="mt-1 db-font-sm" style={{ color: 'var(--db-text-muted)' }}>
                Edit options below, then push to selected models.
              </p>
            </div>

            {/* Options editor */}
            <div className="rounded-xl p-4" style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)' }}>
              <h3 className="mb-3 db-font-sm font-semibold" style={{ color: 'var(--db-text-muted)' }}>OPTIONS ({editOptions.length})</h3>
              <div className="space-y-1">
                {editOptions.map((opt, idx) => (
                  <div key={idx} className="flex items-center gap-2 rounded-lg px-2 py-1" style={{ background: 'var(--db-surface-alt)' }}>
                    <span className="w-24 shrink-0 font-mono db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
                      {String(opt.value)}
                    </span>
                    <input
                      className="flex-1 rounded px-2 py-1 db-font-sm db-input"
                      value={opt.label}
                      onChange={e => updateOptionLabel(idx, e.target.value)}
                    />
                    <button
                      onClick={() => moveOption(idx, -1)}
                      disabled={idx === 0}
                      className="px-1 db-font-xs disabled:opacity-30"
                      style={{ color: 'var(--db-text-muted)' }}
                    >▲</button>
                    <button
                      onClick={() => moveOption(idx, 1)}
                      disabled={idx === editOptions.length - 1}
                      className="px-1 db-font-xs disabled:opacity-30"
                      style={{ color: 'var(--db-text-muted)' }}
                    >▼</button>
                    <button
                      onClick={() => removeOption(idx)}
                      className="px-1 db-font-xs text-rose-500 hover:text-rose-700"
                    >×</button>
                  </div>
                ))}
              </div>

              {/* Add new option */}
              <div className="mt-3 flex items-center gap-2">
                <input
                  className="w-24 shrink-0 rounded px-2 py-1 db-font-sm font-mono db-input"
                  placeholder="value"
                  value={newOptionValue}
                  onChange={e => setNewOptionValue(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addOption()}
                />
                <input
                  className="flex-1 rounded px-2 py-1 db-font-sm db-input"
                  placeholder="label"
                  value={newOptionLabel}
                  onChange={e => setNewOptionLabel(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addOption()}
                />
                <button
                  onClick={addOption}
                  className="rounded-lg px-3 py-1 db-font-sm font-semibold text-indigo-600 hover:text-indigo-500"
                >+ add</button>
              </div>
            </div>

            {/* Model selection */}
            <div className="rounded-xl p-4" style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)' }}>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="db-font-sm font-semibold" style={{ color: 'var(--db-text-muted)' }}>
                  PUSH TO MODELS ({selectedModels.size} selected)
                </h3>
                <div className="flex gap-2">
                  <button onClick={selectAllModels} className="db-font-xs text-indigo-600 hover:text-indigo-500">all</button>
                  <button onClick={selectNoneModels} className="db-font-xs text-indigo-600 hover:text-indigo-500">none</button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {modelsForField.map(model => (
                  <button
                    key={model}
                    onClick={() => toggleModel(model)}
                    className="rounded-lg px-3 py-1.5 db-font-xs font-mono transition"
                    style={{
                      border: '1px solid var(--db-border)',
                      background: selectedModels.has(model) ? 'var(--db-surface-alt)' : 'transparent',
                      color: selectedModels.has(model) ? 'var(--db-text)' : 'var(--db-text-dim)',
                      fontWeight: selectedModels.has(model) ? 600 : 400,
                    }}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>

            {/* Push button */}
            <div className="flex items-center gap-4">
              <button
                onClick={handlePush}
                disabled={pushing || selectedModels.size === 0}
                className="rounded-lg bg-indigo-600 px-6 py-2 db-font-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
              >
                {pushing ? 'Pushing...' : `Push to ${selectedModels.size} model${selectedModels.size !== 1 ? 's' : ''}`}
              </button>
              <span className="db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
                Updates wc:model.config.select_lists.{selectedField} on each selected model
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
