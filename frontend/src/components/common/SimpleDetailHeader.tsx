/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * SimpleDetailHeader - Lightweight header for simple Detail pages
 * 
 * Displays:
 * - Entity type name
 * - Record ID (for edit/view)
 * - Mode indicator (Add/Edit/View)
 * - Back navigation (optional)
 */
import { useNavigate } from "react-router-dom";
import { ChevronLeft, Plus, Pencil, Eye, X } from "lucide-react";
import { DevBadge } from './DevBadge';
import { DetailFeatureBadge, type DetailFeatures } from './DetailFeatureBadge';

interface SimpleDetailHeaderProps {
  /** Entity type name (e.g., "Service", "Currency") */
  entityName: string;
  /** Record ID (for edit/view modes) */
  recordId?: string | number;
  /** Display name of the record */
  recordName?: string;
  /** Current mode */
  mode: "add" | "edit" | "view";
  /** Back navigation URL (optional) */
  backUrl?: string;
  /** Custom class name */
  className?: string;
  /** Whether to show back button */
  showBackButton?: boolean;
  /** Close callback for inline/modal mode */
  onClose?: () => void;
  /** Feature flags shown as a dev-only checklist badge */
  features?: DetailFeatures;
}

export function SimpleDetailHeader({
  entityName,
  recordId,
  recordName,
  mode,
  backUrl,
  className = "",
  showBackButton = true,
  onClose,
  features,
}: SimpleDetailHeaderProps) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (backUrl) {
      navigate(backUrl);
    } else {
      navigate(-1);
    }
  };

  const getModeIcon = () => {
    switch (mode) {
      case "add":
        return <Plus className="w-4 h-4" />;
      case "edit":
        return <Pencil className="w-4 h-4" />;
      case "view":
        return <Eye className="w-4 h-4" />;
    }
  };

  const getModeLabel = () => {
    switch (mode) {
      case "add":
        return "New";
      case "edit":
        return "Edit";
      case "view":
        return "View";
    }
  };

  const getModeStyle = (): React.CSSProperties => {
    switch (mode) {
      case "add":
        return { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' };
      case "edit":
        return { background: 'color-mix(in srgb, var(--db-accent-gold) 15%, transparent)', color: 'var(--db-accent-gold)' };
      case "view":
        return { background: 'color-mix(in srgb, var(--db-accent) 15%, transparent)', color: 'var(--db-accent)' };
    }
  };

  return (
    <div className={`flex items-center gap-3 py-3 px-4 ${className}`}
      style={{ background: 'var(--db-surface, #fff)', borderBottom: '1px solid var(--db-border, #dee2e6)', color: 'var(--db-text, #212529)' }}>
      {/* Back button */}
      {showBackButton && (
        <button
          type="button"
          onClick={handleBack}
          className="p-1.5 rounded-md transition-colors"
          style={{ color: 'var(--db-text-muted)' }}
          title="Go back"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      )}

      {/* Entity name and title */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <DevBadge label={entityName} />
          {features && <DetailFeatureBadge features={features} />}
          <h1 className="text-lg font-semibold truncate" style={{ color: 'var(--db-text)' }}>
            {recordName || entityName}
          </h1>
          {recordId && (
            <span className="text-sm font-mono" style={{ color: 'var(--db-text-muted)' }}>
              #{recordId}
            </span>
          )}
        </div>
        {recordName && (
          <p className="text-sm" style={{ color: 'var(--db-text-muted)' }}>
            {entityName}
          </p>
        )}
      </div>

      {/* Mode badge */}
      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full" style={getModeStyle()}>
        {getModeIcon()}
        {getModeLabel()}
      </span>

      {/* Close button for inline/modal mode */}
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-md transition-colors"
          style={{ color: 'var(--db-text-muted)' }}
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}

export default SimpleDetailHeader;
