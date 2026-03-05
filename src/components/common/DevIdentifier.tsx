/**
 * DevIdentifier – hover-to-reveal component name badge for development.
 *
 * Usage A — JSX wrapper:
 *   <DevIdentifier name="OrderDetail">
 *     <div className="p-4">…</div>
 *   </DevIdentifier>
 *
 * Usage B — HOC (ideal for export lines):
 *   export default withDevIdentifier(OrderDetail, 'OrderDetail');
 *   export default withDevIdentifier(ShippingPanel, 'ShippingPanel', 'teal');
 *
 * Controlled by VITE_DEBUG_BADGES env-var (same flag as DevBadge).
 * Set `VITE_DEBUG_BADGES='true'` in .env to enable; omit to disable.
 *
 * In production builds (or when the flag is off) the wrapper renders
 * children directly with zero overhead — no extra DOM nodes.
 *
 * Variant colours:
 *   indigo → Detail pages
 *   teal   → Panels
 *   amber  → Cards
 *   rose   → Other / misc components
 */
import React, { useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Variant = 'indigo' | 'teal' | 'amber' | 'rose';

interface DevIdentifierProps {
  /** Component / panel / card name to display */
  name: string;
  /** Badge color scheme */
  variant?: Variant;
  /** Children to render */
  children: React.ReactNode;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const VARIANT_CLASSES: Record<Variant, string> = {
  indigo: 'bg-indigo-600/90 text-white',
  teal:   'bg-teal-600/90 text-white',
  amber:  'bg-amber-500/90 text-white',
  rose:   'bg-rose-600/90 text-white',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DevIdentifier({ name, variant = 'indigo', children }: DevIdentifierProps) {
  const [hovered, setHovered] = useState(false);

  // Gate: skip entirely when badges are disabled
  if (import.meta.env.VITE_DEBUG_BADGES !== 'true') {
    return <>{children}</>;
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Hover badge – top-right, fades in/out */}
      <div
        className={`absolute top-0 right-0 z-[9999] transition-opacity duration-150 pointer-events-none ${
          hovered ? 'opacity-100' : 'opacity-0'
        }`}
      >
        <span
          className={`inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium tracking-wide rounded-bl shadow-sm whitespace-nowrap ${VARIANT_CLASSES[variant]}`}
        >
          {name}
        </span>
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// HOC — wrap a component's export for zero-touch integration
// ---------------------------------------------------------------------------

/**
 * Higher-order component that wraps a component with DevIdentifier.
 *
 * @example
 * // At the bottom of a file:
 * export default withDevIdentifier(OrderDetail, 'OrderDetail');
 * export default withDevIdentifier(ShippingPanel, 'ShippingPanel', 'teal');
 */
export function withDevIdentifier<P extends object>(
  Component: React.ComponentType<P>,
  name: string,
  variant: Variant = 'indigo',
): React.FC<P> {
  // Fast path: when badges are disabled, return the original component
  if (import.meta.env.VITE_DEBUG_BADGES !== 'true') {
    return Component as React.FC<P>;
  }

  const Wrapped: React.FC<P> = (props) => (
    <DevIdentifier name={name} variant={variant}>
      <Component {...props} />
    </DevIdentifier>
  );
  Wrapped.displayName = `DevId(${name})`;
  return Wrapped;
}
