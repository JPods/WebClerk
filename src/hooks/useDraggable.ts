/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useRef, useState, useEffect } from "react";

type DragOptions = {
  initial: { x: number; y: number };
  onMove?: (x: number, y: number) => void;
};

export function useDraggable({ initial, onMove }: DragOptions) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState<{ x: number; y: number }>(initial);
  const [dragging, setDragging] = useState(false);
  const startRef = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);

  useEffect(() => {
    setOffset(initial);
  }, [initial.x, initial.y]);

  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      if (!dragging || !startRef.current) return;
      const { startX, startY, originX, originY } = startRef.current;
      const next = {
        x: originX + (e.clientX - startX),
        y: originY + (e.clientY - startY),
      };
      setOffset(next);
      onMove?.(next.x, next.y);
    };

    const handlePointerUp = () => setDragging(false);

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [dragging, onMove]);

  const handleProps = {
    ref,
    onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      const target = e.target as HTMLElement | null;
      if (target?.closest('[data-stop-drag="true"]')) return;
      startRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        originX: offset.x,
        originY: offset.y,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
      setDragging(true);
    },
    style: { cursor: dragging ? "grabbing" : "grab" },
  };

  const dragStyle = {
    transform: `translate(${offset.x}px, ${offset.y}px)`,
  } as const;

  return { handleProps, dragStyle, offset, setOffset, dragging };
}