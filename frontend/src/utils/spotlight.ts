/**
 * spotlight.ts — Flash any UI component to draw attention.
 *
 * Two modes:
 *   Manual:  Trainer presses Cmd+Shift+S → flashes element under cursor.
 *   Guided:  Alice sends a sequence of steps → each flashes an element,
 *            shows a hint, waits for the user to act, then advances.
 *
 * The flash uses the existing data-wc attribute system. Every meaningful
 * component in WC3 has a data-wc tag — spotlight walks up from any
 * element to find the nearest one.
 *
 * CSS animation is injected once. No external stylesheet needed.
 */

// ── CSS injection (once) ───────────────────────────────────────

let _cssInjected = false;

function injectSpotlightCSS() {
  if (_cssInjected) return;
  _cssInjected = true;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes wc-spotlight-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
      30%  { box-shadow: 0 0 12px 6px rgba(59, 130, 246, 0.5); }
      60%  { box-shadow: 0 0 20px 10px rgba(59, 130, 246, 0.3); }
      100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }
    .wc-spotlight {
      animation: wc-spotlight-pulse 1s ease-out;
      outline: 2px solid rgba(59, 130, 246, 0.8) !important;
      outline-offset: 2px;
      border-radius: 4px;
      z-index: 9999;
      position: relative;
    }
    .wc-spotlight-hint {
      position: absolute;
      top: -28px;
      left: 0;
      background: #1e40af;
      color: #fff;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 4px;
      white-space: nowrap;
      z-index: 10000;
      pointer-events: none;
      animation: wc-spotlight-pulse 1s ease-out;
    }
  `;
  document.head.appendChild(style);
}

// ── Core flash ─────────────────────────────────────────────────

/**
 * Flash a single element. Finds nearest data-wc ancestor if the
 * target doesn't have one. Returns the flashed element (or null).
 */
export function flashElement(el: Element | null, hint?: string): Element | null {
  if (!el) return null;
  injectSpotlightCSS();

  // Walk up to nearest data-wc element
  let target: Element | null = el;
  while (target && !target.hasAttribute('data-wc')) {
    target = target.parentElement;
  }
  if (!target) target = el; // flash whatever we have

  // Remove any existing spotlight on this element
  target.classList.remove('wc-spotlight');
  // Force reflow so re-adding triggers animation
  void (target as HTMLElement).offsetWidth;
  target.classList.add('wc-spotlight');

  // Add hint label if provided
  let hintEl: HTMLElement | null = null;
  if (hint) {
    hintEl = document.createElement('div');
    hintEl.className = 'wc-spotlight-hint';
    hintEl.textContent = hint;
    (target as HTMLElement).style.position = (target as HTMLElement).style.position || 'relative';
    target.appendChild(hintEl);
  }

  // Clean up after animation
  setTimeout(() => {
    target!.classList.remove('wc-spotlight');
    if (hintEl && hintEl.parentElement) hintEl.remove();
  }, 1200);

  return target;
}

/**
 * Flash a component by its data-wc value.
 * Used by Alice-guided sequences.
 */
export function flashByWcId(wcId: string, hint?: string): Element | null {
  const el = document.querySelector(`[data-wc="${wcId}"]`);
  return flashElement(el, hint);
}

// ── Manual spotlight (Cmd+Shift+S) ─────────────────────────────

let _lastMouseTarget: Element | null = null;

function trackMouse(e: MouseEvent) {
  _lastMouseTarget = e.target as Element;
}

function handleSpotlightKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 's' || e.key === 'S')) {
    e.preventDefault();
    const target = _lastMouseTarget || document.activeElement;
    const flashed = flashElement(target);

    // Log to Alice — which component trainers spotlight
    if (flashed) {
      const wcId = flashed.getAttribute('data-wc') || 'unknown';
      logSpotlight(wcId, 'manual');
    }
  }
}

let _manualListenersActive = false;

export function enableManualSpotlight() {
  if (_manualListenersActive) return;
  _manualListenersActive = true;
  document.addEventListener('mousemove', trackMouse, { passive: true });
  document.addEventListener('keydown', handleSpotlightKey);
}

export function disableManualSpotlight() {
  if (!_manualListenersActive) return;
  _manualListenersActive = false;
  document.removeEventListener('mousemove', trackMouse);
  document.removeEventListener('keydown', handleSpotlightKey);
}

// ── Alice-guided sequences ─────────────────────────────────────

export interface SpotlightStep {
  wc: string;       // data-wc value to flash
  hint?: string;    // hint text shown above the element
  wait?: 'click' | 'input' | 'time';  // what advances to next step
  delay?: number;   // ms delay if wait='time' (default 3000)
}

let _activeSequence: { steps: SpotlightStep[]; index: number; cleanup?: () => void } | null = null;

/**
 * Run a guided spotlight sequence. Alice calls this with a recipe.
 * Each step flashes an element and optionally waits for user interaction.
 */
export function runSequence(steps: SpotlightStep[], onComplete?: () => void) {
  stopSequence();
  if (!steps.length) return;
  _activeSequence = { steps, index: 0 };
  advanceSequence(onComplete);
}

function advanceSequence(onComplete?: () => void) {
  if (!_activeSequence) return;
  const { steps, index } = _activeSequence;

  // Clean up previous step listener
  if (_activeSequence.cleanup) {
    _activeSequence.cleanup();
    _activeSequence.cleanup = undefined;
  }

  if (index >= steps.length) {
    _activeSequence = null;
    onComplete?.();
    return;
  }

  const step = steps[index];
  const el = flashByWcId(step.wc, step.hint);
  logSpotlight(step.wc, 'guided');

  const waitType = step.wait || 'time';
  const delay = step.delay || 3000;

  if (waitType === 'time' || !el) {
    const timer = setTimeout(() => {
      if (_activeSequence) {
        _activeSequence.index++;
        advanceSequence(onComplete);
      }
    }, delay);
    _activeSequence.cleanup = () => clearTimeout(timer);
  } else if (waitType === 'click') {
    const handler = () => {
      el.removeEventListener('click', handler);
      if (_activeSequence) {
        // Brief pause after click so user sees the result
        setTimeout(() => {
          if (_activeSequence) {
            _activeSequence.index++;
            advanceSequence(onComplete);
          }
        }, 500);
      }
    };
    el.addEventListener('click', handler);
    _activeSequence.cleanup = () => el.removeEventListener('click', handler);
  } else if (waitType === 'input') {
    const handler = () => {
      el.removeEventListener('input', handler);
      // Wait a beat after input
      setTimeout(() => {
        if (_activeSequence) {
          _activeSequence.index++;
          advanceSequence(onComplete);
        }
      }, 800);
    };
    el.addEventListener('input', handler);
    _activeSequence.cleanup = () => el.removeEventListener('input', handler);
  }
}

export function stopSequence() {
  if (_activeSequence?.cleanup) _activeSequence.cleanup();
  _activeSequence = null;
}

export function isSequenceActive(): boolean {
  return _activeSequence !== null;
}

// ── Logging ────────────────────────────────────────────────────

async function logSpotlight(wcId: string, mode: 'manual' | 'guided') {
  try {
    const { saveRecord } = await import('@/api/wcapi');
    saveRecord('ai_message', {
      kind: 'help_lookup',
      sender: 'user',
      receiver: 'alice',
      subject: `spotlight:${wcId}`,
      body: `Spotlight ${mode}: ${wcId} on ${window.location.pathname}`,
      status: 'read',
      context: {
        spotlight: true,
        mode,
        wc_id: wcId,
        page: window.location.pathname,
      },
    }).catch(() => {});
  } catch { /* non-critical */ }
}
