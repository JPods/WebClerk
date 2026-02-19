/**
 * DevBadge – small mono-font label shown on components during development.
 *
 * Controlled by the VITE_DEBUG_BADGES env-var.
 * Set `VITE_DEBUG_BADGES='true'` in .env to show badges;
 * remove or set to any other value to hide them.
 */

interface DevBadgeProps {
  /** Text to display inside the badge */
  label: string;
  /** Color scheme – defaults to indigo */
  variant?: 'indigo' | 'teal';
  /** Extra Tailwind classes for positioning (e.g. "mr-2", "absolute top-1 left-1 z-10") */
  className?: string;
}

const COLOR_MAP = {
  indigo:
    'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-300',
  teal: 'bg-teal-100 text-teal-600 dark:bg-teal-900/40 dark:text-teal-300',
} as const;

export function DevBadge({
  label,
  variant = 'indigo',
  className = '',
}: DevBadgeProps) {
  if (import.meta.env.VITE_DEBUG_BADGES !== 'true') return null;

  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-mono font-normal tracking-wide uppercase ${COLOR_MAP[variant]} rounded ${className}`.trim()}
    >
      {label}
    </span>
  );
}
