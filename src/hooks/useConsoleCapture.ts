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
  source?: string
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

  const addError = useCallback((error: Omit<CapturedError, "id" | "timestamp">) => {
    setErrors((prev) => {
      const next: CapturedError = {
        ...error,
        id: makeId(),
        timestamp: new Date(),
      };
      const updated = [next, ...prev];
      return updated.slice(0, MAX_ERRORS);
    });
  }, []);

  const clearErrors = useCallback(() => setErrors([]), []);

  const clearError = useCallback((id: string) => {
    setErrors((prev) => prev.filter((e) => e.id !== id));
  }, []);

  useEffect(() => {
    // ── Intercept console.error ────────────────────────────────
    originalConsoleError.current = console.error;

    console.error = (...args: unknown[]) => {
      // Still call the original so DevTools F12 works
      originalConsoleError.current?.apply(console, args);

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
    };

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
      // Restore
      if (originalConsoleError.current) {
        console.error = originalConsoleError.current;
      }
      window.removeEventListener("error", handleWindowError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, [addError]);

  return { errors, clearErrors, clearError };
}

export default useConsoleCapture;
