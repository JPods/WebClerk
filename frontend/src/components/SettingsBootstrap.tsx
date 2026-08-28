/**
 * SettingsBootstrap — startup health check for Setting records.
 *
 * Runs on mount. If Settings are missing or corrupt, blocks the entire app
 * with a dialog: Fix from Git, Fix from WC_HQ, or Quit.
 *
 * No dismiss, no skip, no "remind me later." Fix it or don't run.
 * Settings are the operating system — running without them is undefined behavior.
 */
import { useEffect, useState, useCallback, useRef } from 'react';

interface HealthReport {
  healthy: boolean;
  total: number;
  summary: string;
  missing: { type: string; description: string }[];
  corrupt: { id: number; ida: string; purpose: string; issues: string[] }[];
}

interface BootstrapResult {
  success: boolean;
  created: number;
  updated: number;
  errors: string[];
  health?: HealthReport;
}

interface Props {
  children: React.ReactNode;
}

export function SettingsBootstrap({ children }: Props) {
  const [checking, setChecking] = useState(true);
  const [report, setReport] = useState<HealthReport | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<BootstrapResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const runHealthCheck = useCallback(async () => {
    setChecking(true);
    setError(null);
    try {
      const res = await fetch('/wcapi/_settings_health/');
      if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
      const json = await res.json();
      const data: HealthReport = json?.data ?? json;
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Health check failed');
      setReport({ healthy: false, total: 0, summary: 'Cannot reach server', missing: [], corrupt: [] });
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => { runHealthCheck(); }, [runHealthCheck]);

  // Fix from Git — user selects settings-bundle.json file
  const handleGitImport = useCallback(async (file: File) => {
    setImporting(true);
    setImportResult(null);
    setError(null);
    try {
      const text = await file.text();
      const bundle = JSON.parse(text);
      const res = await fetch('/wcapi/_settings_bootstrap/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bundle),
      });
      const data: BootstrapResult = await res.json();
      setImportResult(data);
      if (data.health) setReport(data.health);
    } catch (e: any) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  }, []);

  // Fix from WC_HQ — prompt for Athena token, fetch from webclerk.com
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [athenaToken, setAthenaToken] = useState('');

  const handleFetchHq = useCallback(async () => {
    if (!athenaToken.trim()) return;
    setImporting(true);
    setImportResult(null);
    setError(null);
    try {
      const res = await fetch('/wcapi/_settings_fetch_hq/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ athena_token: athenaToken.trim() }),
      });
      const data: BootstrapResult = await res.json();
      setImportResult(data);
      if (data.health) setReport(data.health);
    } catch (e: any) {
      setError(e.message || 'WC_HQ fetch failed');
    } finally {
      setImporting(false);
      setShowTokenInput(false);
      setAthenaToken('');
    }
  }, [athenaToken]);

  // Quit
  const handleQuit = useCallback(() => {
    document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:#64748b;font-size:1.25rem;">WebClerk requires valid Settings to run. Restart after fixing.</div>';
  }, []);

  // Loading state
  if (checking) {
    return (
      <div style={overlayStyle}>
        <div style={dialogStyle}>
          <h2 style={titleStyle}>Checking Settings...</h2>
          <p style={textStyle}>Validating system configuration.</p>
        </div>
      </div>
    );
  }

  // Healthy — render the app
  if (report?.healthy) {
    return <>{children}</>;
  }

  // Unhealthy — block with dialog
  return (
    <div style={overlayStyle}>
      <div style={dialogStyle}>
        <h2 style={titleStyle}>Settings Required</h2>
        <p style={textStyle}>{report?.summary || 'Settings health check failed.'}</p>

        {/* Missing list */}
        {report?.missing && report.missing.length > 0 && (
          <div style={sectionStyle}>
            <h3 style={subTitleStyle}>Missing ({report.missing.length})</h3>
            <ul style={listStyle}>
              {report.missing.map((m, i) => (
                <li key={i} style={itemStyle}>{m.type} — {m.description}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Corrupt list */}
        {report?.corrupt && report.corrupt.length > 0 && (
          <div style={sectionStyle}>
            <h3 style={subTitleStyle}>Corrupt ({report.corrupt.length})</h3>
            <ul style={listStyle}>
              {report.corrupt.slice(0, 10).map((c, i) => (
                <li key={i} style={itemStyle}>
                  {c.ida || `#${c.id}`} ({c.purpose}) — {c.issues.join(', ')}
                </li>
              ))}
              {report.corrupt.length > 10 && (
                <li style={itemStyle}>...and {report.corrupt.length - 10} more</li>
              )}
            </ul>
          </div>
        )}

        {/* Import result */}
        {importResult && (
          <div style={{ ...sectionStyle, borderColor: importResult.success ? '#22c55e' : '#ef4444' }}>
            <p style={textStyle}>
              {importResult.success
                ? `Imported: ${importResult.created} created, ${importResult.updated} updated.`
                : `Import had errors: ${importResult.errors.join('; ')}`}
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <p style={{ ...textStyle, color: '#ef4444' }}>{error}</p>
        )}

        {/* Token input for WC_HQ */}
        {showTokenInput && (
          <div style={sectionStyle}>
            <label style={textStyle}>Athena Token:</label>
            <input
              type="password"
              value={athenaToken}
              onChange={(e) => setAthenaToken(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleFetchHq(); }}
              style={inputStyle}
              autoFocus
              placeholder="Paste your Athena token"
            />
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button onClick={handleFetchHq} disabled={!athenaToken.trim() || importing} style={btnPrimary}>
                {importing ? 'Fetching...' : 'Fetch'}
              </button>
              <button onClick={() => setShowTokenInput(false)} style={btnSecondary}>Cancel</button>
            </div>
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleGitImport(file);
          }}
        />

        {/* Action buttons */}
        {!showTokenInput && (
          <div style={buttonRowStyle}>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              style={btnPrimary}
            >
              {importing ? 'Importing...' : 'Fix from Git (upload bundle)'}
            </button>
            <button
              onClick={() => setShowTokenInput(true)}
              disabled={importing}
              style={btnPrimary}
            >
              Fix from WC_HQ
            </button>
            <button onClick={handleQuit} style={btnDanger}>
              Quit
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Inline styles — this dialog must render even if CSS fails to load
const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 99999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  backgroundColor: 'rgba(15, 23, 42, 0.95)',
  fontFamily: 'system-ui, -apple-system, sans-serif',
};

const dialogStyle: React.CSSProperties = {
  backgroundColor: '#1e293b', borderRadius: '12px', padding: '32px',
  maxWidth: '600px', width: '90%', maxHeight: '80vh', overflowY: 'auto',
  border: '1px solid #334155',
};

const titleStyle: React.CSSProperties = {
  color: 'var(--db-text)', fontSize: '1.5rem', fontWeight: 700, margin: '0 0 8px',
};

const subTitleStyle: React.CSSProperties = {
  color: 'var(--db-text-dim)', fontSize: '0.875rem', fontWeight: 600, margin: '0 0 4px',
};

const textStyle: React.CSSProperties = {
  color: 'var(--db-text-dim)', fontSize: '0.875rem', lineHeight: 1.5, margin: '0 0 16px',
};

const sectionStyle: React.CSSProperties = {
  border: '1px solid #334155', borderRadius: '8px', padding: '12px',
  marginBottom: '16px',
};

const listStyle: React.CSSProperties = {
  margin: 0, padding: '0 0 0 16px', color: 'var(--db-text-muted)', fontSize: '0.8125rem',
};

const itemStyle: React.CSSProperties = {
  marginBottom: '4px',
};

const buttonRowStyle: React.CSSProperties = {
  display: 'flex', gap: '8px', flexWrap: 'wrap',
};

const btnPrimary: React.CSSProperties = {
  backgroundColor: '#3b82f6', color: '#fff', border: 'none',
  borderRadius: '6px', padding: '10px 20px', fontSize: '0.875rem',
  fontWeight: 600, cursor: 'pointer',
};

const btnSecondary: React.CSSProperties = {
  backgroundColor: 'var(--db-surface-alt)', color: 'var(--db-text-muted)', border: '1px solid var(--db-border)',
  borderRadius: '6px', padding: '10px 20px', fontSize: '0.875rem',
  cursor: 'pointer',
};

const btnDanger: React.CSSProperties = {
  backgroundColor: '#dc2626', color: '#fff', border: 'none',
  borderRadius: '6px', padding: '10px 20px', fontSize: '0.875rem',
  fontWeight: 600, cursor: 'pointer',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', borderRadius: '6px',
  border: '1px solid var(--db-border)', backgroundColor: 'var(--db-bg)',
  color: 'var(--db-text)', fontSize: '0.875rem', marginTop: '4px',
  boxSizing: 'border-box',
};
