/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useRef, useState } from "react";

type ResizeOptions = {
  initial: { width: number; height: number };
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
  onResize?: (width: number, height: number) => void;
  disabled?: boolean;
};

export function useResizable({
  initial,
  minWidth = 420,
  minHeight = 260,
  maxWidth,
  maxHeight,
  onResize,
  disabled = false,
}: ResizeOptions) {
  const [size, setSize] = useState<{ width: number; height: number }>(initial);
  const [resizing, setResizing] = useState(false);
  const startRef = useRef<{
    startX: number;
    startY: number;
    originWidth: number;
    originHeight: number;
  } | null>(null);

  useEffect(() => {
    setSize(initial);
  }, [initial.width, initial.height]);

  useEffect(() => {
    if (disabled) return;

    const handlePointerMove = (e: PointerEvent) => {
      if (!resizing || !startRef.current) return;
      const { startX, startY, originWidth, originHeight } = startRef.current;
      let nextWidth = originWidth + (e.clientX - startX);
      let nextHeight = originHeight + (e.clientY - startY);

      nextWidth = Math.max(minWidth, maxWidth ? Math.min(maxWidth, nextWidth) : nextWidth);
      nextHeight = Math.max(minHeight, maxHeight ? Math.min(maxHeight, nextHeight) : nextHeight);

      setSize({ width: nextWidth, height: nextHeight });
      onResize?.(nextWidth, nextHeight);
    };

    const handlePointerUp = () => setResizing(false);

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [disabled, resizing, minWidth, minHeight, maxWidth, maxHeight, onResize]);

  const handleProps = disabled
    ? {}
    : {
        onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => {
          if (e.button !== 0) return;
          startRef.current = {
            startX: e.clientX,
            startY: e.clientY,
            originWidth: size.width,
            originHeight: size.height,
          };
          e.currentTarget.setPointerCapture(e.pointerId);
          setResizing(true);
        },
        style: { cursor: "nwse-resize" },
      };

  return { size, handleProps, resizing };
}
