/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * DevTools Component
 * 
 * Development-only panel for switching data sets and managing dev environment.
 * Only renders in development mode (VITE_ENV === 'DEV').
 * 
 * Shows a color-coded badge indicating current database mode:
 * - 🟢 Green = Remote (Team)
 * - 🔵 Blue = Local (Debug)
 */

import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/axios';

interface DevConfig {
  db_mode: string;
  data_set_id: string;
  data_set_name: string;
  available_modes: Record<string, { label: string; description: string }>;
  restart_required: boolean;
}

interface DevToolsProps {
  /** Position of the panel toggle */
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

const positionStyles: Record<string, React.CSSProperties> = {
  'top-left': { top: '60px', left: '8px' },
  'top-right': { top: '60px', right: '8px' },
  'bottom-left': { bottom: '60px', left: '8px' },
  'bottom-right': { bottom: '60px', right: '8px' },
};

// Color schemes for database modes
const modeColors: Record<string, { bg: string; border: string; text: string; label: string }> = {
  remote: { bg: '#166534', border: '#22c55e', text: '#f0fdf4', label: '🌐 REMOTE' },
  local: { bg: '#1e40af', border: '#3b82f6', text: '#eff6ff', label: '💻 LOCAL' },
};

export function DevTools({ position = 'bottom-left' }: DevToolsProps): React.ReactElement | null {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<DevConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [syncProgress, setSyncProgress] = useState(0);
  const [syncMessage, setSyncMessage] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncDirection, setSyncDirection] = useState<'remote-to-local' | 'local-to-remote' | null>(null);
  const [backendStatus, setBackendStatus] = useState<'live' | 'restarting' | 'offline'>('live');

  const checkBackendHealth = useCallback(async (): Promise<boolean> => {
    try {
      await apiClient.get('/wcapi/system-info/');
      return true;
    } catch {
      return false;
    }
  }, []);

  // Removed: waitForServerAndReload was causing page reload loops.
  // After server restart, the user can refresh manually or the 10s poll
  // will pick up the new config automatically.

  // Only show in dev mode
  const isDev = import.meta.env.VITE_ENV === 'DEV' || import.meta.env.DEV;
  
  // Fetch config on mount to show the badge
  const fetchConfig = useCallback(async () => {
    setIsLoading(true);
    try {
      // Try dedicated dev_config endpoint first
      const response = await apiClient.get('/wcapi/dev/config/');
      const json = response.data;
      // Handle nested response: { data: { data: { ... } } } or { data: { ... } }
      const configData = json.data?.data || json.data || json;
      setConfig(configData);
      // If endpoint doesn't exist (404), axios throws and we silently catch below
    } catch {
      // Network error or 404 - silently fail, dev config is optional
    } finally {
      setIsLoading(false);
    }
  }, []);

  const waitForServerAndRefresh = useCallback((initialDelayMs = 300) => {
    let attempts = 0;
    const maxAttempts = 45;

    const checkServer = async () => {
      const isLive = await checkBackendHealth();
      if (isLive) {
        setBackendStatus('live');
        await fetchConfig();
        return;
      }

      attempts += 1;
      if (attempts < maxAttempts) {
        setBackendStatus('restarting');
        setTimeout(checkServer, 1000);
      } else {
        setBackendStatus('offline');
        setMessage({ type: 'error', text: 'Restart timeout. Please refresh manually.' });
      }
    };

    setBackendStatus('restarting');
    setTimeout(checkServer, initialDelayMs);
  }, [checkBackendHealth, fetchConfig]);

  // Fetch config on mount (for badge display)
  useEffect(() => {
    if (isDev) {
      fetchConfig();
    }
  }, [isDev, fetchConfig]);

  // Poll config periodically to keep badge in sync (e.g. after runserver.sh restart)
  useEffect(() => {
    if (!isDev) return;
    const timer = setInterval(fetchConfig, 10000);
    return () => clearInterval(timer);
  }, [isDev, fetchConfig]);

  // Also refresh when panel opens
  useEffect(() => {
    if (isOpen) {
      fetchConfig();
    }
  }, [isOpen, fetchConfig]);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    let wasOffline = false;
    const poll = async () => {
      const isLive = await checkBackendHealth();
      if (cancelled) return;
      // Re-fetch config when server comes back online (mode may have changed)
      if (isLive && wasOffline) {
        fetchConfig();
      }
      wasOffline = !isLive;
      setBackendStatus((prev) => {
        if (prev === 'restarting' && !isLive) {
          return 'restarting';
        }
        return isLive ? 'live' : 'offline';
      });
    };

    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [isOpen, checkBackendHealth]);

  useEffect(() => {
    if (!isSyncing) return;
    const poll = setInterval(async () => {
      try {
        const response = await apiClient.get('/wcapi/dev/sync-status/');
        const json = response.data;
        const data = json.data?.data || json.data || {};
        const progress = Number(data.progress ?? 0);
        setSyncProgress(Number.isFinite(progress) ? progress : 0);
        setSyncMessage(data.message || 'Syncing remote data to local...');

        if (data.state === 'completed' || data.state === 'failed') {
          setIsSyncing(false);
        }
      } catch {
        // ignore polling errors while backend restarts
      }
    }, 700);

    return () => clearInterval(poll);
  }, [isSyncing]);

  const handleSwitchMode = async (newMode: string) => {
    setIsSwitching(true);
    setMessage(null);
    
    try {
      const response = await apiClient.post('/wcapi/dev/switch/', { mode: newMode });
      const json = response.data;
      // Handle nested response structure
      const data = json.data?.data || json.data || json;

      setMessage({ type: 'success', text: json.message || data.message || `Switched to ${newMode}` });
      if (data?.changed && data?.same_console_required) {
        waitForServerAndRefresh(300);
      } else if (data?.changed) {
        await fetchConfig();
      }
    } catch (err: any) {
      const errData = err?.response?.data?.data?.data || err?.response?.data?.data || err?.response?.data;
      setMessage({ type: 'error', text: errData?.message || 'Failed to switch mode' });
    } finally {
      setIsSwitching(false);
    }
  };

  const handleSync = async (direction: 'download' | 'upload') => {
    const label = direction === 'download' ? 'remote → local' : 'local → remote';
    if (direction === 'upload' && !confirm(`Upload local data to remote? This will overwrite the shared team database. Continue?`)) {
      return;
    }
    setMessage(null);
    setSyncProgress(0);
    setSyncDirection(direction === 'download' ? 'remote-to-local' : 'local-to-remote');
    setSyncMessage(`Starting ${label} sync...`);
    setIsSyncing(true);

    try {
      const response = await apiClient.post('/wcapi/dev/sync/', { direction });
      const json = response.data;
      setMessage({ type: 'success', text: json.message || `Sync started (${label})` });
    } catch (err: any) {
      const errData = err?.response?.data?.data?.data || err?.response?.data?.data || err?.response?.data;
      setMessage({ type: 'error', text: errData?.message || 'Failed to start sync' });
      setIsSyncing(false);
      setSyncDirection(null);
    }
  };

  const handleRestart = async () => {
    if (!confirm('This will restart both frontend and backend servers. Continue?')) {
      return;
    }
    
    setMessage({ type: 'success', text: 'Restarting servers...' });
    
    try {
      const response = await apiClient.post('/wcapi/dev/restart/');
      const json = response.data;
      const data = json.data?.data || json.data || json;
      if (data?.same_console_required) {
        setMessage({
          type: 'success',
          text: data?.instructions?.note || json.message || 'Restart signal sent.',
        });
        waitForServerAndRefresh(300);
      } else {
        setMessage({ type: 'success', text: 'Restart requested.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to request restart' });
    }
  };

  if (!isDev) return null;

  const posStyle = positionStyles[position];
  const currentMode = config?.db_mode || 'remote';
  const colors = modeColors[currentMode] || modeColors.remote;
  const isPendingSwitch = isSwitching || isSyncing || backendStatus === 'restarting';

  const badgeStyle: React.CSSProperties = {
    position: 'fixed',
    ...posStyle,
    zIndex: 10000,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    borderRadius: '8px',
    backgroundColor: colors.bg,
    color: colors.text,
    border: `2px solid ${colors.border}`,
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
    transition: 'all 0.2s',
  };

  const panelStyle: React.CSSProperties = {
    position: 'fixed',
    ...posStyle,
    zIndex: 10001,
    width: '320px',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    borderRadius: '12px',
    border: '1px solid #334155',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    fontSize: '13px',
    overflow: 'hidden',
  };

  const headerStyle: React.CSSProperties = {
    padding: '12px 16px',
    backgroundColor: '#1e293b',
    borderBottom: '1px solid #334155',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  const contentStyle: React.CSSProperties = {
    padding: '16px',
  };

  const modeButtonStyle = (isActive: boolean): React.CSSProperties => ({
    width: '100%',
    padding: '12px',
    marginBottom: '8px',
    borderRadius: '8px',
    border: isActive ? '2px solid #22c55e' : '1px solid #334155',
    backgroundColor: isActive ? '#166534' : '#1e293b',
    color: '#f8fafc',
    cursor: isPendingSwitch ? 'not-allowed' : 'pointer',
    textAlign: 'left',
    opacity: isPendingSwitch ? 0.6 : 1,
    transition: 'all 0.2s',
  });

  const restartButtonStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px',
    marginTop: '12px',
    borderRadius: '8px',
    border: '1px solid #dc2626',
    backgroundColor: '#7f1d1d',
    color: '#f8fafc',
    cursor: 'pointer',
    fontWeight: 600,
  };

  const backendStatusStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    fontWeight: 600,
    padding: '4px 8px',
    borderRadius: '999px',
    border: '1px solid',
    backgroundColor:
      backendStatus === 'live' ? '#14532d' : backendStatus === 'restarting' ? '#78350f' : '#7f1d1d',
    borderColor:
      backendStatus === 'live' ? '#22c55e' : backendStatus === 'restarting' ? '#f59e0b' : '#dc2626',
    color: '#f8fafc',
  };

  if (!isOpen) {
    return (
      <button
        style={badgeStyle}
        onClick={() => setIsOpen(true)}
        title="Click to open Dev Tools"
        onMouseOver={(e) => { e.currentTarget.style.opacity = '0.9'; }}
        onMouseOut={(e) => { e.currentTarget.style.opacity = '1'; }}
      >
        <span>{colors.label}</span>
        <span style={{ opacity: 0.7, fontSize: '10px' }}>▼</span>
      </button>
    );
  }

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <span style={{ fontWeight: 600 }}>🛠️ Dev Tools</span>
        <button
          onClick={() => setIsOpen(false)}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: '18px',
            padding: '0 4px',
          }}
        >
          ×
        </button>
      </div>

      <div style={contentStyle}>
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
            Loading...
          </div>
        ) : config ? (
          <>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}>
                CURRENT DATA SET
              </div>
              <div style={{ fontWeight: 600 }}>
                {config.data_set_id} - {config.data_set_name}
              </div>
              <div style={{ marginTop: '8px' }}>
                <span style={backendStatusStyle}>
                  {backendStatus === 'live' ? '● Backend Live' : backendStatus === 'restarting' ? '◐ Backend Restarting' : '○ Backend Offline'}
                </span>
              </div>
            </div>

            <div style={{ marginBottom: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '8px' }}>
                DATABASE MODE
              </div>
              
              {Object.entries(config.available_modes).map(([mode, info]) => (
                <button
                  key={mode}
                  style={modeButtonStyle(config.db_mode === mode)}
                  onClick={() => handleSwitchMode(mode)}
                  disabled={isPendingSwitch}
                >
                  <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                    {info.label}
                    {config.db_mode === mode && (
                      <span style={{ marginLeft: '8px', color: '#22c55e' }}>✓</span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    {info.description}
                  </div>
                </button>
              ))}
            </div>

            <div style={{ marginBottom: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '8px' }}>
                DATA SYNC
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    backgroundColor: '#1e293b',
                    color: '#f8fafc',
                    cursor: isPendingSwitch ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '12px',
                    opacity: isPendingSwitch ? 0.6 : 1,
                    transition: 'all 0.2s',
                  }}
                  onClick={() => handleSync('download')}
                  disabled={isPendingSwitch}
                  title="Copy remote database into local"
                >
                  ⬇ Download
                  <div style={{ fontSize: '10px', fontWeight: 400, color: '#94a3b8', marginTop: '2px' }}>
                    Remote → Local
                  </div>
                </button>
                <button
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    backgroundColor: '#1e293b',
                    color: '#f8fafc',
                    cursor: isPendingSwitch ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '12px',
                    opacity: isPendingSwitch ? 0.6 : 1,
                    transition: 'all 0.2s',
                  }}
                  onClick={() => handleSync('upload')}
                  disabled={isPendingSwitch}
                  title="Copy local database into remote (overwrites team data)"
                >
                  ⬆ Upload
                  <div style={{ fontSize: '10px', fontWeight: 400, color: '#94a3b8', marginTop: '2px' }}>
                    Local → Remote
                  </div>
                </button>
              </div>
            </div>

            {message && (
              <div
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: message.type === 'success' ? '#166534' : '#7f1d1d',
                  marginBottom: '8px',
                  fontSize: '12px',
                }}
              >
                {message.text}
              </div>
            )}

            {isSyncing && (
              <div style={{ marginBottom: '10px' }}>
                <div style={{
                  height: '8px',
                  backgroundColor: '#334155',
                  borderRadius: '999px',
                  overflow: 'hidden',
                  border: '1px solid #475569'
                }}>
                  <div style={{
                    width: `${Math.max(2, Math.min(100, syncProgress))}%`,
                    height: '100%',
                    backgroundColor: '#22c55e',
                    transition: 'width 0.35s ease'
                  }} />
                </div>
                <div style={{ marginTop: '6px', fontSize: '11px', color: '#94a3b8' }}>
                  {syncMessage || (syncDirection === 'local-to-remote' ? 'Syncing local data to remote...' : 'Syncing remote data to local...')} ({syncProgress}%)
                </div>
              </div>
            )}

          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
            Failed to load config
          </div>
        )}
      </div>
    </div>
  );
}

export default DevTools;
