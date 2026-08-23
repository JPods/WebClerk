/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * DevIssueReporter.tsx — Developer bug report modal.
 *
 * Richer than the user reporter: captures console errors, lets devs
 * specify component, severity, steps to reproduce, expected vs actual.
 * Each submission creates an Action record with project_name "Dev Issues".
 *
 * Integrates with useConsoleCapture to auto-attach recent console errors.
 *
 * Usage in App.tsx:
 *   <DevIssueReporter />
 */
import React, { useCallback, useState } from "react";
import {
  Bug,
  X,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  Terminal,
  Trash2,
} from "lucide-react";
import {
  submitDevIssue,
  ISSUE_CATEGORIES,
  SEVERITY_OPTIONS,
  type IssueCategory,
  type DevSeverity,
} from "../apps/support/services/issueApi";
import { useConsoleCapture } from "../hooks/useConsoleCapture";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DevIssueReporter() {
  const [isOpen, setIsOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Console capture
  const { errors: capturedErrors, clearErrors } = useConsoleCapture();

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<DevSeverity>("minor");
  const [category, setCategory] = useState<IssueCategory>("bug");
  const [component, setComponent] = useState("");
  const [steps, setSteps] = useState("");
  const [expected, setExpected] = useState("");
  const [actual, setActual] = useState("");
  const [includeErrors, setIncludeErrors] = useState(true);

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setSeverity("minor");
    setCategory("bug");
    setComponent("");
    setSteps("");
    setExpected("");
    setActual("");
    setIncludeErrors(true);
    setError(null);
    setSubmitted(false);
  }, []);

  const handleOpen = useCallback(() => {
    resetForm();
    setIsOpen(true);
  }, [resetForm]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setTimeout(resetForm, 200);
  }, [resetForm]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) {
        setError("Title is required");
        return;
      }
      if (!description.trim()) {
        setError("Description is required");
        return;
      }

      setSubmitting(true);
      setError(null);

      try {
        const consoleErrors =
          includeErrors && capturedErrors.length > 0
            ? capturedErrors.map((err) => `[${err.type}] ${err.message}${err.stack ? "\n" + err.stack : ""}`)
            : [];

        await submitDevIssue({
          title: title.trim(),
          description: description.trim(),
          severity,
          category,
          component: component.trim() || undefined,
          stepsToReproduce: steps.trim() || undefined,
          expectedBehavior: expected.trim() || undefined,
          actualBehavior: actual.trim() || undefined,
          consoleErrors,
          pageUrl: window.location.href,
          environment: {
            app: "React2025",
            mode: import.meta.env.MODE,
            api_url: import.meta.env.VITE_API_URL ?? "localhost:8000",
            browser: navigator.userAgent.split(" ").pop() ?? "",
            screen: `${window.innerWidth}x${window.innerHeight}`,
          },
        });

        setSubmitted(true);
        setTimeout(() => {
          setIsOpen(false);
          setTimeout(resetForm, 200);
        }, 2000);
      } catch (err: any) {
        setError(err?.message || "Failed to submit. Please try again.");
      } finally {
        setSubmitting(false);
      }
    },
    [
      title,
      description,
      severity,
      category,
      component,
      steps,
      expected,
      actual,
      includeErrors,
      capturedErrors,
      resetForm,
    ]
  );

  /* ---- Render ---- */

  // Floating trigger — positioned above the user reporter
  const trigger = (
    <button
      onClick={handleOpen}
      className="fixed bottom-[136px] right-6 z-[9998] flex h-10 w-10 items-center justify-center rounded-full bg-orange-600 text-white shadow-lg transition hover:bg-orange-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-orange-400"
      title="Developer Bug Report"
      aria-label="Developer Bug Report"
    >
      <Bug size={18} />
      {/* Badge for captured error count */}
      {capturedErrors.length > 0 && (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
          {capturedErrors.length > 9 ? "9+" : capturedErrors.length}
        </span>
      )}
    </button>
  );

  if (!isOpen) return trigger;

  return (
    <>
      {trigger}

      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40"
        onClick={handleClose}
      >
        {/* Modal */}
        <div
          className="relative w-[560px] max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-slate-900 dark:border dark:border-slate-700"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <Bug size={18} className="text-orange-600" />
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Developer Bug Report
              </h2>
            </div>
            <button
              onClick={handleClose}
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
            >
              <X size={18} />
            </button>
          </div>

          {/* Success */}
          {submitted ? (
            <div className="flex flex-col items-center gap-3 px-5 py-10">
              <CheckCircle2 size={48} className="text-green-500" />
              <p className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                Bug Report Filed
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Action created in Dev Issues backlog.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3 px-5 py-4">
              {/* Error banner */}
              {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  <AlertTriangle size={14} />
                  {error}
                </div>
              )}

              {/* Title */}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Concise bug summary"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  maxLength={200}
                  autoFocus
                />
              </div>

              {/* Severity + Category + Component row */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Severity
                  </label>
                  <div className="relative">
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value as DevSeverity)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-2 py-1.5 pr-7 text-sm text-slate-800 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {SEVERITY_OPTIONS.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      size={12}
                      className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Category
                  </label>
                  <div className="relative">
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value as IssueCategory)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-2 py-1.5 pr-7 text-sm text-slate-800 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {ISSUE_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      size={12}
                      className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Component
                  </label>
                  <input
                    type="text"
                    value={component}
                    onChange={(e) => setComponent(e.target.value)}
                    placeholder="e.g. OrderDetail"
                    className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What's broken? Include context."
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>

              {/* Steps to Reproduce */}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Steps to Reproduce
                </label>
                <textarea
                  value={steps}
                  onChange={(e) => setSteps(e.target.value)}
                  placeholder="1. Go to…&#10;2. Click…&#10;3. Observe…"
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>

              {/* Expected / Actual row */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Expected Behavior
                  </label>
                  <textarea
                    value={expected}
                    onChange={(e) => setExpected(e.target.value)}
                    placeholder="What should happen"
                    rows={2}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Actual Behavior
                  </label>
                  <textarea
                    value={actual}
                    onChange={(e) => setActual(e.target.value)}
                    placeholder="What actually happens"
                    rows={2}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  />
                </div>
              </div>

              {/* Console errors panel */}
              {capturedErrors.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
                  <div className="flex items-center justify-between px-3 py-2">
                    <div className="flex items-center gap-1.5">
                      <Terminal size={14} className="text-red-500" />
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        Console Errors ({capturedErrors.length})
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                        <input
                          type="checkbox"
                          checked={includeErrors}
                          onChange={(e) => setIncludeErrors(e.target.checked)}
                          className="h-3 w-3 rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                        />
                        Attach
                      </label>
                      <button
                        type="button"
                        onClick={clearErrors}
                        className="text-slate-400 hover:text-red-500"
                        title="Clear captured errors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                  <div className="max-h-24 overflow-y-auto border-t border-slate-200 px-3 py-1.5 dark:border-slate-700">
                    {capturedErrors.slice(0, 5).map((err) => (
                      <p
                        key={err.id}
                        className="truncate text-[11px] font-mono text-red-600 dark:text-red-400"
                        title={err.message}
                      >
                        [{err.type}] {err.message}
                      </p>
                    ))}
                    {capturedErrors.length > 5 && (
                      <p className="text-[11px] text-slate-400">
                        +{capturedErrors.length - 5} more
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Auto-captured context */}
              <div className="rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-slate-500 dark:bg-slate-800/50 dark:text-slate-400">
                <span className="font-medium text-slate-600 dark:text-slate-300">Auto-captured: </span>
                {window.location.pathname} &middot; {import.meta.env.MODE} &middot;{" "}
                {window.innerWidth}x{window.innerHeight}
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-700">
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-lg border border-slate-300 px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 rounded-lg bg-orange-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50"
                >
                  {submitting ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  {submitting ? "Filing…" : "File Bug Report"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  );
}
