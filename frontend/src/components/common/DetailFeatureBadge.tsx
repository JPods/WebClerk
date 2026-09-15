/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * DetailFeatureBadge – dev-only checklist badge for detail pages.
 *
 * Shows which standard features each detail page has implemented.
 * Controlled by VITE_DEBUG_BADGES — same env-var as DevBadge.
 *
 * Usage:
 *   <DetailFeatureBadge features={{ autoSave: true, bgSaveChildren: true }} />
 */

export interface DetailFeatures {
  /** Contact/parent auto-save before child creation */
  autoSave?: boolean;
  /** Background save of related/child records */
  bgSaveChildren?: boolean;
  /** Print / PDF export wired */
  print?: boolean;
  /** Clone / duplicate record */
  clone?: boolean;
  /** Transaction flow (proposals → orders → invoices etc.) */
  transactions?: boolean;
}

interface DetailFeatureBadgeProps {
  features: DetailFeatures;
  /** Extra Tailwind classes for positioning */
  className?: string;
}

const LABELS: Record<keyof DetailFeatures, string> = {
  autoSave: 'Auto-Save',
  bgSaveChildren: 'BG Children',
  print: 'Print',
  clone: 'Clone',
  transactions: 'Txn Flow',
};

export function DetailFeatureBadge({
  features,
  className = '',
}: DetailFeatureBadgeProps) {
  if (import.meta.env.VITE_DEBUG_BADGES !== 'true') return null;

  const entries = Object.entries(LABELS) as [keyof DetailFeatures, string][];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono tracking-wide bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700 ${className}`.trim()}
    >
      {entries.map(([key, label]) => (
        <span
          key={key}
          className={
            features[key]
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-400 dark:text-slate-500 line-through'
          }
          title={`${label}: ${features[key] ? 'implemented' : 'not yet'}`}
        >
          {features[key] ? '✓' : '✗'}{label}
        </span>
      ))}
    </span>
  );
}
