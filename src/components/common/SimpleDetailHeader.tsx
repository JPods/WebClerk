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

  const getModeColors = () => {
    switch (mode) {
      case "add":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "edit":
        return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
      case "view":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    }
  };

  return (
    <div className={`flex items-center gap-3 py-3 px-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Back button */}
      {showBackButton && (
        <button
          type="button"
          onClick={handleBack}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
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
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
            {recordName || entityName}
          </h1>
          {recordId && (
            <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
              #{recordId}
            </span>
          )}
        </div>
        {recordName && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {entityName}
          </p>
        )}
      </div>

      {/* Mode badge */}
      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${getModeColors()}`}>
        {getModeIcon()}
        {getModeLabel()}
      </span>

      {/* Close button for inline/modal mode */}
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}

export default SimpleDetailHeader;
