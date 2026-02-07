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

  // Only show in dev mode
  const isDev = import.meta.env.VITE_ENV === 'DEV' || import.meta.env.DEV;
  
  // Fetch config on mount to show the badge
  const fetchConfig = useCallback(async () => {
    setIsLoading(true);
    try {
      // Try dedicated dev_config endpoint first
      const response = await fetch('/wcapi/dev/config/');
      if (response.ok) {
        const json = await response.json();
        // Handle nested response: { data: { data: { ... } } } or { data: { ... } }
        const configData = json.data?.data || json.data;
        setConfig(configData);
      }
      // If endpoint doesn't exist (404), just don't show config - this is expected
    } catch {
      // Network error - silently fail, dev config is optional
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch config on mount (for badge display)
  useEffect(() => {
    if (isDev) {
      fetchConfig();
    }
  }, [isDev, fetchConfig]);

  // Also refresh when panel opens
  useEffect(() => {
    if (isOpen) {
      fetchConfig();
    }
  }, [isOpen, fetchConfig]);

  const handleSwitchMode = async (newMode: string) => {
    setIsSwitching(true);
    setMessage(null);
    
    try {
      const response = await fetch('/wcapi/dev/switch/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });
      
      const json = await response.json();
      // Handle nested response structure
      const data = json.data?.data || json.data || json;
      
      if (response.ok) {
        setMessage({ type: 'success', text: json.message || data.message || `Switched to ${newMode}` });
        if (data?.changed) {
          // Refresh config
          await fetchConfig();
        }
      } else {
        setMessage({ type: 'error', text: data.message });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to switch mode' });
    } finally {
      setIsSwitching(false);
    }
  };

  const handleRestart = async () => {
    if (!confirm('This will restart both frontend and backend servers. Continue?')) {
      return;
    }
    
    setMessage({ type: 'success', text: 'Restarting servers...' });
    
    try {
      await fetch('/wcapi/dev/restart/', { method: 'POST' });
      // Server will restart, so we won't get a response
      setMessage({ type: 'success', text: 'Restart initiated. Page will reload when ready.' });
      
      // Poll until server is back up
      let attempts = 0;
      const maxAttempts = 30;
      const checkServer = async () => {
        try {
          const resp = await fetch('/wcapi/get/?model_name=system_info');
          if (resp.ok) {
            window.location.reload();
            return;
          }
        } catch {
          // Server not ready yet
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkServer, 1000);
        } else {
          setMessage({ type: 'error', text: 'Server restart timeout. Please refresh manually.' });
        }
      };
      
      setTimeout(checkServer, 3000);
    } catch {
      // Expected - server is restarting
    }
  };

  if (!isDev) return null;

  const posStyle = positionStyles[position];
  const currentMode = config?.db_mode || 'remote';
  const colors = modeColors[currentMode] || modeColors.remote;

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
    cursor: isSwitching ? 'not-allowed' : 'pointer',
    textAlign: 'left',
    opacity: isSwitching ? 0.6 : 1,
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
                  disabled={isSwitching}
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

            <div style={{ 
              marginTop: '12px', 
              padding: '12px', 
              backgroundColor: '#1e293b', 
              borderRadius: '8px',
              fontSize: '11px', 
              color: '#94a3b8',
              lineHeight: '1.6'
            }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
                ⚠️ After switching, restart Django:
              </div>
              <div>1. Stop Django server (Ctrl+C in terminal)</div>
              <div>2. Run: <code style={{ backgroundColor: '#334155', padding: '2px 6px', borderRadius: '4px', color: '#f8fafc' }}>
                python manage.py runserver
              </code></div>
            </div>
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
