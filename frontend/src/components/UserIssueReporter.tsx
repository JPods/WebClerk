/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * UserIssueReporter.tsx — Floating help-desk button for end users.
 *
 * Opens a simple modal where users can report issues, request features,
 * or ask questions. Each submission creates an Action record with
 * project_name "User Support" so it appears in the Actions Kanban.
 *
 * Auto-captures: current page URL, browser info, screen size.
 *
 * Usage in App.tsx:
 *   <UserIssueReporter />
 */
import React, { useCallback, useRef, useState } from "react";
import {
  HelpCircle,
  X,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  Camera,
} from "lucide-react";
import {
  submitUserIssue,
  ISSUE_CATEGORIES,
  PRIORITY_OPTIONS,
  type IssueCategory,
  type IssuePriority,
} from "../apps/support/services/issueApi";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function UserIssueReporter() {
  const [isOpen, setIsOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<IssueCategory>("bug");
  const [priority, setPriority] = useState<IssuePriority>(2);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setCategory("bug");
    setPriority(2);
    setScreenshot(null);
    setError(null);
    setSubmitted(false);
  }, []);

  const handleOpen = useCallback(() => {
    resetForm();
    setIsOpen(true);
  }, [resetForm]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    // Delay reset so closing animation can play
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
      if (!title.trim()) {
        setError("Please enter a title");
        return;
      }
      if (!description.trim()) {
        setError("Please describe the issue");
        return;
      }

      setSubmitting(true);
      setError(null);

      try {
        await submitUserIssue({
          title: title.trim(),
          description: description.trim(),
          category,
          priority,
          pageUrl: window.location.href,
          userAgent: navigator.userAgent,
          screenSize: `${window.innerWidth}x${window.innerHeight}`,
          ...(screenshot ? { screenshot } : {}),
        });
        setSubmitted(true);
        // Auto-close after 2s
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
    [title, description, category, priority, screenshot, resetForm]
  );

  /* ---- Render ---- */

  // Floating trigger button
  const trigger = (
    <button
      onClick={handleOpen}
      className="fixed bottom-20 right-6 z-[9998] flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg transition hover:bg-indigo-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-indigo-400"
      title="Report an issue"
      aria-label="Report an issue"
    >
      <HelpCircle size={22} />
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
          className="relative w-[480px] max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-slate-900 dark:border dark:border-slate-700"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <HelpCircle size={18} className="text-indigo-600" />
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

          {/* Success state */}
          {submitted ? (
            <div className="flex flex-col items-center gap-3 px-5 py-10">
              <CheckCircle2 size={48} className="text-green-500" />
              <p className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                Issue Submitted
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Thank you! Your report has been logged and assigned to the backlog.
              </p>
            </div>
          ) : (
            /* Form */
            <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
              {/* Error banner */}
              {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  <AlertTriangle size={14} />
                  {error}
                </div>
              )}

              {/* Title */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
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

              {/* Category + Priority row */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Category
                  </label>
                  <div className="relative">
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value as IssueCategory)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-8 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {ISSUE_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      size={14}
                      className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Priority
                  </label>
                  <div className="relative">
                    <select
                      value={priority}
                      onChange={(e) => setPriority(Number(e.target.value) as IssuePriority)}
                      className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-8 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {PRIORITY_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      size={14}
                      className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What happened? What were you trying to do?"
                  rows={4}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>

              {/* Screenshot */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Screenshot <span className="text-xs text-slate-400">(optional, max 2 MB)</span>
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  >
                    <Camera size={14} />
                    {screenshot ? "Replace" : "Attach"}
                  </button>
                  {screenshot && (
                    <span className="text-xs text-green-600 dark:text-green-400">
                      Screenshot attached
                    </span>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleScreenshot}
                    className="hidden"
                  />
                </div>
              </div>

              {/* Auto-captured info */}
              <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800/50 dark:text-slate-400">
                <p className="font-medium text-slate-600 dark:text-slate-300">Auto-captured:</p>
                <p className="mt-0.5 truncate">Page: {window.location.pathname}</p>
                <p className="truncate">
                  Screen: {window.innerWidth}x{window.innerHeight}
                </p>
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
                  {submitting ? "Submitting…" : "Submit Issue"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  );
}
