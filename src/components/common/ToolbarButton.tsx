/**
 * ToolbarButton — Phosphor duotone icon button for DataBrowser toolbars.
 *
 * Sized for visual weight at 44px. Duotone gives depth without glass chrome.
 * Hover lifts, active presses, disabled fades. Fun buttons make work fun.
 *
 * MIT licensed icons — no 4D IP concerns.
 */
import React, { useState } from 'react';
import type { Icon } from '@phosphor-icons/react';

interface ToolbarButtonProps {
  icon: Icon;
  title: string;
  onClick?: (e?: React.MouseEvent) => void;
  disabled?: boolean;
  active?: boolean;
  danger?: boolean;
  size?: number;
}

export default function ToolbarButton({
  icon: IconComponent,
  title,
  onClick,
  disabled = false,
  active = false,
  danger = false,
  size = 44,
}: ToolbarButtonProps) {
  const [hover, setHover] = useState(false);
  const [pressed, setPressed] = useState(false);

  const iconSize = Math.round(size * 0.55);

  const baseColor = danger ? '#e05252' : active ? '#4ec98c' : '#9cdcfe';
  const hoverColor = danger ? '#ff6b6b' : active ? '#6fe8a8' : '#bde4ff';
  const bgBase = 'transparent';
  const bgHover = danger ? 'rgba(224, 82, 82, 0.12)' : active ? 'rgba(78, 201, 140, 0.12)' : 'rgba(156, 220, 254, 0.10)';
  const bgPressed = danger ? 'rgba(224, 82, 82, 0.22)' : active ? 'rgba(78, 201, 140, 0.22)' : 'rgba(156, 220, 254, 0.20)';

  return (
    <button
      style={{
        width: size,
        height: size,
        padding: 0,
        border: active ? '2px solid ' + baseColor : '2px solid transparent',
        borderRadius: 8,
        background: pressed ? bgPressed : hover ? bgHover : bgBase,
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.3 : 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.15s ease',
        transform: pressed ? 'scale(0.92)' : hover && !disabled ? 'scale(1.08)' : 'scale(1)',
        flexShrink: 0,
      }}
      title={title}
      disabled={disabled}
      onClick={(e) => onClick?.(e)}
      onMouseEnter={() => !disabled && setHover(true)}
      onMouseLeave={() => { setHover(false); setPressed(false); }}
      onMouseDown={() => !disabled && setPressed(true)}
      onMouseUp={() => !disabled && setPressed(false)}
    >
      <IconComponent
        size={iconSize}
        weight="duotone"
        color={disabled ? '#666' : hover ? hoverColor : baseColor}
        style={{ transition: 'color 0.15s ease' }}
      />
    </button>
  );
}
