/**
 * IssueReporter.tsx — Unified issue reporter (replaces UserIssueReporter + DevIssueReporter).
 *
 * One floating button, one modal, one Action record. Users and developers
 * use the same form. Bug-specific fields (steps to reproduce, expected/actual)
 * show when category is Bug/Error. Console errors auto-attach when present.
 * Screenshot attach always available.
 *
 * Each submission creates an Action record with project_name "Issues".
 *
 * Usage in Router.tsx:
 *   <IssueReporter />
 */
import React, { useCallback, useRef, useState } from "react";
import {
  MessageCircleWarning,
  X,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  Camera,
  Terminal,
  Trash2,
} from "lucide-react";
import {
  ISSUE_CATEGORIES,
  PRIORITY_OPTIONS,
  type IssueCategory,
  type IssuePriority,
} from "../apps/support/services/issueApi";
import { useConsoleCapture } from "../hooks/useConsoleCapture";
import { saveRecord } from "@/api/wcapi";

export function IssueReporter() {
  const [isOpen, setIsOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Console capture
  const { errors: capturedErrors, clearErrors } = useConsoleCapture();

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<IssueCategory>("bug");
  const [priority, setPriority] = useState<IssuePriority>(2);
  const [component, setComponent] = useState("");
  const [steps, setSteps] = useState("");
  const [expected, setExpected] = useState("");
  const [actual, setActual] = useState("");
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [includeErrors, setIncludeErrors] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isBug = category === "bug";

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setCategory("bug");
    setPriority(2);
    setComponent("");
    setSteps("");
    setExpected("");
    setActual("");
    setScreenshot(null);
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

  const handleScreenshot = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setError("Screenshot must be under 2 MB");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setScreenshot(reader.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) { setError("Title is required"); return; }
      if (!description.trim()) { setError("Description is required"); return; }

      setSubmitting(true);
      setError(null);

      try {
        const consoleErrors =
          includeErrors && capturedErrors.length > 0
            ? capturedErrors.map((err) => `[${err.type}] ${err.message}${err.stack ? "\n" + err.stack : ""}`)
            : [];

        const descParts = [
          description.trim(),
          steps.trim() ? `\n**Steps to Reproduce:**\n${steps.trim()}` : "",
          expected.trim() ? `\n**Expected:** ${expected.trim()}` : "",
          actual.trim() ? `\n**Actual:** ${actual.trim()}` : "",
        ].filter(Boolean).join("\n");

        const actionPayload: Record<string, unknown> = {
          action: { en: title.trim() },
          description: { en: descParts },
          project_name: "Issues",
          kanban_column: "Backlog",
          priority,
          status: "Open",
          dt_start: Date.now(),
          refs: {
            tags: [category, ...(component.trim() ? [component.trim()] : [])],
            keywords: ["issue", category],
          },
          metadata: {
            issue_type: category,
            category,
            component: component.trim() || "",
            context: {
              page_url: window.location.href,
              screen_size: `${window.innerWidth}x${window.innerHeight}`,
              user_agent: navigator.userAgent,
              environment: {
                app: "WebClerk",
                mode: import.meta.env.MODE,
                api_url: import.meta.env.VITE_API_URL ?? "localhost:8000",
              },
              console_errors: consoleErrors,
              submitted_at: new Date().toISOString(),
            },
            ...(screenshot ? { screenshot } : {}),
          },
        };

        await saveRecord("action", actionPayload);

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
    [title, description, category, priority, component, steps, expected,
     actual, screenshot, includeErrors, capturedErrors, resetForm]
  );

  /* ---- Trigger button ---- */
  const trigger = (
    <button
      onClick={handleOpen}
      className="fixed bottom-20 right-6 z-[9998] flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg transition hover:bg-indigo-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-indigo-400"
      title="Report an issue"
      aria-label="Report an issue"
    >
      <MessageCircleWarning size={22} />
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
          className="relative w-[520px] max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-slate-900 dark:border dark:border-slate-700"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <MessageCircleWarning size={18} className="text-indigo-600" />
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Report an Issue
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
                Issue Submitted
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Action created in the Issues backlog.
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
                  placeholder="Brief summary of the issue"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  maxLength={200}
                  autoFocus
                />
              </div>

              {/* Category + Priority + Component row */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Category
                  </label>
                  <div className="relative">
                    <select data-wc="select"
                      value={category}
                      onChange={(e) => setCategory(e.target.value as IssueCategory)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-2 py-2 pr-7 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {ISSUE_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                    <ChevronDown size={12} className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-400" />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Priority
                  </label>
                  <div className="relative">
                    <select data-wc="select"
                      value={priority}
                      onChange={(e) => setPriority(Number(e.target.value) as IssuePriority)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-2 py-2 pr-7 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {PRIORITY_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                    <ChevronDown size={12} className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-slate-400" />
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
                    className="w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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
                  placeholder="What happened? What were you trying to do?"
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>

              {/* Bug-specific fields — show when category is bug */}
              {isBug && (
                <>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                      Steps to Reproduce
                    </label>
                    <textarea
                      value={steps}
                      onChange={(e) => setSteps(e.target.value)}
                      placeholder={"1. Go to\u2026\n2. Click\u2026\n3. Observe\u2026"}
                      rows={3}
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    />
                  </div>

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
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* Screenshot */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  <Camera size={14} />
                  {screenshot ? "Replace Screenshot" : "Attach Screenshot"}
                </button>
                {screenshot && (
                  <span className="text-xs text-green-600 dark:text-green-400">attached</span>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleScreenshot}
                  className="hidden"
                />
              </div>

              {/* Console errors — show when any are captured */}
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
                          className="h-3 w-3 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
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
                      <p className="text-[11px] text-slate-400">+{capturedErrors.length - 5} more</p>
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
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  {submitting ? "Submitting\u2026" : "Submit Issue"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  );
}
