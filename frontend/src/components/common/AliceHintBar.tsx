/**
 * AliceHintBar — shows Alice coaching hints, WCHQ tips, and power user suggestions.
 *
 * Drop into any page:
 *   <AliceHintBar model="order" />
 *
 * Shows hints relevant to the current model. Dismissible.
 * Sources: Alice (local), WCHQ (synced), Power users (shared).
 */
import React from 'react';
import { useAlice, AliceHint } from '@/context/AliceContext';

interface AliceHintBarProps {
  model?: string;
  field?: string;
  maxHints?: number;
}

const SOURCE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  alice: { bg: '#1a3a2e', text: '#4ade80', label: 'Alice' },
  wchq: { bg: '#1a2a3e', text: '#60a5fa', label: 'WCHQ' },
  power_user: { bg: '#3a2a1a', text: '#fbbf24', label: 'Tip' },
};

const SOURCE_COLORS_LIGHT: Record<string, { bg: string; text: string; label: string }> = {
  alice: { bg: '#dcfce7', text: '#166534', label: 'Alice' },
  wchq: { bg: '#dbeafe', text: '#1e40af', label: 'WCHQ' },
  power_user: { bg: '#fef3c7', text: '#92400e', label: 'Tip' },
};

export default function AliceHintBar({ model, field, maxHints = 3 }: AliceHintBarProps) {
  const { hints, hintsForModel, hintsForField, dismissHint } = useAlice();

  const relevant = field && model
    ? hintsForField(model, field)
    : model
      ? hintsForModel(model)
      : hints;

  const visible = relevant.filter((h) => !h.dismissed).slice(0, maxHints);

  if (!visible.length) return null;

  // Detect dark mode from body or parent
  const isDark = typeof document !== 'undefined' && document.body.classList.contains('dark')
    || (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches);

  return (
    <div data-wc="alice-hint-bar" style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '6px 12px' }}>
      {visible.map((hint) => {
        const colors = (isDark ? SOURCE_COLORS : SOURCE_COLORS_LIGHT)[hint.source] || SOURCE_COLORS.alice;
        return (
          <div
            key={hint.id}
            data-wc={`alice-hint-${hint.id}`}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '4px 10px', borderRadius: 4,
              background: colors.bg, color: colors.text,
              fontSize: 11,
            }}
          >
            <span style={{
              fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
              padding: '1px 5px', borderRadius: 2,
              background: colors.text + '22', color: colors.text,
            }}>
              {colors.label}
            </span>
            <span style={{ flex: 1 }}>{hint.message}</span>
            {hint.priority >= 2 && (
              <span style={{ fontSize: 9, fontWeight: 700, color: '#ef4444' }}>URGENT</span>
            )}
            <button
              data-wc={`alice-dismiss-${hint.id}`}
              onClick={() => dismissHint(hint.id)}
              style={{
                background: 'none', border: 'none', color: colors.text,
                cursor: 'pointer', fontSize: 13, padding: '0 4px', opacity: 0.6,
              }}
              title="Dismiss"
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
