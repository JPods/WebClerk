/**
 * CalculatedFields — a model's calculated fields, in the column dialog (Bill, 2026-11-01: users
 * insert values they want calculated in rows). Each is data on the model's definition
 * (config.calculated) and the server works it out for every list that names it:
 *   name = calc (sum | count | min | max | average) of <field> over <rows of a related model>
 * Defined and removed through the definition's commands: POST /wcapi/setting/<id>/calculated/
 * (staff), offered through …/calculated_offer/. The server refuses one it cannot work out.
 */
import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '@/api/axios';
import { getRecords } from '@/api/wcapi';

interface Spec { calc: string; of?: string; over: string }
interface Offer { over: string; model: string; numbers: string[]; json: string[] }
interface State { defined: Record<string, Spec>; problems: Record<string, string>; offer?: Offer[] }

const CALCS = ['sum', 'count', 'min', 'max', 'average'];

const CalculatedFields: React.FC<{ modelName: string; onChanged: () => void }> = ({ modelName, onChanged }) => {
  const [definitionId, setDefinitionId] = useState<number | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState<{ name: string; calc: string; over: string; of: string }>(
    { name: '', calc: 'sum', over: '', of: '' });

  const command = useCallback(async (verb: string, body: object) => {
    const r = await apiClient.post(`/wcapi/setting/${definitionId}/${verb}/`, body);
    return r.data?.data?.result as State;
  }, [definitionId]);

  useEffect(() => {
    getRecords('setting', { purpose: 'wc:model', parent_model: modelName, limit: 1 })
      .then((r: any) => setDefinitionId(r?.results?.[0]?.id ?? null))
      .catch(() => setDefinitionId(null));
  }, [modelName]);

  useEffect(() => {
    if (!definitionId) return;
    command('calculated_offer', {}).then(setState).catch((e) => setError(e?.response?.data?.message || 'Could not read'));
  }, [definitionId, command]);

  const save = async (name: string, spec: Spec | null) => {
    setError('');
    try {
      const next = await command('calculated', { name, spec });
      setState((s) => ({ ...next, offer: s?.offer }));
      setDraft({ name: '', calc: 'sum', over: '', of: '' });
      onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Not saved');
    }
  };

  if (!definitionId || !state) return null;
  const over = state.offer?.find((o) => o.over === draft.over);

  return (
    <div className="fod-section" style={{ borderTop: '1px solid var(--db-border)', paddingTop: 8, marginTop: 8 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Calculated fields</div>
      {Object.entries(state.defined).map(([name, s]) => (
        <div key={name} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <code>{name}</code>
          <span className="db-text-muted">= {s.calc}{s.of ? ` of ${s.of}` : ''} over {s.over}</span>
          {state.problems[name] && <span style={{ color: 'var(--db-accent-red)' }} title={state.problems[name]}>⚠</span>}
          <button type="button" className="db-text-dim" style={{ marginLeft: 'auto' }}
            title="Remove this calculated field" onClick={() => save(name, null)}>×</button>
        </div>
      ))}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 6, flexWrap: 'wrap' }}>
        <input className="db-input" placeholder="name" style={{ width: 110 }} value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })} />
        =
        <select className="db-input" value={draft.calc} onChange={(e) => setDraft({ ...draft, calc: e.target.value })}>
          {CALCS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {draft.calc !== 'count' && <>
          of
          <input className="db-input" list="calc-of" placeholder="field (or json.path)" style={{ width: 140 }}
            value={draft.of} onChange={(e) => setDraft({ ...draft, of: e.target.value })} />
          <datalist id="calc-of">
            {(over?.numbers ?? []).map((f) => <option key={f} value={f} />)}
            {(over?.json ?? []).map((f) => <option key={f} value={`${f}.`} />)}
          </datalist>
        </>}
        over
        <select className="db-input" value={draft.over} onChange={(e) => setDraft({ ...draft, over: e.target.value, of: '' })}>
          <option value="">rows of…</option>
          {(state.offer ?? []).map((o) => <option key={o.over} value={o.over}>{o.over} ({o.model})</option>)}
        </select>
        <button type="button" className="db-btn db-btn--small"
          disabled={!draft.name || !draft.over || (draft.calc !== 'count' && !draft.of)}
          onClick={() => save(draft.name, { calc: draft.calc, over: draft.over, ...(draft.of ? { of: draft.of } : {}) })}>
          Add
        </button>
      </div>
      {error && <div style={{ color: 'var(--db-accent-red)', marginTop: 4 }}>{error}</div>}
    </div>
  );
};

export default CalculatedFields;
