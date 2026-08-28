/* LastChecked: 2026-08-16 | WhereUsed: Window frame for all content | Theme: --wc-* variables */
import { ReactNode } from "react";
import { useAppSelector } from "../store/hooks";
import { useWindowManager } from "../context/WindowManagerContext";
import { WindowPathProvider } from "../context/WindowPathContext";
import { useDraggable } from "../hooks/useDraggable";
import { useResizable } from "../hooks/useResizable";

type Props = {
  path: string;
  title: string;
  children: ReactNode;
  onActivate?: () => void;
  x: number;
  y: number;
  width?: number;
  height?: number;
  maximized?: boolean;
  isActive?: boolean;
};

export default function MacWindowChrome({ path, title, children, onActivate, x, y, width, height, maximized = false, isActive = false }: Props) {
  const { minimizeWindow, closeWindow, activateWindow, updateWindowPosition, maximizeWindow, updateWindowSize } = useWindowManager();
  const isApiLoading = useAppSelector((state) => state.loading.isApiLoading);
  const draggable = useDraggable({
    initial: { x, y },
    onMove: (nx, ny) => updateWindowPosition(path, nx, ny),
  });
  const resizable = useResizable({
    initial: { width: width ?? 980, height: height ?? 640 },
    minWidth: 520,
    minHeight: 360,
    onResize: (nw, nh) => updateWindowSize(path, nw, nh),
    disabled: maximized,
  });

  const transitionClass = maximized || draggable.dragging
    ? "transition-none"
    : "transition-transform duration-150";

  const showSpinner = isActive && isApiLoading;

  const baseStyle = maximized
    ? {
        position: "absolute" as const,
        inset: 0,
        width: "100%",
        height: "100%",
        transform: "none",
      }
    : {
        ...draggable.dragStyle,
        width: resizable.size.width,
        height: resizable.size.height,
      };

  return (
    <div
      data-wc="mac-window-chrome"
      className={`absolute flex flex-col overflow-hidden backdrop-blur-sm ${maximized ? "rounded-none border-0 shadow-none" : "rounded-2xl border shadow-xl"} ${transitionClass} will-change-transform`}
      style={{
        ...baseStyle,
        backgroundColor: 'var(--wc-window-bg)',
        borderColor: maximized ? undefined : 'var(--wc-window-border)',
        color: 'var(--wc-text)',
      }}
      onMouseDown={() => {
        activateWindow(path);
        onActivate?.();
      }}
    >
      <div className="relative flex-1 overflow-auto"
        style={{ backgroundColor: 'var(--wc-window-bg)', color: 'var(--wc-text)' }}>
        <WindowPathProvider value={path}>
        {children}
        </WindowPathProvider>
        {showSpinner && (
          <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center"
            style={{ backgroundColor: 'var(--wc-spinner-overlay)' }}>
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-t-transparent"
              style={{ borderColor: 'var(--wc-spinner-color)', borderTopColor: 'transparent' }}
              aria-label="Loading" />
          </div>
        )}
      </div>
      {!maximized && (
        <div
          className="absolute bottom-1 right-1 h-4 w-4 rounded-sm border border-transparent bg-transparent"
          data-stop-drag="true"
          {...resizable.handleProps}
        />
      )}
    </div>
  );
}
