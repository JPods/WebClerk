import { useRef, useState, useEffect } from "react";

type DragOptions = {
  initial: { x: number; y: number };
  onMove?: (x: number, y: number) => void;
};

export function useDraggable({ initial, onMove }: DragOptions) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState<{ x: number; y: number }>(initial);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    setOffset(initial);
  }, [initial.x, initial.y]);

  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      if (!dragging) return;
      setOffset((prev) => {
        const next = { x: prev.x + e.movementX, y: prev.y + e.movementY };
        onMove?.(next.x, next.y);
        return next;
      });
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
    onPointerDown: () => setDragging(true),
    style: { cursor: dragging ? "grabbing" : "grab" },
  };

  const dragStyle = {
    transform: `translate(${offset.x}px, ${offset.y}px)`,
  } as const;

  return { handleProps, dragStyle, offset, setOffset };
}