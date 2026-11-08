/**
 * FloatingSteps — the flight simulator's step (what to do, why, Prev/Next, the step picker) in a
 * floating panel the person drags, hides and shows, so the forms below get the whole height.
 *
 * Bill, 2026-11-08: "Step at the top talk important operation screen space. It would be best to
 * have the instructions in a floating window that can be shown or hidden to give operating space
 * on the active forms." Open/closed and position are the viewer's own (localStorage); the panel
 * renders without storage too.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';

export interface FloatingStep { step: number; title: string; model?: string; instruction: string; explanation?: string }

const OPEN_KEY = 'flightsim.steps.open';
const POS_KEY = 'flightsim.steps.pos';
const WIDTH = 420;

function readOpen(): boolean {
  try { return localStorage.getItem(OPEN_KEY) !== 'closed'; } catch { return true; }
}
function readPos(): { x: number; y: number } {
  try {
    const raw = localStorage.getItem(POS_KEY);
    if (raw) { const p = JSON.parse(raw); if (Number.isFinite(p.x) && Number.isFinite(p.y)) return p; }
  } catch { /* per-viewer convenience only */ }
  return { x: Math.max(8, (typeof window !== 'undefined' ? window.innerWidth : 1200) - WIDTH - 24), y: 88 };
}
function clamp(p: { x: number; y: number }) {
  const w = typeof window !== 'undefined' ? window.innerWidth : 1200;
  const h = typeof window !== 'undefined' ? window.innerHeight : 800;
  return { x: Math.min(Math.max(0, p.x), Math.max(0, w - 120)), y: Math.min(Math.max(0, p.y), Math.max(0, h - 40)) };
}

const FloatingSteps: React.FC<{
  steps: FloatingStep[];
  index: number;
  onIndex: (i: number) => void;
}> = ({ steps, index, onIndex }) => {
  const [open, setOpen] = useState<boolean>(readOpen);
  const [pos, setPos] = useState(() => clamp(readPos()));
  const drag = useRef<{ dx: number; dy: number } | null>(null);

  const toggle = useCallback(() => {
    setOpen((o) => { try { localStorage.setItem(OPEN_KEY, o ? 'closed' : 'open'); } catch { /* ignore */ } return !o; });
  }, []);

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest('button, select, a, input')) return;
    drag.current = { dx: e.clientX - pos.x, dy: e.clientY - pos.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    setPos(clamp({ x: e.clientX - drag.current.dx, y: e.clientY - drag.current.dy }));
  };
  const onPointerUp = (e: React.PointerEvent) => {
    if (!drag.current) return;
    drag.current = null;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    try { localStorage.setItem(POS_KEY, JSON.stringify(pos)); } catch { /* ignore */ }
  };
  useEffect(() => {
    const onResize = () => setPos((p) => clamp(p));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  if (!steps.length) return null;
  const i = Math.min(index, steps.length - 1);
  const step = steps[i];
  const handleProps = { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp };

  if (!open) {
    return (
      <div className="fs-float fs-float--closed" style={{ left: pos.x, top: pos.y }} data-wc="fs-float" {...handleProps}>
        <button className="fs-btn" onClick={toggle} title="Show the step">▸ Step {step.step} of {steps.length}: {step.title}</button>
      </div>
    );
  }
  return (
    <div className="fs-float" style={{ left: pos.x, top: pos.y, width: WIDTH }} data-wc="fs-float" role="dialog" aria-label="Simulation step">
      <div className="fs-float-bar" {...handleProps} title="Drag to move">
        <button className="fs-btn" onClick={toggle} title="Hide the step — the forms get the room">▾</button>
        <select className="fs-float-pick" value={i} onChange={(e) => onIndex(Number(e.target.value))} title="Go to a step">
          {steps.map((s, n) => <option key={s.step} value={n}>{s.step}. {s.title}</option>)}
        </select>
        {step.model && <span className="fs-steps-model">{step.model}</span>}
        <span className="fs-steps-spacer" />
        <button className="fs-btn" disabled={i === 0} onClick={() => onIndex(Math.max(0, i - 1))}>← Prev</button>
        <button className="fs-btn" disabled={i >= steps.length - 1} onClick={() => onIndex(Math.min(steps.length - 1, i + 1))}>Next →</button>
      </div>
      <div className="fs-float-body">
        <pre className="fs-steps-instruction">{step.instruction}</pre>
        {step.explanation && <details className="fs-steps-why"><summary>Why</summary><pre>{step.explanation}</pre></details>}
      </div>
    </div>
  );
};

export default FloatingSteps;
