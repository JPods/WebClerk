/**
 * QueryBuilderPanel — visual compound query builder.
 *
 * Users build multi-row filter queries: pick field, operator, value,
 * combine with AND/OR. Saved searches persist as Setting records.
 * Operators filtered by field type via filterOperators.ts.
 *
 * Emits Django ORM-compatible filter params via onExecute callback.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { OPERATORS_BY_TYPE, type FilterOperator } from '@/constants/filterOperators';
import { getRecords, saveRecord } from '@/api/wcapi';

// ── Types ───────────────────────────────────────────────────────────────────

interface AliceIntent {
  text: string;
  sent: boolean;
}

export type ValueType = 'text' | 'number' | 'date' | 'boolean' | 'json';

export interface QueryRule {
  field: string;
  lookup: string;       // Django lookup suffix
  operatorKey: string;  // internal key (for operator label display)
  value: string;
  combine: '' | 'AND' | 'OR';
  valueType?: ValueType; // user override — when set, controls operators + input widget
}

interface SavedSearch {
  id: number;
  name: string;
  rules: QueryRule[];
}

interface QueryBuilderPanelProps {
  fields: string[];
  fieldBehaviors: Record<string, any>;
  model: string;
  onExecute: (filters: Record<string, unknown>) => void;
  onClear: () => void;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const EMPTY_RULE: QueryRule = { field: '', lookup: 'exact', operatorKey: 'eq', value: '', combine: '', valueType: undefined };

const VALUE_TYPE_OPTIONS: { value: ValueType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'date', label: 'Date' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'json', label: 'JSON' },
];

// Known JSON/array fields — add here as needed
const JSON_FIELD_NAMES = new Set([
  'assigned_to', 'refs', 'metadata', 'prefs', 'comments', 'actions',
  'config', 'objective', 'tasks', 'tags', 'burndown_history',
]);

function getFieldType(field: string, behaviors: Record<string, any>): string {
  const b = behaviors[field];
  if (!b) {
    // Heuristic for untyped fields
    if (JSON_FIELD_NAMES.has(field)) return 'json';
    if (field.startsWith('dt_') || field.endsWith('_date')) return 'date';
    if (field.endsWith('_id')) return 'select';
    return 'text';
  }
  if (b.type === 'json' || b.type === 'jsonb') return 'json';
  if (b.type === 'select' || b.type === 'lookup') return 'select';
  if (b.type === 'number' || b.type === 'currency') return 'number';
  if (b.type === 'boolean') return 'boolean';
  if (b.type === 'date' || b.type === 'timestamp') return 'date';
  // Heuristic: fields starting with dt_ or ending in _date are dates
  if (field.startsWith('dt_') || field.endsWith('_date')) return 'date';
  // Fields ending in _id are lookups
  if (field.endsWith('_id')) return 'select';
  // Check if known JSON field
  if (JSON_FIELD_NAMES.has(field)) return 'json';
  return 'text';
}

function getOperatorsForType(type: string): FilterOperator[] {
  return OPERATORS_BY_TYPE[type] || OPERATORS_BY_TYPE.text;
}

function getOperatorsForField(field: string, behaviors: Record<string, any>): FilterOperator[] {
  const type = getFieldType(field, behaviors);
  return getOperatorsForType(type);
}

function rulesToParams(rules: QueryRule[], behaviors: Record<string, any>): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  const excludes: Record<string, unknown> = {};

  for (const rule of rules) {
    if (!rule.field || (!rule.value && rule.operatorKey !== 'empty' && rule.operatorKey !== 'notempty')) continue;

    const fieldType = rule.valueType || getFieldType(rule.field, behaviors);

    // Handle special operators
    if (rule.operatorKey === 'empty') {
      params[`${rule.field}__isnull`] = true;
      continue;
    }
    if (rule.operatorKey === 'notempty') {
      params[`${rule.field}__isnull`] = false;
      continue;
    }
    if (rule.operatorKey === 'not_contains') {
      excludes[`${rule.field}__icontains`] = rule.value;
      continue;
    }

    // Boolean special handling
    if (fieldType === 'boolean') {
      params[rule.field] = rule.operatorKey === 'eq' ? true : false;
      continue;
    }

    // JSON "contains text" — cast to text and search (works on PostgreSQL JSONField)
    if (rule.operatorKey === 'json_contains_text') {
      params[`${rule.field}__icontains`] = rule.value;
      continue;
    }

    // JSON "has value" — PostgreSQL __contains for JSON containment
    if (rule.operatorKey === 'json_has') {
      params[`${rule.field}__contains`] = rule.value;
      continue;
    }

    // Date fields: convert to milliseconds
    let value: unknown = rule.value;
    if (fieldType === 'date' && rule.value) {
      const d = new Date(rule.value);
      if (!isNaN(d.getTime())) value = d.getTime();
    }

    // Build param key
    const key = rule.lookup === 'exact' ? rule.field : `${rule.field}__${rule.lookup}`;
    params[key] = value;
  }

  // Negation params use exclude__ prefix (backend handles this)
  for (const [k, v] of Object.entries(excludes)) {
    params[`exclude__${k}`] = v;
  }

  return params;
}

// ── Component ───────────────────────────────────────────────────────────────

const QueryBuilderPanel: React.FC<QueryBuilderPanelProps> = ({
  fields,
  fieldBehaviors,
  model,
  onExecute,
  onClear,
}) => {
  const [rules, setRules] = useState<QueryRule[]>([{ ...EMPTY_RULE }]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [selectedSaved, setSelectedSaved] = useState<string>('');
  const [aliceIntent, setAliceIntent] = useState<AliceIntent>({ text: '', sent: false });
  const [pasteText, setPasteText] = useState('');
  const [copyFeedback, setCopyFeedback] = useState(false);

  // Load saved searches for this model
  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('setting', {
          purpose: 'saved_search',
          parent_model: model,
          limit: 50,
        }) as any;
        const records = res?.results || [];
        setSavedSearches(
          records.map((r: any) => ({
            id: r.id,
            name: r.name || r.ida || `#${r.id}`,
            rules: r.config?.rules || [],
          }))
        );
      } catch { /* no saved searches */ }
    })();
  }, [model]);

  const sortedFields = [...fields].sort();

  const updateRule = useCallback((index: number, updates: Partial<QueryRule>) => {
    setRules((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };

      // When field changes, auto-detect type and reset operator
      if (updates.field && updates.field !== prev[index].field) {
        const detectedType = getFieldType(updates.field, fieldBehaviors) as ValueType;
        next[index].valueType = detectedType;
        const ops = getOperatorsForType(detectedType);
        if (ops.length > 0) {
          next[index].lookup = ops[0].django;
          next[index].operatorKey = ops[0].key;
        }
      }

      // When valueType is explicitly changed, reset operator
      if (updates.valueType && updates.valueType !== prev[index].valueType) {
        const ops = getOperatorsForType(updates.valueType);
        if (ops.length > 0) {
          next[index].lookup = ops[0].django;
          next[index].operatorKey = ops[0].key;
        }
        next[index].value = '';
      }

      return next;
    });
  }, [fieldBehaviors]);

  const addRule = useCallback(() => {
    setRules((prev) => [...prev, { ...EMPTY_RULE, combine: 'AND' }]);
  }, []);

  const removeRule = useCallback((index: number) => {
    setRules((prev) => {
      if (prev.length <= 1) return [{ ...EMPTY_RULE }];
      const next = prev.filter((_, i) => i !== index);
      // First rule never has a combine
      if (next.length > 0) next[0] = { ...next[0], combine: '' };
      return next;
    });
  }, []);

  const handleExecute = useCallback(() => {
    const params = rulesToParams(rules, fieldBehaviors);
    onExecute(params);
  }, [rules, fieldBehaviors, onExecute]);

  const handleClear = useCallback(() => {
    setRules([{ ...EMPTY_RULE }]);
    setSelectedSaved('');
    onClear();
  }, [onClear]);

  const handleSave = useCallback(async () => {
    const name = prompt('Search name:');
    if (!name?.trim()) return;
    try {
      const params = rulesToParams(rules, fieldBehaviors);
      await saveRecord('setting', {
        name: name.trim(),
        purpose: 'saved_search',
        parent_model: model,
        config: { rules, filters: params },
      });
      // Refresh list
      const res = await getRecords('setting', { purpose: 'saved_search', parent_model: model, limit: 50 }) as any;
      setSavedSearches((res?.results || []).map((r: any) => ({
        id: r.id, name: r.name || r.ida, rules: r.config?.rules || [],
      })));
    } catch (e) {
      console.error('[QueryBuilder] Save failed:', e);
    }
  }, [rules, fieldBehaviors, model]);

  const handleLoadSaved = useCallback((name: string) => {
    const saved = savedSearches.find((s) => s.name === name);
    if (saved && saved.rules.length > 0) {
      setRules(saved.rules);
      setSelectedSaved(name);
      // Auto-execute
      const params = rulesToParams(saved.rules, fieldBehaviors);
      onExecute(params);
    }
  }, [savedSearches, fieldBehaviors, onExecute]);

  // Send intent to Alice — she learns what users are searching for and why
  const handleAliceSend = useCallback(async () => {
    if (!aliceIntent.text.trim()) return;
    try {
      const { default: apiClient } = await import('@/api/axios');
      await apiClient.post('/wcapi/manage/', {
        action: 'alice_observe',
        params: {
          event: 'search_intent',
          model,
          intent: aliceIntent.text.trim(),
          rules: rules.filter((r) => r.field),
          filters: rulesToParams(rules, fieldBehaviors),
        },
      });
      setAliceIntent((prev) => ({ ...prev, sent: true }));
    } catch {
      // Silent — Alice observation is best-effort
    }
  }, [aliceIntent.text, model, rules, fieldBehaviors]);

  const handleCopy = useCallback(() => {
    const data = rules.filter((r) => r.field).map(({ field, operatorKey, value, combine, valueType }) => ({
      field, op: operatorKey, value, ...(combine ? { combine } : {}), ...(valueType ? { type: valueType } : {}),
    }));
    const text = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    });
  }, [rules]);

  const handlePaste = useCallback(() => {
    try {
      const data = JSON.parse(pasteText);
      if (!Array.isArray(data)) return;
      const parsed: QueryRule[] = data.map((d: any, i: number) => {
        const vt = d.type as ValueType | undefined;
        const ops = getOperatorsForType(vt || 'text');
        const matched = ops.find((o) => o.key === d.op) || ops[0];
        return {
          field: d.field || '',
          operatorKey: matched?.key || 'eq',
          lookup: matched?.django || 'exact',
          value: String(d.value ?? ''),
          combine: i === 0 ? '' : (d.combine || 'AND'),
          valueType: vt,
        } as QueryRule;
      });
      if (parsed.length > 0) {
        setRules(parsed);
        setPasteText('');
      }
    } catch {
      // Invalid JSON — leave paste field for user to fix
    }
  }, [pasteText]);

  const handleDeleteSaved = useCallback(async () => {
    const saved = savedSearches.find((s) => s.name === selectedSaved);
    if (!saved) return;
    if (!confirm(`Delete saved search "${saved.name}"?`)) return;
    try {
      const { deleteRecord } = await import('@/api/wcapi');
      await deleteRecord('setting', saved.id);
      setSavedSearches((prev) => prev.filter((s) => s.id !== saved.id));
      setSelectedSaved('');
    } catch (e) {
      console.error('[QueryBuilder] Delete failed:', e);
    }
  }, [savedSearches, selectedSaved]);

  return (
    <div className="db-query-panel">
      {/* Rules */}
      {rules.map((rule, i) => {
        const activeType = rule.valueType || (rule.field ? getFieldType(rule.field, fieldBehaviors) as ValueType : 'text');
        const ops = rule.field ? getOperatorsForType(activeType) : [];
        const needsValue = rule.operatorKey !== 'empty' && rule.operatorKey !== 'notempty';

        return (
          <div key={i} className="db-query-row">
            {/* Combine (AND/OR) */}
            {i === 0 ? (
              <span className="db-query-combine-label">Where</span>
            ) : (
              <select
                className="db-query-combine"
                value={rule.combine}
                onChange={(e) => updateRule(i, { combine: e.target.value as 'AND' | 'OR' })}
              >
                <option value="AND">AND</option>
                <option value="OR">OR</option>
              </select>
            )}

            {/* Field */}
            <select
              className="db-query-field"
              value={rule.field}
              onChange={(e) => updateRule(i, { field: e.target.value })}
            >
              <option value="">Field...</option>
              {sortedFields.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>

            {/* Type override — user can change how the field is searched */}
            <select
              className="db-query-type"
              value={activeType}
              onChange={(e) => updateRule(i, { valueType: e.target.value as ValueType })}
              disabled={!rule.field}
              title="Value type — change if auto-detection is wrong"
            >
              {VALUE_TYPE_OPTIONS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            {/* Operator */}
            <select
              className="db-query-operator"
              value={rule.operatorKey}
              onChange={(e) => {
                const op = ops.find((o) => o.key === e.target.value);
                if (op) updateRule(i, { lookup: op.django, operatorKey: op.key });
              }}
              disabled={!rule.field}
            >
              {ops.map((op) => (
                <option key={op.key} value={op.key}>{op.label}</option>
              ))}
            </select>

            {/* Value — input widget matches activeType */}
            {needsValue && (
              activeType === 'boolean' ? (
                <select
                  className="db-query-value"
                  value={rule.value}
                  onChange={(e) => updateRule(i, { value: e.target.value })}
                >
                  <option value="true">True</option>
                  <option value="false">False</option>
                </select>
              ) : activeType === 'date' ? (
                <input
                  type="date"
                  className="db-query-value"
                  value={rule.value}
                  onChange={(e) => updateRule(i, { value: e.target.value })}
                />
              ) : (
                <input
                  type={activeType === 'number' ? 'number' : 'text'}
                  className="db-query-value"
                  value={rule.value}
                  placeholder={activeType === 'json' ? 'Search in JSON...' : 'Value...'}
                  onChange={(e) => updateRule(i, { value: e.target.value })}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleExecute(); }}
                />
              )
            )}
            {!needsValue && <span className="db-query-value-placeholder" />}

            {/* Remove */}
            <button className="db-query-remove" onClick={() => removeRule(i)} title="Remove rule">×</button>
          </div>
        );
      })}

      {/* Actions row */}
      <div className="db-query-actions">
        <button className="db-btn db-btn--small" onClick={addRule}>+ Add</button>
        <button className="db-btn db-btn--small db-btn--primary" onClick={handleExecute}>Execute</button>
        <button className="db-btn db-btn--small" onClick={handleClear}>Clear</button>

        <span className="db-query-spacer" />

        {/* Saved searches */}
        <select
          className="db-query-saved"
          value={selectedSaved}
          onChange={(e) => { if (e.target.value) handleLoadSaved(e.target.value); }}
        >
          <option value="">Saved...</option>
          {savedSearches.map((s) => (
            <option key={s.id} value={s.name}>{s.name}</option>
          ))}
        </select>
        <button className="db-btn db-btn--small" onClick={handleSave} title="Save current search">Save</button>
        {selectedSaved && (
          <button className="db-btn db-btn--small db-btn--danger" onClick={handleDeleteSaved} title="Delete saved search">Del</button>
        )}

        <span className="db-query-spacer" />

        {/* Copy / Paste */}
        <button className="db-btn db-btn--small" onClick={handleCopy} title="Copy query as JSON — edit externally, paste back">
          {copyFeedback ? '✓ Copied' : 'Copy'}
        </button>
        <input
          type="text"
          className="db-query-paste-input"
          placeholder="Paste query JSON..."
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && pasteText.trim()) handlePaste(); }}
        />
        <button
          className="db-btn db-btn--small"
          onClick={handlePaste}
          disabled={!pasteText.trim()}
          title="Load pasted query"
        >
          Paste
        </button>
      </div>

      {/* Alice intent — what are you trying to find? */}
      <div className="db-query-alice">
        <input
          type="text"
          className="db-query-alice-input"
          placeholder="Tell Alice what you're looking for..."
          value={aliceIntent.text}
          onChange={(e) => setAliceIntent({ text: e.target.value, sent: false })}
          onKeyDown={(e) => { if (e.key === 'Enter' && aliceIntent.text.trim()) handleAliceSend(); }}
        />
        <button
          className="db-btn db-btn--small"
          onClick={handleAliceSend}
          disabled={!aliceIntent.text.trim() || aliceIntent.sent}
          title="Send to Alice — helps her learn what searches matter"
        >
          {aliceIntent.sent ? '✓ Sent' : 'Ask Alice'}
        </button>
      </div>
    </div>
  );
};

export default QueryBuilderPanel;
