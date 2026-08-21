/**
 * AdminTools — run admin utility tools from Report records.
 *
 * Each tool is a Report record with category='utility', model_name='setting'.
 * The Report.config holds the management command name, default args, and
 * parameter definitions. Tools run via /wcapi/manage/ action=run_admin_tool.
 *
 * Superuser only.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { getRecords } from '@/api/wcapi';
import { useAppSelector } from '@/store/hooks';
import './AdminTools.css';

interface ToolParam {
  name: string;
  type: 'text' | 'boolean';
  label: string;
  required?: boolean;
  default?: any;
}

interface ToolConfig {
  command: string;
  default_args: string[];
  parameters: ToolParam[];
}

interface ToolReport {
  id: number;
  ida: string;
  name: string;
  description: string;
  explanation: string;
  config: ToolConfig;
}

interface ToolResult {
  command: string;
  args: string[];
  result: any;
}

export default function AdminTools() {
  const { user } = useAppSelector((s) => s.auth);
  const [tools, setTools] = useState<ToolReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ToolResult | null>(null);
  const [error, setError] = useState('');

  // Load tool reports
  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('report', {
          model_name: 'setting',
          category: 'utility',
          is_active: true,
          order_by: 'sort_order',
        }) as any;
        setTools((res?.results || []).map((r: any) => ({
          id: r.id, ida: r.ida, name: r.name,
          description: r.description, explanation: r.explanation,
          config: r.config || {},
        })));
      } catch { setError('Failed to load tools'); }
      finally { setLoading(false); }
    })();
  }, []);

  const selectTool = useCallback((ida: string) => {
    setActiveTool(ida);
    setResult(null);
    setError('');
    // Initialize params with defaults
    const tool = tools.find(t => t.ida === ida);
    if (tool?.config?.parameters) {
      const defaults: Record<string, any> = {};
      tool.config.parameters.forEach(p => {
        defaults[p.name] = p.default ?? (p.type === 'boolean' ? false : '');
      });
      setParamValues(defaults);
    }
  }, [tools]);

  const runTool = useCallback(async () => {
    const tool = tools.find(t => t.ida === activeTool);
    if (!tool) return;

    setRunning(true);
    setError('');
    setResult(null);

    try {
      // Build args from default_args + parameter values
      const args = [...(tool.config.default_args || [])];
      (tool.config.parameters || []).forEach(param => {
        const val = paramValues[param.name];
        if (param.type === 'boolean' && val) {
          args.push(`--${param.name}`);
        } else if (param.type === 'text' && val) {
          args.push(`--${param.name}`, String(val));
        }
      });

      const { default: apiClient } = await import('@/api/axios');
      const resp = await apiClient.post('/wcapi/manage/', {
        action: 'run_admin_tool',
        params: { command: tool.config.command, args },
      });

      setResult(resp.data?.data || null);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Run failed');
    } finally {
      setRunning(false);
    }
  }, [activeTool, tools, paramValues]);

  if (!user?.is_superuser) {
    return <div className="at-denied">Superuser access required</div>;
  }

  const selectedTool = tools.find(t => t.ida === activeTool);

  return (
    <div className="at-root">
      <div className="at-header">
        <h2 className="at-title">Admin Tools</h2>
        <span className="at-subtitle">{tools.length} utilities</span>
      </div>

      {loading ? <div className="at-loading">Loading tools…</div> : (
        <div className="at-layout">
          {/* Tool cards */}
          <div className="at-cards">
            {tools.map(tool => (
              <div key={tool.ida}
                className={`at-card ${activeTool === tool.ida ? 'at-card--active' : ''}`}
                onClick={() => selectTool(tool.ida)}>
                <div className="at-card-name">{tool.name}</div>
                <div className="at-card-desc">{tool.description}</div>
                <div className="at-card-cmd">{tool.config?.command}</div>
              </div>
            ))}
          </div>

          {/* Tool runner */}
          {selectedTool && (
            <div className="at-runner">
              <div className="at-runner-header">
                <h3>{selectedTool.name}</h3>
                <code className="at-runner-cmd">{selectedTool.config.command}</code>
              </div>

              {selectedTool.explanation && (
                <div className="at-runner-explain">{selectedTool.explanation}</div>
              )}

              {/* Parameters */}
              {selectedTool.config.parameters?.length > 0 && (
                <div className="at-params">
                  {selectedTool.config.parameters.map(param => (
                    <div key={param.name} className="at-param-row">
                      <label className="at-param-label">{param.label}</label>
                      {param.type === 'boolean' ? (
                        <input type="checkbox"
                          checked={!!paramValues[param.name]}
                          onChange={e => setParamValues(p => ({ ...p, [param.name]: e.target.checked }))} />
                      ) : (
                        <input className="at-param-input" type="text"
                          value={paramValues[param.name] || ''}
                          onChange={e => setParamValues(p => ({ ...p, [param.name]: e.target.value }))}
                          placeholder={param.required ? 'required' : 'optional'} />
                      )}
                    </div>
                  ))}
                </div>
              )}

              <button className="at-run-btn" onClick={runTool} disabled={running}>
                {running ? 'Running…' : 'Run'}
              </button>

              {error && <div className="at-error">{error}</div>}

              {/* Results */}
              {result && (
                <div className="at-result">
                  <div className="at-result-header">
                    <span>Result: <code>{result.command} {result.args.join(' ')}</code></span>
                  </div>
                  <pre className="at-result-json">
                    {typeof result.result === 'string'
                      ? result.result
                      : JSON.stringify(result.result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
