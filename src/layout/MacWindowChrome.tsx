import { ReactNode } from "react";
import { useAppSelector } from "../store/hooks";
import { useWindowManager } from "../context/WindowManagerContext";
import { useDraggable } from "../hooks/useDraggable";

type Props = {
  path: string;
  title: string;
  children: ReactNode;
  onActivate?: () => void;
  x: number;
  y: number;
  maximized?: boolean;
  isActive?: boolean;
};

export default function MacWindowChrome({ path, title, children, onActivate, x, y, maximized = false, isActive = false }: Props) {
  const { minimizeWindow, closeWindow, activateWindow, updateWindowPosition, maximizeWindow } = useWindowManager();
  const isApiLoading = useAppSelector((state) => state.loading.isApiLoading);
  const draggable = maximized
    ? null
    : useDraggable({
        initial: { x, y },
        onMove: (nx, ny) => updateWindowPosition(path, nx, ny),
      });

  const transitionClass = maximized || draggable?.dragging
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
    : draggable?.dragStyle;

  return (
    <div
      className={`absolute flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white text-slate-900 shadow-xl backdrop-blur-sm ${transitionClass} will-change-transform`}
      style={baseStyle}
      onMouseDown={() => {
        activateWindow(path);
        onActivate?.();
      }}
    >
      <div
        className={`flex items-center gap-3 border-b border-slate-200 bg-slate-100 px-4 py-2 text-sm text-slate-900 ${maximized ? "cursor-default" : ""}`}
        {...(draggable ? draggable.handleProps : {})}
      >
        <div className="flex items-center gap-2">
          <button
            className="h-3.5 w-3.5 rounded-full bg-rose-500 hover:bg-rose-400"
            aria-label="Close"
            onClick={(e) => {
              e.stopPropagation();
              closeWindow(path);
            }}
          />
          <button
            className="h-3.5 w-3.5 rounded-full bg-amber-400 hover:bg-amber-300"
            aria-label="Minimize"
            onClick={(e) => {
              e.stopPropagation();
              minimizeWindow(path, true);
            }}
          />
          <button
            className="h-3.5 w-3.5 rounded-full bg-emerald-400 hover:bg-emerald-300"
            aria-label="Maximize"
            onClick={(e) => {
              e.stopPropagation();
              maximizeWindow(path, !maximized);
            }}
          />
        </div>
        <span className="truncate text-xs font-semibold text-slate-700">{title}</span>
      </div>
      <div className="relative flex-1 overflow-auto bg-white p-4 text-slate-900">
        {children}
        {showSpinner && (
          <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center bg-white/60">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-400 border-t-transparent" aria-label="Loading" />
          </div>
        )}
      </div>
    </div>
  );
}