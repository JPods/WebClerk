/**
 * FormCoachAlert — Displays form completeness issues before printing
 *
 * Shows a dismissible panel with color-coded issues:
 *   - Red:    Missing required fields (will not print correctly)
 *   - Orange: Incomplete data (prints but may look incomplete)
 *   - Blue:   Suggestions for better data quality
 *
 * Renders inline (typically below the toolbar) and can be dismissed.
 */
import React from 'react';
import { FaExclamationTriangle, FaExclamationCircle, FaInfoCircle, FaTimes, FaExternalLinkAlt } from 'react-icons/fa';
import type { CoachIssue, CoachSeverity } from '@/hooks/useFormCoach';

// ── Severity styling ───────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<CoachSeverity, {
  icon: React.ReactNode;
  textClass: string;
  bgClass: string;
  borderClass: string;
  label: string;
}> = {
  error: {
    icon: <FaExclamationCircle size={14} />,
    textClass: 'text-red-600 dark:text-red-400',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
    borderClass: 'border-red-200 dark:border-red-800',
    label: 'Missing',
  },
  warning: {
    icon: <FaExclamationTriangle size={14} />,
    textClass: 'text-orange-600 dark:text-orange-400',
    bgClass: 'bg-orange-50 dark:bg-orange-900/20',
    borderClass: 'border-orange-200 dark:border-orange-800',
    label: 'Incomplete',
  },
  info: {
    icon: <FaInfoCircle size={14} />,
    textClass: 'text-blue-600 dark:text-blue-400',
    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
    borderClass: 'border-blue-200 dark:border-blue-800',
    label: 'Suggestion',
  },
};

// ── Issue row ──────────────────────────────────────────────────────────

const IssueRow: React.FC<{ issue: CoachIssue }> = ({ issue }) => {
  const cfg = SEVERITY_CONFIG[issue.severity];
  return (
    <div className={`flex items-start gap-2 px-3 py-1.5 ${cfg.textClass}`}>
      <span className="mt-0.5 shrink-0">{cfg.icon}</span>
      <div className="flex-1 min-w-0">
        <span className="font-medium">{issue.field}</span>
        <span className="mx-1.5 text-gray-400">—</span>
        <span className="text-sm">{issue.message}</span>
      </div>
      {issue.section && (
        <span className="text-xs opacity-60 shrink-0">({issue.section})</span>
      )}
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────

interface FormCoachAlertProps {
  issues: CoachIssue[];
  onDismiss?: () => void;
  /** Compact mode (fewer visual elements) */
  compact?: boolean;
  /** Optional title override */
  title?: string;
  /** Source-file path relative to project root (e.g. "src/apps/…/OrderDetail.tsx") */
  formSourcePath?: string;
  className?: string;
}

/** Build a vscode:// URI that opens a file in VS Code */
const vscodeUri = (relativePath: string) => {
  return 'vscode://file/' + encodeURIComponent(relativePath);
};

const FormCoachAlert: React.FC<FormCoachAlertProps> = ({
  issues,
  onDismiss,
  compact = false,
  title,
  formSourcePath,
  className = '',
}) => {
  if (issues.length === 0) return null;

  const errorCount = issues.filter((i) => i.severity === 'error').length;
  const warningCount = issues.filter((i) => i.severity === 'warning').length;
  const infoCount = issues.filter((i) => i.severity === 'info').length;

  // Pick dominant severity for the outer border
  const dominant: CoachSeverity = errorCount > 0 ? 'error' : warningCount > 0 ? 'warning' : 'info';
  const borderCfg = SEVERITY_CONFIG[dominant];

  const heading =
    title ??
    (errorCount > 0
      ? 'Print Pre-Check — Issues Found'
      : 'Print Pre-Check — Review Recommended');

  return (
    <div
      className={`
        border rounded-lg overflow-hidden
        ${borderCfg.borderClass} ${borderCfg.bgClass}
        ${className}
      `}
      role="alert"
    >
      {/* Form source path + Open in VS Code */}
      {formSourcePath && !compact && (
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-200/50 dark:border-gray-700/50 bg-white/60 dark:bg-slate-800/40">
          <span className="text-xs font-mono text-gray-500 dark:text-gray-400 truncate">
            {formSourcePath}
          </span>
          <a
            href={vscodeUri(formSourcePath)}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded transition-colors"
            title={`Open ${formSourcePath} in VS Code`}
          >
            <FaExternalLinkAlt size={10} />
            Open in VS Code
          </a>
        </div>
      )}

      {/* Header bar */}
      <div className={`flex items-center justify-between px-3 py-2 ${borderCfg.textClass}`}>
        <div className="flex items-center gap-2">
          {borderCfg.icon}
          <span className="font-semibold text-sm">{heading}</span>
          {!compact && (
            <span className="text-xs opacity-70 ml-2">
              {[
                errorCount > 0 && `${errorCount} missing`,
                warningCount > 0 && `${warningCount} incomplete`,
                infoCount > 0 && `${infoCount} suggestion${infoCount > 1 ? 's' : ''}`,
              ]
                .filter(Boolean)
                .join(' · ')}
            </span>
          )}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            aria-label="Dismiss"
          >
            <FaTimes size={12} />
          </button>
        )}
      </div>

      {/* Issue list */}
      <div className="divide-y divide-gray-200/50 dark:divide-gray-700/50">
        {issues.map((issue) => (
          <IssueRow key={issue.key} issue={issue} />
        ))}
      </div>
    </div>
  );
};

export default FormCoachAlert;
