/**
 * ToolbarIcon — renders a toolbar button using the user's preferred style.
 *
 * Styles: 'glass' (WC2 PNGs), 'phosphor' (duotone SVG), 'minimal' (text)
 * Preference stored in localStorage: wc3_button_style
 * Picker in MacTopBar next to theme toggle.
 */
import React, { useState } from 'react';
import type { Icon as PhosphorIcon } from '@phosphor-icons/react';

// ---------------------------------------------------------------------------
// Style preference
// ---------------------------------------------------------------------------
export type ButtonStyle = 'glass' | 'phosphor' | 'minimal';

export function getButtonStyle(): ButtonStyle {
  return (localStorage.getItem('wc3_button_style') as ButtonStyle) || 'glass';
}

export function setButtonStyle(style: ButtonStyle) {
  localStorage.setItem('wc3_button_style', style);
  window.dispatchEvent(new Event('wc3-button-style-changed'));
}

// ---------------------------------------------------------------------------
// Icon mapping — each action has a glass PNG name, Phosphor component, and emoji/text
// ---------------------------------------------------------------------------
export interface ToolbarAction {
  glass: string;           // PNG filename in button_glass/ (without .png)
  phosphor: PhosphorIcon;  // Phosphor duotone icon component
  minimal: string;         // Text label for minimal style
  emoji?: string;          // Optional emoji for minimal style
}

// ---------------------------------------------------------------------------
// Glass button renderer (3-state sprite)
// ---------------------------------------------------------------------------
const GBS = 56;

const GlassRenderer: React.FC<{
  icon: string; title: string; onClick?: (e?: React.MouseEvent) => void;
  disabled?: boolean; active?: boolean;
}> = ({ icon, title, onClick, disabled, active }) => {
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
        backgroundImage: `url(/src/components/ui/button/button_glass/${encodeURIComponent(icon)}.png)`,
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
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.3 : 1,
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
  style?: ButtonStyle;  // override user preference for testing
}

export default function ToolbarIcon({
  action, title, onClick, disabled, active, danger, style: styleOverride,
}: ToolbarIconProps) {
  const btnStyle = styleOverride || getButtonStyle();

  switch (btnStyle) {
    case 'glass':
      return <GlassRenderer icon={action.glass} title={title} onClick={onClick} disabled={disabled} active={active} />;
    case 'phosphor':
      return <PhosphorRenderer icon={action.phosphor} title={title} onClick={onClick} disabled={disabled} active={active} danger={danger} />;
    case 'minimal':
      return <MinimalRenderer label={action.minimal} emoji={action.emoji} title={title} onClick={onClick} disabled={disabled} active={active} danger={danger} />;
    default:
      return <GlassRenderer icon={action.glass} title={title} onClick={onClick} disabled={disabled} active={active} />;
  }
}
