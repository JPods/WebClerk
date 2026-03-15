/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * DataSetBadge Component
 * 
 * Visual indicator showing current data set (DEV/STAGING/PRODUCTION).
 * Displays a warning if frontend and backend data sets don't match.
 */

import React from 'react';
import { useDataSetInfo } from '../hooks/useDataSetInfo';

interface DataSetBadgeProps {
  /** Show detailed info on hover/click */
  showDetails?: boolean;
  /** Position of the badge */
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'inline';
  /** Custom class name */
  className?: string;
}

const positionStyles: Record<string, React.CSSProperties> = {
  'top-left': { position: 'fixed', top: '8px', left: '8px', zIndex: 9999 },
  'top-right': { position: 'fixed', top: '8px', right: '8px', zIndex: 9999 },
  'bottom-left': { position: 'fixed', bottom: '8px', left: '8px', zIndex: 9999 },
  'bottom-right': { position: 'fixed', bottom: '8px', right: '8px', zIndex: 9999 },
  'inline': {},
};

const colorSchemes: Record<string, { bg: string; text: string; border: string }> = {
  DEV: { bg: '#22c55e20', text: '#16a34a', border: '#22c55e' },
  STAGING: { bg: '#f59e0b20', text: '#d97706', border: '#f59e0b' },
  PRODUCTION: { bg: '#ef444420', text: '#dc2626', border: '#ef4444' },
  PROD: { bg: '#ef444420', text: '#dc2626', border: '#ef4444' },
  LOCAL: { bg: '#3b82f620', text: '#2563eb', border: '#3b82f6' },
  UNKNOWN: { bg: '#6b728020', text: '#4b5563', border: '#6b7280' },
};

export function DataSetBadge({ 
  showDetails = false, 
  position = 'inline',
  className = '',
}: DataSetBadgeProps): React.ReactElement {
  const { frontend, backend, isLoading, error, isMatch } = useDataSetInfo();
  const [expanded, setExpanded] = React.useState(false);

  const colors = colorSchemes[frontend.id.toUpperCase()] || colorSchemes.UNKNOWN;
  const posStyle = positionStyles[position];

  const baseStyle: React.CSSProperties = {
    ...posStyle,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    fontSize: '12px',
    cursor: showDetails ? 'pointer' : 'default',
  };

  const badgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '4px',
    backgroundColor: colors.bg,
    color: colors.text,
    border: `1px solid ${colors.border}`,
    fontWeight: 600,
  };

  const mismatchStyle: React.CSSProperties = {
    ...badgeStyle,
    backgroundColor: '#ef444440',
    color: '#dc2626',
    border: '2px solid #ef4444',
    animation: 'pulse 2s infinite',
  };

  const detailsStyle: React.CSSProperties = {
    marginTop: '8px',
    padding: '12px',
    backgroundColor: '#f8fafc',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    fontSize: '11px',
    lineHeight: '1.6',
    maxWidth: '300px',
  };

  return (
    <div style={baseStyle} className={className}>
      <div 
        style={isMatch === false ? mismatchStyle : badgeStyle}
        onClick={() => showDetails && setExpanded(!expanded)}
        title={showDetails ? 'Click for details' : frontend.name}
      >
        <span>{frontend.id}</span>
        {isMatch === false && <span>⚠️</span>}
        {isLoading && <span>...</span>}
      </div>

      {showDetails && expanded && (
        <div style={detailsStyle}>
          <div><strong>Frontend:</strong> {frontend.id} - {frontend.name}</div>
          {backend?.data_set && (
            <>
              <div><strong>Backend:</strong> {backend.data_set.id} - {backend.data_set.name}</div>
              <div><strong>Database:</strong> {backend.database?.name ?? 'N/A'} @ {backend.database?.host ?? 'N/A'}</div>
              <div><strong>Debug Mode:</strong> {backend.server?.debug ? 'Yes' : 'No'}</div>
            </>
          )}
          {error && <div style={{ color: '#dc2626' }}><strong>Error:</strong> {error}</div>}
          {isMatch === false && (
            <div style={{ color: '#dc2626', marginTop: '8px', fontWeight: 'bold' }}>
              ⚠️ DATA SET MISMATCH - Frontend and Backend are pointing to different environments!
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DataSetBadge;
