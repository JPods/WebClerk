import React, { useEffect, useState } from 'react';
import { api } from '../api/client';

interface State {
  endpoints: string[];
  modelNames: string[];
  selectedModel: string | null;
  fields: string[];
  loading: boolean;
  error: string | null;
}

export const Explorer: React.FC = () => {
  const [state, setState] = useState<State>({
    endpoints: [],
    modelNames: [],
    selectedModel: null,
    fields: [],
    loading: false,
    error: null,
  });

  useEffect(() => {
    (async () => {
      try {
        setState(s => ({ ...s, loading: true }));
        const [endpoints, modelNames] = await Promise.all([
          api.listEndpoints().catch(()=>[]),
          api.listModelNames().catch(()=>[])
        ]);
        setState(s => ({ ...s, endpoints, modelNames, loading: false }));
      } catch (e:any) {
        setState(s => ({ ...s, loading: false, error: e.message || 'Load failed'}));
      }
    })();
  }, []);

  async function selectModel(m: string) {
    setState(s => ({ ...s, selectedModel: m, fields: [], loading: true, error: null }));
    try {
      const fields = await api.getFields(m);
      setState(s => ({ ...s, fields, loading: false }));
    } catch(e:any) {
      setState(s => ({ ...s, loading: false, error: e.message || 'Failed to fetch fields' }));
    }
  }

  return (
    <div style={{ display: 'flex', flex:1, overflow:'hidden', fontSize:14 }}>
      <div style={{ width: 280, borderRight:'1px solid #ddd', padding:12, overflowY:'auto' }}>
        <h3 style={{ marginTop:0 }}>Models</h3>
        {state.modelNames.map(m => (
          <div key={m} style={{ cursor:'pointer', padding:'4px 6px', background: m===state.selectedModel? '#eef':'transparent' }} onClick={()=>selectModel(m)}>{m}</div>
        ))}
        <h3>Endpoints</h3>
        <ul style={{ paddingLeft:18 }}>
          {state.endpoints.map(e => <li key={e} style={{ wordBreak:'break-all' }}>{e}</li>)}
        </ul>
      </div>
      <div style={{ flex:1, padding:16, overflowY:'auto' }}>
        {state.loading && <div>Loading...</div>}
        {state.error && <div style={{ color:'red' }}>{state.error}</div>}
        {state.selectedModel && !state.loading && (
          <div>
            <h2 style={{ marginTop:0 }}>{state.selectedModel}</h2>
            <h4>Fields</h4>
            <ul>
              {state.fields.map(f => <li key={f}>{f}</li>)}
            </ul>
          </div>
        )}
        {!state.selectedModel && !state.loading && <div>Select a model to view fields.</div>}
      </div>
    </div>
  );
};
