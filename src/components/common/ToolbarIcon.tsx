/**
 * ToolbarIcon — renders a toolbar button using the selected style.
 *
 * Styles discovered from src/components/ui/button/{folder}/ — each folder
 * is a button set with its own README.md. PNG sets use 3-state sprites.
 * Phosphor uses duotone SVG. Minimal uses text + emoji.
 *
 * Preference stored in localStorage: wc3_button_style
 * Company sets once at deployment. User can override.
 */
import React, { useState, useEffect } from 'react';
import type { Icon as PhosphorIcon } from '@phosphor-icons/react';
import type { ToolbarAction, ButtonStyleName } from './toolbarActions';
import { AVAILABLE_PNG_STYLES } from './toolbarActions';

// ---------------------------------------------------------------------------
// Style preference
// ---------------------------------------------------------------------------
export function getButtonStyle(): ButtonStyleName {
  return (localStorage.getItem('wc3_button_style') as ButtonStyleName) || 'button_glass';
}

export function setButtonStyle(style: ButtonStyleName) {
  localStorage.setItem('wc3_button_style', style);
  window.dispatchEvent(new Event('wc3-button-style-changed'));
}

// ---------------------------------------------------------------------------
// PNG sprite renderer (works for any folder: button_glass, OSX, etc.)
// ---------------------------------------------------------------------------
const GBS = 56;

const PngRenderer: React.FC<{
  folder: string; file: string; title: string;
  onClick?: (e?: React.MouseEvent) => void; disabled?: boolean; active?: boolean;
}> = ({ folder, file, title, onClick, disabled, active }) => {
  const [st, setSt] = useState<0 | 1 | 2>(0);
  return (
    <button
      style={{
        width: GBS, height: GBS, padding: 0, border: 'none', background: 'transparent',
        cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.35 : active ? 1 : 0.8,
        outline: active ? '2px solid var(--db-accent, #9cdcfe)' : 'none',
        borderRadius: 4, overflow: 'hidden', flexShrink: 0,
      }}
      title={title} disabled={disabled} onClick={(e) => onClick?.(e)}
      onMouseEnter={() => !disabled && setSt(1)} onMouseLeave={() => setSt(0)}
      onMouseDown={() => !disabled && setSt(2)} onMouseUp={() => !disabled && setSt(1)}
    >
      <div style={{
        width: GBS, height: GBS * 3,
        backgroundImage: `url(/src/components/ui/button/${folder}/${encodeURIComponent(file)}.png)`,
        backgroundSize: `${GBS}px auto`, backgroundRepeat: 'no-repeat',
        transform: `translateY(${-st * GBS}px)`,
      }} />
    </button>
  );
};

// ---------------------------------------------------------------------------
// Phosphor duotone renderer
// ---------------------------------------------------------------------------
const PhosphorRenderer: React.FC<{
  icon: PhosphorIcon; title: string; onClick?: (e?: React.MouseEvent) => void;
  disabled?: boolean; active?: boolean; danger?: boolean;
}> = ({ icon: IconComp, title, onClick, disabled, active, danger }) => {
  const [hover, setHover] = useState(false);
  const [pressed, setPressed] = useState(false);
  const size = 44;
  const iconSize = Math.round(size * 0.55);
  const baseColor = danger ? '#e05252' : active ? '#4ec98c' : '#9cdcfe';
  const hoverColor = danger ? '#ff6b6b' : active ? '#6fe8a8' : '#bde4ff';
  const bgHover = danger ? 'rgba(224,82,82,0.12)' : active ? 'rgba(78,201,140,0.12)' : 'rgba(156,220,254,0.10)';
  const bgPressed = danger ? 'rgba(224,82,82,0.22)' : active ? 'rgba(78,201,140,0.22)' : 'rgba(156,220,254,0.20)';

  return (
    <button
      style={{
        width: size, height: size, padding: 0,
        border: active ? `2px solid ${baseColor}` : '2px solid transparent',
        borderRadius: 8,
        background: pressed ? bgPressed : hover ? bgHover : 'transparent',
        cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.3 : 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.15s ease',
        transform: pressed ? 'scale(0.92)' : hover && !disabled ? 'scale(1.08)' : 'scale(1)',
        flexShrink: 0,
      }}
      title={title} disabled={disabled} onClick={(e) => onClick?.(e)}
      onMouseEnter={() => !disabled && setHover(true)}
      onMouseLeave={() => { setHover(false); setPressed(false); }}
      onMouseDown={() => !disabled && setPressed(true)}
      onMouseUp={() => !disabled && setPressed(false)}
    >
      <IconComp size={iconSize} weight="duotone"
        color={disabled ? '#666' : hover ? hoverColor : baseColor}
        style={{ transition: 'color 0.15s ease' }} />
    </button>
  );
};

// ---------------------------------------------------------------------------
// Minimal text renderer
// ---------------------------------------------------------------------------
const MinimalRenderer: React.FC<{
  label: string; emoji?: string; title: string; onClick?: (e?: React.MouseEvent) => void;
  disabled?: boolean; active?: boolean; danger?: boolean;
}> = ({ label, emoji, title, onClick, disabled, active, danger }) => {
  const color = danger ? '#e05252' : active ? '#4ec98c' : '#9cdcfe';
  return (
    <button
      style={{
        padding: '4px 8px', border: active ? `1px solid ${color}` : '1px solid transparent',
        borderRadius: 4, background: 'transparent',
        color: disabled ? '#666' : color, cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.4 : 1, fontSize: 12, fontWeight: 600,
        flexShrink: 0, whiteSpace: 'nowrap',
      }}
      title={title} disabled={disabled} onClick={(e) => onClick?.(e)}
    >
      {emoji ? `${emoji} ${label}` : label}
    </button>
  );
};

// ---------------------------------------------------------------------------
// ToolbarIcon — the unified component
// ---------------------------------------------------------------------------
export interface ToolbarIconProps {
  action: ToolbarAction;
  title: string;
  onClick?: (e?: React.MouseEvent) => void;
  disabled?: boolean;
  active?: boolean;
  danger?: boolean;
}

export default function ToolbarIcon({
  action, title, onClick, disabled, active, danger,
}: ToolbarIconProps) {
  const [style, setStyle] = useState<ButtonStyleName>(getButtonStyle);

  // Listen for style changes from the picker
  useEffect(() => {
    const handler = () => setStyle(getButtonStyle());
    window.addEventListener('wc3-button-style-changed', handler);
    return () => window.removeEventListener('wc3-button-style-changed', handler);
  }, []);

  // PNG-based styles (any folder)
  if ((AVAILABLE_PNG_STYLES as readonly string[]).includes(style)) {
    const file = action.png[style];
    if (file) {
      return <PngRenderer folder={style} file={file} title={title} onClick={onClick} disabled={disabled} active={active} />;
    }
    // Fallback to button_glass if this set doesn't have the icon
    const fallback = action.png['button_glass'];
    if (fallback) {
      return <PngRenderer folder="button_glass" file={fallback} title={title} onClick={onClick} disabled={disabled} active={active} />;
    }
  }

  // Phosphor duotone
  if (style === 'phosphor') {
    return <PhosphorRenderer icon={action.phosphor} title={title} onClick={onClick} disabled={disabled} active={active} danger={danger} />;
  }

  // Minimal text
  return <MinimalRenderer label={action.minimal} emoji={action.emoji} title={title} onClick={onClick} disabled={disabled} active={active} danger={danger} />;
}
