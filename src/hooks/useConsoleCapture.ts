/**
 * useConsoleCapture.ts — Captures browser console errors and unhandled
 * exceptions for the AI debugger.
 *
 * Usage:
 *   const { errors, clearErrors, clearError } = useConsoleCapture();
 *
 * Captured errors appear in the AI widget when debugger mode is active,
 * letting the user send them to DeepSeek with one click.
 */
import { useEffect, useRef, useState, useCallback } from "react";

export interface CapturedError {
  id: string;
  timestamp: Date;
  message: string;
  stack?: string;
  source?: string;
  /** 'console' | 'window' | 'unhandledrejection' */
  type: "console" | "window" | "unhandledrejection";
  /** Raw text ready to paste into debugger */
  raw: string;
}

const MAX_ERRORS = 50;

/**
 * Generates a compact timestamp-based ID.
 */
function makeId(): string {
  return `err_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * Formats a captured error into a string suitable for the AI debugger.
 */
function formatError(
  type: CapturedError["type"],
  message: string,
  stack?: string,
  source?: string,
): string {
  const parts: string[] = [];
  parts.push(`[${type.toUpperCase()}] ${message}`);
  if (source) parts.push(`Source: ${source}`);
  if (stack) parts.push(`Stack:\n${stack}`);
  return parts.join("\n");
}

export function useConsoleCapture() {
  const [errors, setErrors] = useState<CapturedError[]>([]);
  const originalConsoleError = useRef<typeof console.error | null>(null);
  const handlingConsoleRef = useRef(false);

  const addError = useCallback(
    (error: Omit<CapturedError, "id" | "timestamp">) => {
      setErrors((prev) => {
        const next: CapturedError = {
          ...error,
          id: makeId(),
          timestamp: new Date(),
        };
        const updated = [next, ...prev];
        return updated.slice(0, MAX_ERRORS);
      });
    },
    [],
  );

  const clearErrors = useCallback(() => setErrors([]), []);

  const clearError = useCallback((id: string) => {
    setErrors((prev) => prev.filter((e) => e.id !== id));
  }, []);

  useEffect(() => {
<<<<<<< HEAD
    // Install a single global console.error wrapper and keep a list
    // of subscriber callbacks (one per hook instance). This prevents
    // multiple mounts from repeatedly wrapping console.error and
    // causing infinite recursion.
    const g = console as any;

    g.__consoleCaptureSubscribers = g.__consoleCaptureSubscribers || [];

    // Register this hook's addError so the global wrapper can notify it.
    g.__consoleCaptureSubscribers.push(addError);

    // If wrapper isn't installed yet, capture original and install.
    if (!g.__consoleCaptureWrapperInstalled) {
      originalConsoleError.current = console.error;

      const wrapper = (...args: unknown[]) => {
        // Call the original so DevTools still shows the error.
        try {
          originalConsoleError.current?.apply(console, args);
        } catch (e) {
          // If calling original fails, still continue to notify subscribers.
        }

        const message = args
          .map((a) => {
            if (a instanceof Error) return a.message;
            if (typeof a === "string") return a;
            try {
              return JSON.stringify(a, null, 2);
            } catch {
              return String(a);
            }
          })
          .join(" ");

        const errorArg = args.find((a) => a instanceof Error) as
          | Error
          | undefined;

        const payload = {
          type: "console",
          message,
          stack: errorArg?.stack,
          raw: formatError("console", message, errorArg?.stack),
        };

        // Notify all subscribers (each useConsoleCapture instance)
        const subs: Array<
          (err: Omit<CapturedError, "id" | "timestamp">) => void
        > = g.__consoleCaptureSubscribers || [];
        for (const s of subs) {
          try {
            s(payload);
          } catch (e) {
            // Subscriber errors should not break the loop
          }
        }
      };

      g.__consoleCaptureWrapperInstalled = true;
      g.__originalConsoleError = originalConsoleError.current;
      console.error = wrapper;
    }
=======
    // ── Intercept console.error ────────────────────────────────
    const globalConsole = console as any;
    // Preserve a single non-wrapper original console.error across multiple mounts
    const baseOriginal = globalConsole.__originalConsoleError || console.error;
    globalConsole.__originalConsoleError = baseOriginal;
    globalConsole.__consoleCaptureCount = (globalConsole.__consoleCaptureCount || 0) + 1;

    originalConsoleError.current = baseOriginal;

    const wrapper = (...args: unknown[]) => {
      // Prevent re-entrancy: if a console.error occurs while handling a previous
      // console.error (for example React warnings during setState), skip adding
      // a new captured error to avoid infinite recursion.
      if (handlingConsoleRef.current) {
        const globalConsole = console as any;
        const base = globalConsole.__originalConsoleError;
        const fallback = globalConsole.__originalConsoleLog || console.log;
        try {
          if (base && !base.__isConsoleCaptureWrapper) {
            Function.prototype.apply.call(base, console, args);
          } else {
            Function.prototype.apply.call(fallback, console, args);
          }
        } catch {
          // swallow
        }
        return;
      }

      handlingConsoleRef.current = true;
      try {
        const globalConsole = console as any;
        const base = globalConsole.__originalConsoleError;
        const fallback = globalConsole.__originalConsoleLog || console.log;

        // Call the saved original if it's not another capture wrapper; otherwise
        // call fallback to avoid chaining into another wrapper that may call us.
        try {
          if (base && !base.__isConsoleCaptureWrapper) {
            Function.prototype.apply.call(base, console, args);
          } else {
            Function.prototype.apply.call(fallback, console, args);
          }
        } catch {
          // ignore
        }

        const message = args
          .map((a) => {
            if (a instanceof Error) return a.message;
            if (typeof a === "string") return a;
            try {
              return JSON.stringify(a, null, 2);
            } catch {
              return String(a);
            }
          })
          .join(" ");

        const errorArg = args.find((a) => a instanceof Error) as Error | undefined;

        addError({
          type: "console",
          message,
          stack: errorArg?.stack,
          raw: formatError("console", message, errorArg?.stack),
        });
      } finally {
        handlingConsoleRef.current = false;
      }
    };
>>>>>>> 9af940e04dae78d3fb2a25bff5971ff95a6a1218

    // Mark wrapper to detect it later and store fallback log
    (wrapper as any).__isConsoleCaptureWrapper = true;
    console.error = wrapper;
    const globalConsoleAny = console as any;
    globalConsoleAny.__originalConsoleLog = globalConsoleAny.__originalConsoleLog || console.log;

    // ── Intercept window.onerror ───────────────────────────────
    const handleWindowError = (event: ErrorEvent) => {
      const source = event.filename
        ? `${event.filename}:${event.lineno}:${event.colno}`
        : undefined;

      addError({
        type: "window",
        message: event.message,
        stack: event.error?.stack,
        source,
        raw: formatError("window", event.message, event.error?.stack, source),
      });
    };

    // ── Intercept unhandled promise rejections ─────────────────
    const handleRejection = (event: PromiseRejectionEvent) => {
      const message =
        event.reason instanceof Error
          ? event.reason.message
          : String(event.reason);
      const stack =
        event.reason instanceof Error ? event.reason.stack : undefined;

      addError({
        type: "unhandledrejection",
        message: `Unhandled Promise Rejection: ${message}`,
        stack,
        raw: formatError("unhandledrejection", message, stack),
      });
    };

    window.addEventListener("error", handleWindowError);
    window.addEventListener("unhandledrejection", handleRejection);

    return () => {
<<<<<<< HEAD
      // Unregister subscriber
      const subs: Array<any> =
        (console as any).__consoleCaptureSubscribers || [];
      const idx = subs.indexOf(addError as any);
      if (idx !== -1) subs.splice(idx, 1);

      // If no subscribers left, restore original console.error
      if (!subs.length) {
        const g2 = console as any;
        if (g2.__originalConsoleError) {
          console.error = g2.__originalConsoleError;
        }
        delete g2.__consoleCaptureSubscribers;
        delete g2.__consoleCaptureWrapperInstalled;
        delete g2.__originalConsoleError;
=======
      const globalConsole = console as any;
      globalConsole.__consoleCaptureCount = (globalConsole.__consoleCaptureCount || 1) - 1;
      // Only restore the original console.error when the last capture hook unmounts
      if (globalConsole.__consoleCaptureCount <= 0) {
        if (originalConsoleError.current) {
          console.error = originalConsoleError.current;
        }
        delete globalConsole.__originalConsoleError;
        delete globalConsole.__consoleCaptureCount;
>>>>>>> 9af940e04dae78d3fb2a25bff5971ff95a6a1218
      }

      window.removeEventListener("error", handleWindowError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, [addError]);

  return { errors, clearErrors, clearError };
}

export default useConsoleCapture;
