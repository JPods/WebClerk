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
      }

      window.removeEventListener("error", handleWindowError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, [addError]);

  return { errors, clearErrors, clearError };
}

export default useConsoleCapture;
