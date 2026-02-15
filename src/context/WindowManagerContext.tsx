import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

export type WindowEntry = {
  path: string;
  title: string;
  minimized: boolean;
  maximized: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  openedAt: number;
};

export type EnsureWindowOptions = {
  maximized?: boolean;
  width?: number;
  height?: number;
  x?: number;
  y?: number;
};

type WindowManagerCtx = {
  windows: WindowEntry[];
  activePath: string | null;
  ensureWindow: (path: string, title?: string, options?: EnsureWindowOptions) => void;
  closeWindow: (path: string) => void;
  minimizeWindow: (path: string, minimized?: boolean) => void;
  activateWindow: (path: string) => void;
  updateWindowPosition: (path: string, x: number, y: number) => void;
  maximizeWindow: (path: string, maximized?: boolean) => void;
  updateWindowSize: (path: string, width: number, height: number) => void;
  setNavigate: (nav: (path: string) => void) => void;
  /** Base pathname that ensureWindow just navigated to — AppLayout checks this to avoid creating a duplicate auto-window. */
  skipAutoCreateForPathRef: React.MutableRefObject<string | null>;
};

const WindowManagerContext = createContext<WindowManagerCtx | null>(null);

export const WindowManagerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [windows, setWindows] = useState<WindowEntry[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const openedCounter = useRef(0);
  const navigateRef = useRef<((path: string) => void) | null>(null);
  const skipAutoCreateForPathRef = useRef<string | null>(null);
  
  const setNavigate = useCallback((nav: (path: string) => void) => {
    navigateRef.current = nav;
  }, []);

  const ensureWindow = useCallback((path: string, title = path, options?: EnsureWindowOptions) => {
    // Record the base pathname so AppLayout's useEffect skips duplicate auto-creation
    skipAutoCreateForPathRef.current = path.split('?')[0];
    if (navigateRef.current) {
      navigateRef.current(path);
    }
    setWindows((prev) => {
      const existing = prev.find((w) => w.path === path);
      if (existing) {
        const needsUpdate = existing.minimized || existing.title !== title;
        if (!needsUpdate) {
          setActivePath(path);
          return prev;
        }
        const updated = prev.map((w) =>
          w.path === path
            ? {
                ...w,
                minimized: false,
                title,
                maximized: options?.maximized ?? w.maximized,
                width: options?.width ?? w.width,
                height: options?.height ?? w.height,
                x: options?.x ?? w.x,
                y: options?.y ?? w.y,
              }
            : w
        );
        setActivePath(path);
        return updated;
      }
      const stagger = 28 * prev.length;
      const maximized = options?.maximized ?? true;
      setActivePath(path);
      return [
        ...prev,
        {
          path,
          title,
          minimized: false,
          maximized,
          x: options?.x ?? stagger,
          y: options?.y ?? stagger,
          width: options?.width ?? 980,
          height: options?.height ?? 640,
          openedAt: openedCounter.current++,
        },
      ];
    });
  }, []);

  const closeWindow = useCallback((path: string) => {
    setWindows((prev) => {
      const next = prev.filter((w) => w.path !== path);
      const fallback = next.length ? next[next.length - 1].path : null;
      setActivePath(fallback);
      return next;
    });
  }, []);

  const minimizeWindow = useCallback(
    (path: string, minimized = true) => {
      setWindows((prev) => {
        const updated = prev.map((w) => (w.path === path ? { ...w, minimized, maximized: minimized ? false : w.maximized } : w));
        if (minimized && activePath === path) {
          const fallback = updated.filter((w) => !w.minimized).slice(-1)[0]?.path || null;
          setActivePath(fallback);
        }
        return updated;
      });
    },
    [activePath]
  );

  const activateWindow = useCallback((path: string) => {
    if (navigateRef.current) {
      navigateRef.current(path);
    }
    setWindows((prev) => {
      const target = prev.find((w) => w.path === path);
      if (!target) return prev;
      const rest = prev.filter((w) => w.path !== path);
      setActivePath(path);
      return [...rest, { ...target, minimized: false }];
    });
  }, []);

  const updateWindowPosition = useCallback((path: string, x: number, y: number) => {
    setWindows((prev) => prev.map((w) => (w.path === path ? { ...w, x, y } : w)));
  }, []);

  const maximizeWindow = useCallback((path: string, maximized = true) => {
    setWindows((prev) => prev.map((w) => (w.path === path ? { ...w, maximized, minimized: false } : w)));
  }, []);

  const updateWindowSize = useCallback((path: string, width: number, height: number) => {
    setWindows((prev) => prev.map((w) => (w.path === path ? { ...w, width, height } : w)));
  }, []);

  const api = useMemo<WindowManagerCtx>(
    () => ({ windows, activePath, ensureWindow, closeWindow, minimizeWindow, activateWindow, updateWindowPosition, maximizeWindow, updateWindowSize, setNavigate, skipAutoCreateForPathRef }),
    [windows, activePath, ensureWindow, closeWindow, minimizeWindow, activateWindow, updateWindowPosition, maximizeWindow, updateWindowSize, setNavigate]
  );

  return <WindowManagerContext.Provider value={api}>{children}</WindowManagerContext.Provider>;
};

// Hook component to connect React Router's navigate to WindowManager
export const WindowManagerNavigationSync: React.FC = () => {
  const navigate = useNavigate();
  const { setNavigate } = useWindowManager();
  
  useEffect(() => {
    setNavigate(navigate);
  }, [navigate, setNavigate]);
  
  return null;
};

export const useWindowManager = () => {
  const ctx = useContext(WindowManagerContext);
  if (!ctx) throw new Error("useWindowManager must be used within WindowManagerProvider");
  return ctx;
};